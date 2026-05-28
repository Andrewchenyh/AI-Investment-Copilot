import json
from typing import Any

from api.redis_client import get_redis_client


HISTORY_TTL_SECONDS = 60 * 60 * 24


def save_history_item(session_id: str, item: dict[str, Any]) -> None:
    redis_client = get_redis_client()
    key = f"history:{session_id}"

    redis_client.rpush(key, json.dumps(item))
    redis_client.expire(key, HISTORY_TTL_SECONDS)


def get_history_items(session_id: str) -> list[dict[str, Any]]:
    redis_client = get_redis_client()
    key = f"history:{session_id}"

    raw_items = redis_client.lrange(key, 0, -1)
    return [json.loads(item) for item in raw_items]