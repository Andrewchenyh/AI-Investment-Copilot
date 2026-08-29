from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all PostgreSQL ORM models."""


class ConversationSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_sessions_updated_at", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    trace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    status: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )
    trace: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ConversationSession] = relationship(
        back_populates="messages",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_messages_role",
        ),
        CheckConstraint(
            "status IS NULL OR status IN ('success', 'error')",
            name="ck_messages_status",
        ),
        UniqueConstraint(
            "session_id",
            "trace_id",
            "role",
            name="uq_messages_session_trace_role",
        ),
        Index(
            "ix_messages_session_created_at",
            "session_id",
            "created_at",
        ),
        Index("ix_messages_trace_id", "trace_id"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    total: Mapped[int] = mapped_column(nullable=False)
    passed: Mapped[int] = mapped_column(nullable=False)
    failed: Mapped[int] = mapped_column(nullable=False)
    pass_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "total >= 0 AND passed >= 0 AND failed >= 0",
            name="ck_evaluation_runs_nonnegative_counts",
        ),
        CheckConstraint(
            "passed + failed = total",
            name="ck_evaluation_runs_consistent_counts",
        ),
        CheckConstraint(
            "pass_rate >= 0 AND pass_rate <= 1",
            name="ck_evaluation_runs_pass_rate",
        ),
        Index(
            "ix_evaluation_runs_created_at",
            "created_at",
        ),
    )