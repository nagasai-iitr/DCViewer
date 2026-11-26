"""Picks pending jobs and runs the ingest off the request."""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.database import session_scope
from app.services.meeting_flow import MeetingFlow
from app.llm.gemini import GeminiClient
from app.llm.jev import JevClient
from app.repositories import JobRepository, MeetingRepository

logger = logging.getLogger("app.worker")


class JobWorker:
    """One background thread. A crashed processing job is queued again once."""

    def __init__(self) -> None:
        """Prepare the thread. It starts when start is called."""
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="ingest-worker", daemon=True)

    def start(self) -> None:
        """Requeue jobs left in processing, then start claiming."""
        with session_scope() as session:
            count = JobRepository(session).requeue_interrupted()
        if count:
            logger.info("requeued %s interrupted jobs", count)
        self._thread.start()

    def stop(self) -> None:
        """Ask the thread to leave after the current wait."""
        self._stop.set()
        self._thread.join(timeout=2)

    def _loop(self) -> None:
        """Claim one pending job, or wait a second when the queue is empty."""
        while not self._stop.is_set():
            try:
                job_id = self._claim()
            except Exception:
                logger.exception("claim failed")
                self._stop.wait(2)
                continue
            if job_id is None:
                self._stop.wait(1)
                continue
            self._run(job_id)

    def _claim(self):
        """Mark the oldest pending job as processing and return its id."""
        with session_scope() as session:
            job = JobRepository(session).claim_next()
            return None if job is None else job.id

    def _step(self, job_id, step: str) -> None:
        """Store the step so a status request can see it while the models run."""
        try:
            with session_scope() as session:
                JobRepository(session).set_step(job_id, step)
        except Exception:
            logger.exception("job %s step update failed", job_id)
        logger.info("job %s %s", job_id, step)

    def _fail(self, job_id, error: str) -> None:
        """Store the failure. The uploaded file stays so the error can be traced."""
        with session_scope() as session:
            JobRepository(session).fail(job_id, error)

    def _run(self, job_id) -> None:
        """Read the saved file, call the models, then commit the meeting or mark the job failed."""
        with session_scope() as session:
            job = JobRepository(session).get(job_id)
            if job is None:
                return
            meta = {
                "transcript_id": job.transcript_id,
                "title": job.title,
                "location": job.location_name,
                "location_id": job.location_external_id,
                "meeting_id": job.external_meeting_id,
                "meeting_date": job.meeting_date,
                "source_url": job.source_url,
                "source_kind": job.source_kind,
            }
            path = Path(job.file_path)
        flow = MeetingFlow(JevClient(), GeminiClient())
        try:
            prepared = flow.prepare(path, lambda step: self._step(job_id, step))
            detail = (
                f"data_center={flow.relevant} "
                f"keywords={','.join(flow.matched_keywords) or 'none'} "
                f"cues={','.join(flow.signal_names) or 'none'}; "
                f"jev {flow.jev.calls} calls, {flow.jev.cache_hits} reused, gemini {flow.gemini.calls} calls"
            )
            with session_scope() as session:
                meeting = flow.save(session, meta, prepared)
                counts = MeetingRepository(session).counts(meeting)
                JobRepository(session).complete(job_id, meeting.id, counts, detail)
            logger.info("job %s completed %s", job_id, detail)
        except Exception as error:
            detail = (
                f"data_center={flow.relevant} "
                f"keywords={','.join(getattr(flow, 'matched_keywords', []) or []) or 'none'} "
                f"cues={','.join(flow.signal_names) or 'none'}; "
                f"jev {flow.jev.calls} calls, gemini {flow.gemini.calls} calls"
            )
            logger.exception("job %s failed", job_id)
            self._fail(job_id, f"{error} ({detail})")
