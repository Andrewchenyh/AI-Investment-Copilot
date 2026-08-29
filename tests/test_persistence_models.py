from __future__ import annotations

from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from persistence.models import (
    Base,
    ConversationSession,
    EvaluationRun,
    Message,
)


def constraint_names(table_name: str, constraint_type: type) -> set[str | None]:
    table = Base.metadata.tables[table_name]
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def index_columns(table_name: str) -> dict[str, tuple[str, ...]]:
    table = Base.metadata.tables[table_name]
    return {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }


def test_metadata_contains_expected_postgresql_tables() -> None:
    assert set(Base.metadata.tables) == {
        "evaluation_runs",
        "messages",
        "sessions",
    }


def test_session_model_uses_client_session_id_and_recent_activity_index() -> None:
    table = ConversationSession.__table__

    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, String)
    assert table.c.id.type.length == 128
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None
    assert index_columns("sessions") == {
        "ix_sessions_updated_at": ("updated_at",),
    }


def test_message_model_uses_postgresql_native_types() -> None:
    table = Message.__table__

    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.identity is not None
    assert isinstance(table.c.trace_id.type, PG_UUID)
    assert table.c.trace_id.type.as_uuid is True
    assert isinstance(table.c.trace.type, JSONB)


def test_message_session_foreign_key_cascades_on_delete() -> None:
    foreign_keys = list(Message.__table__.c.session_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "sessions.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_message_model_has_integrity_constraints_and_query_indexes() -> None:
    assert constraint_names("messages", CheckConstraint) == {
        "ck_messages_role",
        "ck_messages_status",
    }
    assert constraint_names("messages", UniqueConstraint) == {
        "uq_messages_session_trace_role",
    }
    assert index_columns("messages") == {
        "ix_messages_session_created_at": ("session_id", "created_at"),
        "ix_messages_trace_id": ("trace_id",),
    }


def test_session_message_relationship_is_bidirectional_and_cascading() -> None:
    session = ConversationSession(id="session-123")
    message = Message(
        role="user",
        content="Analyze ORCL",
        trace_id=uuid4(),
    )

    session.messages.append(message)

    assert message.session is session
    relationship = ConversationSession.__mapper__.relationships["messages"]
    assert relationship.back_populates == "session"
    assert relationship.passive_deletes is True
    assert "delete-orphan" in relationship.cascade


def test_evaluation_run_uses_jsonb_and_integrity_constraints() -> None:
    table = EvaluationRun.__table__

    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.identity is not None
    assert isinstance(table.c.payload.type, JSONB)
    assert constraint_names("evaluation_runs", CheckConstraint) == {
        "ck_evaluation_runs_consistent_counts",
        "ck_evaluation_runs_nonnegative_counts",
        "ck_evaluation_runs_pass_rate",
    }
    assert index_columns("evaluation_runs") == {
        "ix_evaluation_runs_created_at": ("created_at",),
    }
