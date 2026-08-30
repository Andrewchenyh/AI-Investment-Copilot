from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
DUMMY_DATABASE_URL = (
    "postgresql+psycopg://user:password@localhost:5432/copilot"
)


def make_alembic_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", DUMMY_DATABASE_URL)
    return Config(str(ALEMBIC_CONFIG_PATH))


def test_migration_history_has_one_linear_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_alembic_config(monkeypatch)
    script = ScriptDirectory.from_config(config)
    revision = script.get_revision("0001")

    assert script.get_heads() == ["0001"]
    assert revision is not None
    assert revision.down_revision is None
    assert revision.doc == "Create durable persistence tables."


def test_initial_migration_renders_expected_postgresql_schema(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = make_alembic_config(monkeypatch)

    command.upgrade(config, "head", sql=True)

    sql = capsys.readouterr().out
    normalized_sql = " ".join(sql.lower().split())

    assert "create table sessions" in normalized_sql
    assert "create table messages" in normalized_sql
    assert "create table evaluation_runs" in normalized_sql
    assert normalized_sql.index("create table sessions") < normalized_sql.index(
        "create table messages"
    )
    assert "trace_id uuid not null" in normalized_sql
    assert "trace jsonb" in normalized_sql
    assert "payload jsonb not null" in normalized_sql
    assert "on delete cascade" in normalized_sql
    assert "uq_messages_session_trace_role" in normalized_sql
    assert "ck_evaluation_runs_consistent_counts" in normalized_sql
    assert "insert into alembic_version" in normalized_sql
