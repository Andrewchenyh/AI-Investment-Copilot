import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

import api.rate_limit as rate_limit


def test_missing_api_key_is_rejected_before_redis_access(mocker) -> None:
    get_redis_client = mocker.patch.object(rate_limit, "get_redis_client")

    with pytest.raises(HTTPException) as exc_info:
        rate_limit.enforce_rate_limit(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing API key."
    get_redis_client.assert_not_called()


def test_first_request_starts_rate_limit_window(mocker) -> None:
    redis_client = mocker.Mock()
    redis_client.incr.return_value = 1
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        return_value=redis_client,
    )

    rate_limit.enforce_rate_limit("test-api-key")

    redis_client.incr.assert_called_once_with("rate_limit:test-api-key")
    redis_client.expire.assert_called_once_with(
        "rate_limit:test-api-key",
        rate_limit.WINDOW_SECONDS,
    )


def test_later_allowed_request_does_not_reset_window(mocker) -> None:
    redis_client = mocker.Mock()
    redis_client.incr.return_value = rate_limit.REQUESTS_PER_MINUTE
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        return_value=redis_client,
    )

    rate_limit.enforce_rate_limit("test-api-key")

    redis_client.incr.assert_called_once_with("rate_limit:test-api-key")
    redis_client.expire.assert_not_called()


def test_request_over_limit_is_rejected(mocker) -> None:
    redis_client = mocker.Mock()
    redis_client.incr.return_value = rate_limit.REQUESTS_PER_MINUTE + 1
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        return_value=redis_client,
    )

    with pytest.raises(HTTPException) as exc_info:
        rate_limit.enforce_rate_limit("test-api-key")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == (
        "Rate limit exceeded. "
        f"Max {rate_limit.REQUESTS_PER_MINUTE} requests per minute."
    )
    redis_client.expire.assert_not_called()


def test_redis_failure_fails_open_without_logging_api_key(mocker) -> None:
    api_key = "super-secret-api-key"
    redis_client = mocker.Mock()
    redis_client.incr.side_effect = RedisConnectionError("Redis unavailable")
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        return_value=redis_client,
    )
    log_event = mocker.patch.object(rate_limit, "log_event")

    rate_limit.enforce_rate_limit(api_key)

    log_event.assert_called_once()
    log_call = log_event.call_args
    assert log_call.args[1] == "rate_limit_unavailable"
    assert log_call.kwargs == {
        "error_type": "ConnectionError",
        "error_message": "Redis unavailable",
        "fail_open": True,
    }
    assert api_key not in repr(log_call)


def test_missing_redis_configuration_fails_open(mocker) -> None:
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        side_effect=ValueError("REDIS_URL is not configured."),
    )
    log_event = mocker.patch.object(rate_limit, "log_event")

    rate_limit.enforce_rate_limit("test-api-key")

    log_event.assert_called_once()
    log_call = log_event.call_args
    assert log_call.args[1] == "rate_limit_unavailable"
    assert log_call.kwargs["error_type"] == "ValueError"
    assert log_call.kwargs["fail_open"] is True


def test_unexpected_exception_is_not_swallowed(mocker) -> None:
    redis_client = mocker.Mock()
    redis_client.incr.side_effect = RuntimeError("programming bug")
    mocker.patch.object(
        rate_limit,
        "get_redis_client",
        return_value=redis_client,
    )

    with pytest.raises(RuntimeError, match="programming bug"):
        rate_limit.enforce_rate_limit("test-api-key")
