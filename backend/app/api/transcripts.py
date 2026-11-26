"""Single-transcript upload ingest."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import upload_dir
from app.dto.request import TranscriptUploadRequest
from app.dto.response import IngestResponse
from app.models import Job
from app.repositories import JobRepository, MeetingRepository

router = APIRouter(prefix="/transcripts", tags=["transcripts"])
logger = logging.getLogger("app.api.transcripts")


@router.post("", response_model=IngestResponse)
def ingest_transcript(
    file: UploadFile = File(..., description="Caption JSON: a list of {text, start, end}."),
    transcript_id: int = Form(...),
    title: str = Form(""),
    location: str = Form(""),
    location_id: int | None = Form(None),
    meeting_id: int | None = Form(None),
    meeting_date: str = Form(""),
    source_url: str = Form(""),
    source_kind: str = Form(""),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """Save the caption file and queue it. The response is the job id."""
    request = TranscriptUploadRequest(
        transcript_id=transcript_id,
        title=title,
        location=location,
        location_id=location_id,
        meeting_id=meeting_id,
        meeting_date=meeting_date,
        source_url=source_url,
        source_kind=source_kind,
    )
    raw = file.file.read()
    logger.info("POST /transcripts transcript %s bytes %s", request.transcript_id, len(raw))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="The file is not JSON.") from error
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="The file must be a list of captions.")
    try:
        parsed_date = date.fromisoformat(request.meeting_date) if request.meeting_date else None
    except ValueError as error:
        raise HTTPException(status_code=400, detail="meeting_date must be YYYY-MM-DD.") from error

    job_id = uuid.uuid4()
    path = upload_dir() / f"{job_id}.json"
    path.write_bytes(raw)
    try:
        meeting_repo = MeetingRepository(db)
        job_repo = JobRepository(db)
        if meeting_repo.for_transcript(request.transcript_id) is not None:
            raise HTTPException(status_code=409, detail="This transcript is already ingested.")
        if job_repo.blocking(request.transcript_id) is not None:
            raise HTTPException(status_code=409, detail="This transcript is already queued.")
        job_repo.add(
            Job(
                id=job_id,
                status="pending",
                step="pending",
                transcript_id=request.transcript_id,
                filename=file.filename or "",
                file_path=str(path),
                title=request.title,
                location_name=request.location,
                location_external_id=request.location_id,
                external_meeting_id=request.meeting_id,
                meeting_date=parsed_date,
                source_url=request.source_url or None,
                source_kind=request.source_kind or None,
            )
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    logger.info("transcript %s queued as job %s", request.transcript_id, job_id)
    return IngestResponse(job_id=job_id, status="pending")
