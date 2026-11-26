"""Response after a transcript is queued."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class IngestResponse(BaseModel):
    """The job created for one upload. Poll GET /jobs/{job_id} for progress."""

    job_id: uuid.UUID
    status: str
