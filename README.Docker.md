# RAGProd deployment

RAGProd currently accepts a question, sanitizes it, and sends it to the configured Gemini model with a fallback model. This repository does not yet include document ingestion, a vector index, or retrieval; no corpus or topic has been added or changed here. The `/chat` contract remains available for the existing client.

## Configure

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` and a unique `API_AUTH_TOKEN` of at least 32 characters. Keep `.env` out of source control and image builds. Model names and application limits can be overridden with environment variables; the defaults preserve the existing Gemini models.

LangSmith tracing is disabled by default because it sends trace data to an external service. Enable `LANGSMITH_TRACING=true` only when that data flow is intended, and provide the LangSmith credentials separately.

## Run with Docker Compose

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env and replace both required credentials.
docker compose up --build -d
docker compose ps
```

Compose binds the API to `127.0.0.1:8000`, runs as a non-root user with a read-only root filesystem, drops Linux capabilities, and checks `/health`. Put a TLS reverse proxy or load balancer in front of it for remote access. Set `FORWARDED_ALLOW_IPS` to the trusted proxy address when forwarding client IP headers; do not trust arbitrary forwarded headers.

The chat API requires the configured key in production:

```powershell
curl.exe -H "X-API-Key: <your API_AUTH_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message":"Ask a question","thread_id":"demo"}' `
  http://127.0.0.1:8000/chat
```

`/health` is available without authentication for container and load-balancer checks. `/metrics` and `/cache/stats` require the same `X-API-Key`. Interactive API documentation is enabled in development and disabled in production.

## Deployment notes

- Run one worker per container with the default configuration. Cache, counters, and rate limiting are process-local; use a shared cache and rate-limit backend before increasing workers or replicas.
- Set `WEB_CONCURRENCY` only when you have accounted for that process-local state.
- Supply credentials through a secrets manager or your deployment platform in production rather than storing `.env` on the host.
- Logs are JSON and omit request/response content. Do not enable external tracing unless its data handling matches your requirements.
- The production API key is a shared bearer secret. Place it in a secret store and rotate it through a controlled deployment.

## Build an image

```powershell
docker build -t ragprod:latest .
```

Publish the image to your registry and deploy it behind your platform's TLS and network controls. The container listens on port 8000.
