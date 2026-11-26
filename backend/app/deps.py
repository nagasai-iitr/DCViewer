"""FastAPI dependencies. Endpoints ask for a Session; they do not open one themselves."""
from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import session_factory
from app.repositories import (
    FactRepository,
    JobRepository,
    LocationViewsRepository,
    MeetingRepository,
    PersonRepository,
    ProjectRepository,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one request-scoped session. Commit on success, roll back on error."""
    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def jobs(db: Session = Depends(get_db)) -> JobRepository:
    """Job repository for this request."""
    return JobRepository(db)


def meetings(db: Session = Depends(get_db)) -> MeetingRepository:
    """Meeting repository for this request."""
    return MeetingRepository(db)


def people(db: Session = Depends(get_db)) -> PersonRepository:
    """Person repository for this request."""
    return PersonRepository(db)


def facts(db: Session = Depends(get_db)) -> FactRepository:
    """Fact repository for this request."""
    return FactRepository(db)


def projects(db: Session = Depends(get_db)) -> ProjectRepository:
    """Project repository for this request."""
    return ProjectRepository(db)


def location_views(db: Session = Depends(get_db)) -> LocationViewsRepository:
    """Location sentiment and statement views for this request."""
    return LocationViewsRepository(db)
