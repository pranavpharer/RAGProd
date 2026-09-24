from pydantic import BaseModel , Field
from datetime import datetime , timezone



class ChatReq(BaseModel):
    message: str = Field(
        ...,
        min_length=3,
        max_length=10000,  # stops overly long messages
        description="Users query to Agent",
    )
    thread_id: str = Field(
        default="default",
        min_length=1,
        max_length=128,
        description="Conversation id"
    )


class ChatRes(BaseModel):
    response : str
    thread_id : str
    model_used : str
    cache_used : bool = False
    processing_t_ms : float
    t_Stamp : str = Field( default_factory= lambda: datetime.now(timezone.utc).isoformat())



class HealthResponse(BaseModel):
    stat : str = "healthy"
    environment : str
    version: str = "1.0.0"
    checks :dict = Field(default_factory=dict)

class MetricRes(BaseModel): # endpoints for metrics
    tot_reqs:int
    tot_err : int
    err_rate : str
    avg_latency : float 
    cache_hits : str
    tot_ip_tokens : int
    tot_op_tokens : int


class ErrResponse(BaseModel):
    error : str
    detail: str | None = None
    req_id : str | None = None



if __name__ == "__main__":
    from config import get_settings
    settings = get_settings()
    print(f"Environment: {settings.app_env}")
    print(f"Primary model: {settings.primary_model}")
    print(f"Rate limit: {settings.rate_limit}")
    print(f"Cache TTL: {settings.cache_ttl_sec}s")
    print(f"Max retries: {settings.max_retry}")
    print(f"Is production: {settings.is_production}")
    print("Config loaded successfully!")
