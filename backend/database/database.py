from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_SERVICE_NAME = "pratirup_postgresql"
DATABASE_LAYER_VERSION = "1.0.0"


DB_HOST = os.getenv("PRATIRUP_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("PRATIRUP_DB_PORT", "5432"))
DB_NAME = os.getenv("PRATIRUP_DB_NAME", "pratirup_db")
DB_USER = os.getenv("PRATIRUP_DB_USER", "postgres")
DB_PASSWORD = os.getenv("PRATIRUP_DB_PASSWORD")


def build_database_url() -> URL:

    if not DB_PASSWORD:
        raise RuntimeError(
            "PRATIRUP_DB_PASSWORD is not configured. "
            "Set it as an environment variable before starting PRATIRUP."
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )


class Base(DeclarativeBase):

    pass


def create_database_engine() -> Engine:

    database_url = build_database_url()

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        future=True,
    )


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:

    global _engine

    if _engine is None:
        _engine = create_database_engine()

    return _engine


def get_session_factory() -> sessionmaker[Session]:

    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    return _session_factory


def get_db() -> Generator[Session, None, None]:

    session_factory = get_session_factory()
    db = session_factory()

    try:
        yield db
    finally:
        db.close()


@contextmanager
def database_session() -> Generator[Session, None, None]:

    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def check_database_connection() -> dict:

    try:
        engine = get_engine()

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS connected_user,
                        version() AS server_version
                    """
                )
            ).mappings().one()

        return {
            "connected": True,
            "status": "READY",
            "service": DATABASE_SERVICE_NAME,
            "version": DATABASE_LAYER_VERSION,
            "database": row["database_name"],
            "user": row["connected_user"],
            "server_version": row["server_version"],
            "host": DB_HOST,
            "port": DB_PORT,
        }

    except Exception as exc:
        return {
            "connected": False,
            "status": "NOT_READY",
            "service": DATABASE_SERVICE_NAME,
            "version": DATABASE_LAYER_VERSION,
            "database": DB_NAME,
            "host": DB_HOST,
            "port": DB_PORT,
            "error": str(exc),
        }


def dispose_database_engine() -> None:

    global _engine
    global _session_factory

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _session_factory = None
