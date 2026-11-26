"""One transcript file, tied to a location and a date."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Meeting(Base):
    """A single meeting transcript and the source it was taken from."""

    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id: Mapped[int] = mapped_column(Integer, unique=True)
    external_meeting_id: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(400))
    meeting_date: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_kind: Mapped[Optional[str]] = mapped_column(String(40))
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("locations.id"))
    # relevant is true only when the data_center gate fired. signals keeps every
    # provisional cue seen during the scan, including on skipped transcripts.
    relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    signals: Mapped[list] = mapped_column(JSONB, default=list)

    location: Mapped[Optional["Location"]] = relationship(back_populates="meetings")
    sections: Mapped[list["Section"]] = relationship(back_populates="meeting")
    facts: Mapped[list["Fact"]] = relationship(back_populates="meeting")
