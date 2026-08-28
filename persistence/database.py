from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


load_dotenv()

POSTGRESQL_URL_PREFIX = "postgresql+psycopg://"


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        raise ValueError("DATABASE_URL is not configured.")

    if not database_url.startswith(POSTGRESQL_URL_PREFIX):
        raise ValueError(
            "DATABASE_URL must use the "
            "'postgresql+psycopg://' driver."
        )

    return database_url


class Database:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(POSTGRESQL_URL_PREFIX):
            raise ValueError(
                "database_url must use the "
                "'postgresql+psycopg://' driver."
            )

        self.engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.session_factory.begin() as session:
            yield session

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        self.engine.dispose()


@lru_cache(maxsize=1)
def get_database() -> Database:
    return Database(get_database_url())
