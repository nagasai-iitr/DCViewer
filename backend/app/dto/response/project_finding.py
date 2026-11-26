"""One dated finding on a project or policy timeline."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class ProjectFindingResponse(BaseModel):
    """A dated remark. A later row does not replace an earlier one."""

    finding_id: uuid.UUID
    finding_date: date | None = None
    transcript_id: int
    title: str
    kind: str
    stage: str | None = None
    prior_stage: str | None = None
    body: str
    excerpt: str | None = None
    coverage: str
    signals: list[str]
    start_seconds: float | None = None
