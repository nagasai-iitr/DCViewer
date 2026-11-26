"""Project or policy list item."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.models import Project


class ProjectResponse(BaseModel):
    """A project or policy. stage is the latest stage; findings hold the history."""

    project_id: uuid.UUID
    name: str
    code: str | None = None
    kind: str
    about: str | None = None
    stage: str
    stage_as_of: date | None = None
    data_center: bool
    signals: list[str]
    location: str | None = None
    finding_count: int = 0

    @classmethod
    def from_project(cls, project: Project) -> "ProjectResponse":
        """Map a stored project into the public response."""
        return cls(
            project_id=project.id,
            name=project.name,
            code=project.code,
            kind=project.kind,
            about=project.about,
            stage=project.stage,
            stage_as_of=project.stage_as_of,
            data_center=project.data_center,
            signals=project.signals or [],
            location=project.location.name if project.location is not None else None,
            finding_count=len(project.findings or []),
        )
