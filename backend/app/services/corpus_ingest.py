"""Enqueue transcript jobs from a GatherGov corpus folder + manifest.json."""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import upload_dir
from app.models import CorpusRun, Job
from app.repositories import JobRepository, MeetingRepository

logger = logging.getLogger("app.services.corpus_ingest")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_manifest(corpus_path: Path) -> tuple[dict[int, str], list[dict]]:
    """Return (location_id → name, transcript rows) from manifest.json."""
    manifest_path = corpus_path / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json not found under {corpus_path}")
    payload = json.loads(manifest_path.read_text())
    locations = {
        int(row["id"]): str(row.get("name") or f"location-{row['id']}")
        for row in payload.get("locations") or []
        if row.get("id") is not None
    }
    transcripts = payload.get("transcripts") or []
    if not isinstance(transcripts, list):
        raise ValueError("manifest transcripts must be a list")
    return locations, transcripts


def enqueue_corpus(
    session: Session,
    corpus_path: Path,
    *,
    limit: int | None = None,
    location_ids: list[int] | None = None,
    skip_existing: bool = True,
) -> CorpusRun:
    """Create a corpus run and queue up to `limit` pending jobs from the manifest.

    Transcripts are staged into UPLOAD_DIR and processed one-by-one by the
    existing ingest worker. Already-ingested or already-queued ids are skipped.
    """
    corpus_path = corpus_path.resolve()
    if not corpus_path.is_dir():
        raise FileNotFoundError(f"corpus path is not a directory: {corpus_path}")

    locations, transcripts = load_manifest(corpus_path)
    wanted = set(location_ids) if location_ids else None

    run = CorpusRun(
        id=uuid.uuid4(),
        corpus_path=str(corpus_path),
        status="running",
        limit_n=limit,
        total_in_manifest=len(transcripts),
    )
    session.add(run)
    session.flush()

    meeting_repo = MeetingRepository(session)
    job_repo = JobRepository(session)
    staged_dir = upload_dir()

    try:
        for row in transcripts:
            if limit is not None and run.queued >= limit:
                break
            run.considered += 1
            tid = row.get("transcript_id")
            if tid is None:
                continue
            lids = row.get("location_ids") or []
            lid = lids[0] if lids else None
            if wanted is not None and (lid is None or int(lid) not in wanted):
                continue
            if skip_existing and meeting_repo.for_transcript(int(tid)) is not None:
                run.skipped_existing += 1
                continue
            if skip_existing and job_repo.blocking(int(tid)) is not None:
                run.skipped_existing += 1
                continue

            rel = row.get("file") or ""
            source = corpus_path / rel
            if not source.is_file():
                run.skipped_missing_file += 1
                continue

            job_id = uuid.uuid4()
            dest = staged_dir / f"{job_id}.json"
            shutil.copyfile(source, dest)
            job_repo.add(
                Job(
                    id=job_id,
                    status="pending",
                    step="pending",
                    transcript_id=int(tid),
                    filename=source.name,
                    file_path=str(dest),
                    title=row.get("title") or "",
                    location_name=locations.get(int(lid), "") if lid is not None else "",
                    location_external_id=int(lid) if lid is not None else None,
                    external_meeting_id=row.get("meeting_id"),
                    meeting_date=_parse_date(row.get("meeting_date")),
                    source_url=row.get("source_url"),
                    source_kind="corpus",
                )
            )
            run.queued += 1

        run.status = "queued" if run.queued else "completed"
        run.detail = (
            f"queued={run.queued} skipped_existing={run.skipped_existing} "
            f"skipped_missing_file={run.skipped_missing_file} considered={run.considered}"
        )
        if run.status == "completed":
            run.finished_at = datetime.now(timezone.utc)
        session.flush()
        logger.info("corpus run %s %s", run.id, run.detail)
        return run
    except Exception as error:
        run.status = "failed"
        run.error = str(error)
        run.finished_at = datetime.now(timezone.utc)
        session.flush()
        raise
