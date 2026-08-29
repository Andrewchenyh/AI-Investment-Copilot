"""Create durable persistence tables.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable session, message, and evaluation storage."""
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sessions_updated_at",
        "sessions",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_messages_role",
        ),
        sa.CheckConstraint(
            "status IS NULL OR status IN ('success', 'error')",
            name="ck_messages_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "trace_id",
            "role",
            name="uq_messages_session_trace_role",
        ),
    )
    op.create_index(
        "ix_messages_session_created_at",
        "messages",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_messages_trace_id",
        "messages",
        ["trace_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_runs",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "passed",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "failed",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "pass_rate",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "total >= 0 AND passed >= 0 AND failed >= 0",
            name="ck_evaluation_runs_nonnegative_counts",
        ),
        sa.CheckConstraint(
            "passed + failed = total",
            name="ck_evaluation_runs_consistent_counts",
        ),
        sa.CheckConstraint(
            "pass_rate >= 0 AND pass_rate <= 1",
            name="ck_evaluation_runs_pass_rate",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_runs_created_at",
        "evaluation_runs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove durable persistence tables in dependency-safe order."""
    op.drop_index(
        "ix_evaluation_runs_created_at",
        table_name="evaluation_runs",
    )
    op.drop_table("evaluation_runs")

    op.drop_index(
        "ix_messages_trace_id",
        table_name="messages",
    )
    op.drop_index(
        "ix_messages_session_created_at",
        table_name="messages",
    )
    op.drop_table("messages")

    op.drop_index(
        "ix_sessions_updated_at",
        table_name="sessions",
    )
    op.drop_table("sessions")
