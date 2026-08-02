import os
from functools import lru_cache


from dotenv import load_dotenv
from redis import Redis


load_dotenv()


REDIS_CONNECT_TIMEOUT_SECONDS = 1.0
REDIS_SOCKET_TIMEOUT_SECONDS = 1.0
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL is not configured.")

    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
        health_check_interval=REDIS_HEALTH_CHECK_INTERVAL_SECONDS,
    )
