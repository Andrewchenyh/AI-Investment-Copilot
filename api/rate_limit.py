from fastapi import Header, HTTPException

from api.redis_client import get_redis_client


REQUESTS_PER_MINUTE = 10
WINDOW_SECONDS = 60


def enforce_rate_limit(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key.")

    redis_client = get_redis_client()
    redis_key = f"rate_limit:{x_api_key}"

    current_count = redis_client.incr(redis_key)

    if current_count == 1:
        redis_client.expire(redis_key, WINDOW_SECONDS)

    if current_count > REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {REQUESTS_PER_MINUTE} requests per minute.",
        )