"""Job rows. Status moves from pending to processing, then completed or failed."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Job

BLOCKING = ("pending", "processing", "completed")


def _now() -> datetime:
    """UTC timestamp for a status change."""
    return datetime.now(timezone.utc)


class JobRepository:
    """Reads and updates ingest jobs."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def add(self, job: Job) -> Job:
        """Insert a pending job."""
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: uuid.UUID) -> Job | None:
        """Return one job."""
        return self.session.get(Job, job_id)

    def recent(self, limit: int) -> list[Job]:
        """Return the newest jobs first."""
        return self.session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()

    def blocking(self, transcript_id: int) -> Job | None:
        """Return a job that already owns this transcript, ignoring failed jobs."""
        return (
            self.session.query(Job)
            .filter(Job.transcript_id == transcript_id, Job.status.in_(BLOCKING))
            .order_by(Job.created_at.desc())
            .first()
        )

    def claim_next(self) -> Job | None:
        """Lock the oldest pending job and mark it processing."""
        job = (
            self.session.query(Job)
            .filter_by(status="pending")
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            return None
        job.status = "processing"
        job.step = "starting"
        job.started_at = _now()
        job.updated_at = job.started_at
        self.session.flush()
        return job

    def requeue_interrupted(self) -> int:
        """Put crashed processing jobs back in the queue. A second crash fails the job."""
        rows = self.session.query(Job).filter_by(status="processing").all()
        for job in rows:
            job.attempts += 1
            job.updated_at = _now()
            if job.attempts >= 2:
                job.status = "failed"
                job.step = "failed"
                job.error = "The worker stopped while this job was processing."
                job.finished_at = job.updated_at
            else:
                job.status = "pending"
                job.step = "retrying after interruption"
        return len(rows)

    def set_step(self, job_id: uuid.UUID, step: str) -> None:
        """Record the current step while the job is processing."""
        job = self.get(job_id)
        if job is None or job.status != "processing":
            return
        job.step = step[:200]
        job.updated_at = _now()

    def complete(self, job_id: uuid.UUID, meeting_id: uuid.UUID, counts: dict, detail: str) -> None:
        """Mark the job completed and store the meeting it produced."""
        job = self.get(job_id)
        if job is None:
            return
        job.status = "completed"
        job.step = "completed"
        job.meeting_id = meeting_id
        job.section_count = counts["sections"]
        job.people_count = counts["people"]
        job.fact_count = counts["facts"]
        job.detail = detail
        job.error = None
        job.finished_at = _now()
        job.updated_at = job.finished_at

    def fail(self, job_id: uuid.UUID, error: str) -> None:
        """Mark the job failed and keep the error for the status endpoint."""
        job = self.get(job_id)
        if job is None:
            return
        job.status = "failed"
        job.step = "failed"
        job.error = error[:2000]
        job.finished_at = _now()
        job.updated_at = job.finished_at

    def delete_failed(self, transcript_id: int | None = None) -> list[str]:
        """Remove failed jobs (and return their upload paths) so they can be requeued."""
        query = self.session.query(Job).filter_by(status="failed")
        if transcript_id is not None:
            query = query.filter_by(transcript_id=transcript_id)
        rows = query.all()
        paths = [job.file_path for job in rows]
        for job in rows:
            self.session.delete(job)
        self.session.flush()
        return paths
