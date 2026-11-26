"""Engine, sessions, and table creation.

Endpoints use get_db from app.deps. The background worker uses session_scope
because it is not inside a request.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.config import database_url

_engine = None
_factory = None


def get_engine():
    """Return the shared engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def session_factory() -> sessionmaker[Session]:
    """Return the shared session factory."""
    global _factory
    if _factory is None:
        _factory = sessionmaker(bind=get_engine())
    return _factory


@contextmanager
def session_scope():
    """Open a session for background work. Commit on success, roll back on failure."""
    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create tables. An older integer-key schema is replaced with UUID keys."""
    from app.models import Base

    engine = get_engine()
    if _integer_keys(engine):
        import logging

        logging.getLogger("app.database").warning("replacing integer primary keys with uuid")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _ensure_project_code_columns(engine)


def _ensure_project_code_columns(engine) -> None:
    """Add code columns on projects when an older volume is missing them."""
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return
    names = {column["name"] for column in inspector.get_columns("projects")}
    statements = []
    if "code" not in names:
        statements.append("ALTER TABLE projects ADD COLUMN code VARCHAR(120)")
    if "code_key" not in names:
        statements.append("ALTER TABLE projects ADD COLUMN code_key VARCHAR(120)")
        statements.append("CREATE INDEX IF NOT EXISTS ix_projects_code_key ON projects (code_key)")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def reset_db() -> None:
    """Drop every table and create them again. Used for a clean test run."""
    from app.models import Base

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _integer_keys(engine) -> bool:
    """True when an existing locations table still uses an integer primary key."""
    inspector = inspect(engine)
    if "locations" not in inspector.get_table_names():
        return False
    for column in inspector.get_columns("locations"):
        if column["name"] == "id":
            return type(column["type"]).__name__ in {"INTEGER", "Integer"}
    return False
