from __future__ import annotations

from unittest.mock import MagicMock, sentinel

import pytest
from sqlalchemy.orm import Session

import persistence.database as database_module
from persistence.database import Database, get_database_url


DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/copilot"


def make_database_without_engine() -> Database:
    """Build a Database shell so unit tests never open a real connection."""
    return object.__new__(Database)


def test_get_database_url_returns_trimmed_postgresql_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", f"  {DATABASE_URL}  ")

    assert get_database_url() == DATABASE_URL


def test_get_database_url_rejects_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        get_database_url()


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///copilot.db",
        "postgresql://user:password@localhost/copilot",
    ],
)
def test_get_database_url_rejects_unsupported_driver(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ValueError, match=r"postgresql\+psycopg://"):
        get_database_url()


def test_database_configures_engine_and_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MagicMock()
    session_factory = MagicMock()
    create_engine = MagicMock(return_value=engine)
    create_session_factory = MagicMock(return_value=session_factory)
    monkeypatch.setattr(database_module, "create_engine", create_engine)
    monkeypatch.setattr(database_module, "sessionmaker", create_session_factory)

    database = Database(DATABASE_URL)

    assert database.engine is engine
    assert database.session_factory is session_factory
    create_engine.assert_called_once_with(DATABASE_URL, pool_pre_ping=True)
    create_session_factory.assert_called_once_with(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )


def test_database_rejects_unsupported_driver() -> None:
    with pytest.raises(ValueError, match=r"postgresql\+psycopg://"):
        Database("sqlite:///copilot.db")


def test_session_uses_transaction_context() -> None:
    database = make_database_without_engine()
    session_factory = MagicMock()
    transaction = MagicMock()
    session = MagicMock(spec=Session)
    transaction.__enter__.return_value = session
    session_factory.begin.return_value = transaction
    database.session_factory = session_factory

    with database.session() as yielded_session:
        assert yielded_session is session

    session_factory.begin.assert_called_once_with()
    transaction.__exit__.assert_called_once_with(None, None, None)


def test_session_propagates_exception_to_transaction_context() -> None:
    database = make_database_without_engine()
    session_factory = MagicMock()
    transaction = MagicMock()
    transaction.__enter__.return_value = MagicMock(spec=Session)
    transaction.__exit__.return_value = False
    session_factory.begin.return_value = transaction
    database.session_factory = session_factory

    with pytest.raises(RuntimeError, match="write failed"):
        with database.session():
            raise RuntimeError("write failed")

    exception_type, exception, _ = transaction.__exit__.call_args.args
    assert exception_type is RuntimeError
    assert str(exception) == "write failed"


def test_ping_executes_select_one() -> None:
    database = make_database_without_engine()
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    database.engine = engine

    database.ping()

    engine.connect.assert_called_once_with()
    statement = connection.execute.call_args.args[0]
    assert str(statement) == "SELECT 1"


def test_dispose_releases_engine_pool() -> None:
    database = make_database_without_engine()
    database.engine = MagicMock()

    database.dispose()

    database.engine.dispose.assert_called_once_with()


def test_get_database_reuses_single_database_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = MagicMock(return_value=sentinel.database)
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setattr(database_module, "Database", constructor)
    database_module.get_database.cache_clear()

    try:
        first = database_module.get_database()
        second = database_module.get_database()

        assert first is sentinel.database
        assert second is sentinel.database
        constructor.assert_called_once_with(DATABASE_URL)
    finally:
        database_module.get_database.cache_clear()
