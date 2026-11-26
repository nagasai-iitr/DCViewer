"""One dated statement on a person's timeline."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class StatementResponse(BaseModel):
    """One dated view. A later row does not replace an earlier one."""

    fact_id: uuid.UUID
    meeting_date: date | None = None
    transcript_id: int
    title: str
    stance: str | None = None
    prior_stance: str | None = None
    evidence_kind: str | None = None
    signals: list[str]
    topic: str | None = None
    body: str
    excerpt: str | None = None
    person_id: uuid.UUID | None = None
    person_name: str | None = None
    person_kind: str | None = None
    project_id: uuid.UUID | None = None
    project: str | None = None
    project_kind: str | None = None
    start_seconds: float | None = None
