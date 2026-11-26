"""One person's statement at a location in a given month."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class LocationStatementResponse(BaseModel):
    """A dated stance excerpt for the location side panel."""

    fact_id: uuid.UUID
    person_id: uuid.UUID | None = None
    person_name: str | None = None
    person_kind: str | None = None
    stance: str | None = None
    body: str
    excerpt: str | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    meeting_date: date | None = None
    start_seconds: float | None = None
