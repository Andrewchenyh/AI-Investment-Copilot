import hashlib
import json
from typing import Any

from api.redis_client import get_redis_client


def build_cache_key(tool_name: str, tool_args: dict[str, Any]) -> str:
    serialized_args = json.dumps(tool_args, sort_keys=True)
    args_hash = hashlib.md5(serialized_args.encode("utf-8")).hexdigest()
    return f"tool_cache:{tool_name}:{args_hash}"


def get_cached_tool_result(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any] | None:
    redis_client = get_redis_client()
    cache_key = build_cache_key(tool_name, tool_args)

    cached_value = redis_client.get(cache_key)
    if not cached_value:
        return None

    return json.loads(cached_value)


def set_cached_tool_result(
    tool_name: str,
    tool_args: dict[str, Any],
    result: dict[str, Any],
    ttl_seconds: int = 300,
) -> None:
    redis_client = get_redis_client()
    cache_key = build_cache_key(tool_name, tool_args)

    redis_client.set(
        cache_key,
        json.dumps(result),
        ex=ttl_seconds,
    )