"""One uploaded transcript waiting for, or finished by, the ingest worker."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    """UTC timestamp for job rows."""
    return datetime.now(timezone.utc)


class Job(Base):
    """The upload and its status. The meeting row appears when the job completes."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    step: Mapped[str] = mapped_column(String(200), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    transcript_id: Mapped[int] = mapped_column(Integer, index=True)
    filename: Mapped[str] = mapped_column(String(300), default="")
    file_path: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(400), default="")
    location_name: Mapped[str] = mapped_column(String(200), default="")
    location_external_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_meeting_id: Mapped[Optional[int]] = mapped_column(Integer)
    meeting_date: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_kind: Mapped[Optional[str]] = mapped_column(String(40))
    error: Mapped[Optional[str]] = mapped_column(Text)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    section_count: Mapped[Optional[int]] = mapped_column(Integer)
    people_count: Mapped[Optional[int]] = mapped_column(Integer)
    fact_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
