"""Multipart fields accepted by POST /transcripts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptUploadRequest(BaseModel):
    """Metadata sent with the caption file. The file itself is a separate upload part."""

    transcript_id: int
    title: str = ""
    location: str = ""
    location_id: int | None = None
    meeting_id: int | None = None
    meeting_date: str = Field(default="", description="YYYY-MM-DD, or empty")
    source_url: str = ""
    source_kind: str = ""
