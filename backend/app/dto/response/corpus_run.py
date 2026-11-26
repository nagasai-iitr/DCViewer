"""Corpus run status view."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import CorpusRun


class CorpusRunResponse(BaseModel):
    """One folder/manifest enqueue pass."""

    run_id: uuid.UUID
    corpus_path: str
    status: str
    limit_n: int | None = None
    total_in_manifest: int
    considered: int
    queued: int
    skipped_existing: int
    skipped_missing_file: int
    error: str | None = None
    detail: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None

    @classmethod
    def from_run(cls, run: CorpusRun) -> "CorpusRunResponse":
        return cls(
            run_id=run.id,
            corpus_path=run.corpus_path,
            status=run.status,
            limit_n=run.limit_n,
            total_in_manifest=run.total_in_manifest,
            considered=run.considered,
            queued=run.queued,
            skipped_existing=run.skipped_existing,
            skipped_missing_file=run.skipped_missing_file,
            error=run.error,
            detail=run.detail,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
