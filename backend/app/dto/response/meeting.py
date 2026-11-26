"""Meeting list item."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.models import Meeting


class MeetingResponse(BaseModel):
    """A stored meeting. relevant means the data-center keyword gate opened full ingest."""

    meeting_id: uuid.UUID
    transcript_id: int
    title: str
    meeting_date: date | None = None
    location: str | None = None
    relevant: bool
    signals: list[str]
    source_url: str | None = None

    @classmethod
    def from_meeting(cls, meeting: Meeting) -> "MeetingResponse":
        """Map a stored meeting into the public response."""
        return cls(
            meeting_id=meeting.id,
            transcript_id=meeting.transcript_id,
            title=meeting.title,
            meeting_date=meeting.meeting_date,
            location=meeting.location.name if meeting.location is not None else None,
            relevant=meeting.relevant,
            signals=meeting.signals or [],
            source_url=meeting.source_url,
        )
