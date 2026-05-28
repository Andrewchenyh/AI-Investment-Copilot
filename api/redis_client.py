import os

from dotenv import load_dotenv
from redis import Redis


load_dotenv()


def get_redis_client() -> Redis:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL is not configured.")

    return Redis.from_url(redis_url, decode_responses=True)