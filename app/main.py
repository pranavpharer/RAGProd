import hmac
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
settings = get_settings()
# `traceable` reads this setting at call time; make telemetry opt-in even when
# the deployment injects LangSmith credentials for another purpose.
os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing_v2).lower()

from app.agent import ProdAgent
from app.cache import CacheResp
from app.models import ChatReq, ChatRes, ErrResponse, HealthResponse, MetricRes
from app.monitoring import Metrics, gLogger
from app.security import SecPipeline

logger = gLogger("RAGProd")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting application", extra={"extra_data": {
        "environment": settings.app_env,
        "primary_model": settings.primary_model,
        "tracing_enabled": settings.langsmith_tracing_v2,
    }})
    app.state.security = SecPipeline()
    app.state.cache = CacheResp(settings.cache_ttl_sec, settings.cache_max_entries)
    app.state.metrics = Metrics()
    app.state.agent = ProdAgent()
    logger.info("Application startup complete")
    try:
        yield
    finally:
        logger.info("Application shutdown", extra={"extra_data": app.state.metrics.get_summary()})


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="RAGProd",
    description="Question answering service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded. Please try again later."})


def require_api_key(x_api_key: str | None) -> None:
    configured = get_settings().api_auth_token
    if get_settings().is_production:
        expected = configured.get_secret_value() if configured else ""
        if not x_api_key or not hmac.compare_digest(x_api_key, expected):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.post("/chat", response_model=ChatRes, responses={429: {"model": ErrResponse}})
@limiter.limit(get_settings().rate_limit)
async def chat_endpoint(request: Request, chat_req: ChatReq, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    started = time.perf_counter()
    cache: CacheResp = request.app.state.cache
    metrics: Metrics = request.app.state.metrics
    security: SecPipeline = request.app.state.security

    is_allowed, cleaned_query, security_notes = security.check_ip(chat_req.message)
    if not is_allowed:
        metrics.record_request(error=True)
        logger.warning("Request blocked by security pipeline")
        raise HTTPException(status_code=400, detail="Request blocked by security pipeline")

    cached_response = cache.get(cleaned_query)
    if cached_response is not None:
        metrics.record_request(
            ip_tokens=max(1, int(len(cleaned_query.split()) * 1.2)),
            latency_ms=(time.perf_counter() - started) * 1000,
            cache_hit=True,
        )
        return ChatRes(
            response=cached_response,
            thread_id=chat_req.thread_id,
            model_used="Cache",
            cache_used=True,
            processing_t_ms=(time.perf_counter() - started) * 1000,
        )

    try:
        result = await run_in_threadpool(request.app.state.agent.invoke, cleaned_query)
    except Exception as exc:
        metrics.record_request(latency_ms=(time.perf_counter() - started) * 1000, error=True)
        logger.error("Model invocation failed", extra={"extra_data": {"error_type": type(exc).__name__}})
        raise HTTPException(status_code=503, detail="The model service is temporarily unavailable") from None

    if result.get("error") or result.get("model") == "error_handler":
        metrics.record_request(latency_ms=(time.perf_counter() - started) * 1000, error=True)
        raise HTTPException(status_code=503, detail="The model service is temporarily unavailable")

    response_text = result.get("response")
    if not isinstance(response_text, str):
        response_text = str(response_text)
    validated_response, output_warnings = security.check_op(response_text)
    security_notes.extend(output_warnings)
    cache.set(cleaned_query, validated_response)

    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics.record_request(
        ip_tokens=max(1, int(len(cleaned_query.split()) * 1.2)),
        op_tokens=max(1, int(len(validated_response.split()) * 1.2)),
        latency_ms=elapsed_ms,
    )
    if security_notes:
        logger.info("Security controls applied", extra={"extra_data": {"notes": security_notes}})
    return ChatRes(
        response=validated_response,
        thread_id=chat_req.thread_id,
        model_used=str(result.get("model", "unknown")),
        cache_used=False,
        processing_t_ms=elapsed_ms,
    )


@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    current_settings = get_settings()
    checks = {
        "agent": getattr(request.app.state, "agent", None) is not None,
        "security": getattr(request.app.state, "security", None) is not None,
        "cache": getattr(request.app.state, "cache", None) is not None,
    }
    return HealthResponse(
        stat="healthy" if all(checks.values()) else "degraded",
        environment=current_settings.app_env,
        checks=checks,
    )


@app.get("/metrics", response_model=MetricRes)
async def get_metrics(request: Request, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return MetricRes(**request.app.state.metrics.get_summary())


@app.get("/cache/stats")
async def cache_stat(request: Request, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    return request.app.state.cache.stats
