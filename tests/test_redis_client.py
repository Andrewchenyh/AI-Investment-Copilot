from collections.abc import Iterator

import pytest

import api.redis_client as redis_client


@pytest.fixture(autouse=True)
def clear_redis_client_cache() -> Iterator[None]:
    redis_client.get_redis_client.cache_clear()
    yield
    redis_client.get_redis_client.cache_clear()


def test_get_redis_client_reuses_one_client(monkeypatch) -> None:
    sentinel_client = object()
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_from_url(redis_url: str, **options: object) -> object:
        calls.append((redis_url, options))
        return sentinel_client

    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setattr(redis_client.Redis, "from_url", fake_from_url)

    first = redis_client.get_redis_client()
    second = redis_client.get_redis_client()

    assert first is sentinel_client
    assert second is first
    assert calls == [
        (
            "redis://example.test:6379/0",
            {
                "decode_responses": True,
                "socket_connect_timeout": 1.0,
                "socket_timeout": 1.0,
                "health_check_interval": 30,
            },
        )
    ]


def test_get_redis_client_requires_redis_url(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ValueError, match="REDIS_URL is not configured"):
        redis_client.get_redis_client()
