"""Ingest job status reads."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import jobs
from app.dto.response import JobResponse
from app.repositories import JobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(limit: int = 50, repo: JobRepository = Depends(jobs)) -> list[JobResponse]:
    """Return the newest jobs, including the step each one is on."""
    limit = min(max(limit, 1), 200)
    return [JobResponse.from_job(job) for job in repo.recent(limit)]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, repo: JobRepository = Depends(jobs)) -> JobResponse:
    """Return one job, including its current step, error, and meeting id."""
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobResponse.from_job(job)
