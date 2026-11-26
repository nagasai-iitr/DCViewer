"""Job status returned to the client.

This is not the Job ORM row. The upload path and other internal fields stay off
the wire; the API only exposes what a caller needs to poll progress.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import Job


class JobResponse(BaseModel):
    """One ingest job and the step it is on."""

    job_id: uuid.UUID
    status: str
    step: str
    transcript_id: int
    filename: str
    title: str
    error: str | None = None
    detail: str | None = None
    meeting_id: uuid.UUID | None = None
    section_count: int | None = None
    people_count: int | None = None
    fact_count: int | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        """Map a stored job into the public response."""
        return cls(
            job_id=job.id,
            status=job.status,
            step=job.step,
            transcript_id=job.transcript_id,
            filename=job.filename,
            title=job.title,
            error=job.error,
            detail=job.detail,
            meeting_id=job.meeting_id,
            section_count=job.section_count,
            people_count=job.people_count,
            fact_count=job.fact_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
