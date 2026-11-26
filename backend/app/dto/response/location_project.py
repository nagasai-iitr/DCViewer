"""Project details shown for a location in one month."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class LocationProjectFinding(BaseModel):
    """One finding from the selected month on a project."""

    finding_id: uuid.UUID
    finding_date: date | None = None
    kind: str
    stage: str | None = None
    body: str
    excerpt: str | None = None


class LocationProjectResponse(BaseModel):
    """A project or policy active at a location in the selected month."""

    project_id: uuid.UUID
    name: str
    code: str | None = None
    kind: str
    about: str | None = None
    stage: str
    stage_as_of: date | None = None
    data_center: bool
    signals: list[str]
    statement_count: int = 0
    findings: list[LocationProjectFinding] = []
