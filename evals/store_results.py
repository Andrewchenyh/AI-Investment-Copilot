from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path("evals/results/eval_runs.sqlite3")


def init_eval_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                pass_rate REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_eval_run(
    payload: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    init_eval_db(db_path)

    summary = payload["summary"]

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO eval_runs (
                total,
                passed,
                failed,
                pass_rate,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                summary["total"],
                summary["passed"],
                summary["failed"],
                summary["pass_rate"],
                json.dumps(payload),
            ),
        )
        conn.commit()

        return int(cursor.lastrowid)


def list_eval_runs(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    init_eval_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id,
                created_at,
                total,
                passed,
                failed,
                pass_rate
            FROM eval_runs
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_eval_run(
    run_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    init_eval_db(db_path)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM eval_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row[0])