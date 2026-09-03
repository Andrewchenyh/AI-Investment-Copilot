from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from persistence.database import Database, get_database
from persistence.models import ConversationSession, Message


VALID_STATUSES = frozenset({"success", "error"})
MAX_SESSION_ID_LENGTH = 128


class SessionRepository:
    """Persist conversation sessions and their messages in PostgreSQL."""

    def __init__(self, database: Database | None = None) -> None:
        self.database = (
            database
            if database is not None
            else get_database()
        )

    def save_interaction(
        self,
        *,
        session_id: str,
        query: str,
        status: str,
        trace_id: str,
        trace: list[dict[str, Any]],
        answer: str | None = None,
        message: str | None = None,
    ) -> None:
        parsed_trace_id = self._validate_input(
            session_id=session_id,
            query=query,
            status=status,
            trace_id=trace_id,
            answer=answer,
            message=message,
        )

        assistant_content = (
            answer
            if status == "success"
            else message
        )
        assert assistant_content is not None

        session_statement = (
            insert(ConversationSession)
            .values(id=session_id)
            .on_conflict_do_update(
                index_elements=[ConversationSession.id],
                set_={"updated_at": func.now()},
            )
        )

        message_statement = (
            insert(Message)
            .values(
                [
                    {
                        "session_id": session_id,
                        "role": "user",
                        "content": query,
                        "trace_id": parsed_trace_id,
                        "status": None,
                        "trace": None,
                    },
                    {
                        "session_id": session_id,
                        "role": "assistant",
                        "content": assistant_content,
                        "trace_id": parsed_trace_id,
                        "status": status,
                        "trace": trace,
                    },
                ]
            )
            .on_conflict_do_nothing(
                constraint="uq_messages_session_trace_role",
            )
        )

        with self.database.session() as database_session:
            database_session.execute(session_statement)
            database_session.execute(message_statement)

    @staticmethod
    def _validate_input(
        *,
        session_id: str,
        query: str,
        status: str,
        trace_id: str,
        answer: str | None,
        message: str | None,
    ) -> UUID:
        if not session_id.strip():
            raise ValueError("session_id must not be blank.")

        if len(session_id) > MAX_SESSION_ID_LENGTH:
            raise ValueError(
                "session_id must not exceed "
                f"{MAX_SESSION_ID_LENGTH} characters."
            )

        if not query.strip():
            raise ValueError("query must not be blank.")

        if status not in VALID_STATUSES:
            raise ValueError(
                "status must be either 'success' or 'error'."
            )

        if status == "success" and answer is None:
            raise ValueError(
                "answer is required when status is 'success'."
            )

        if status == "error" and message is None:
            raise ValueError(
                "message is required when status is 'error'."
            )

        try:
            return UUID(trace_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "trace_id must be a valid UUID."
            ) from exc