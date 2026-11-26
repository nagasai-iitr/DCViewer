"""A stretch of one meeting: introduction, awards, an agenda item, or the close."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Section(Base):
    """One labeled part of a meeting. An introduction is a section, not an agenda."""

    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(400), default="")
    about: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    is_vote: Mapped[bool] = mapped_column(Boolean, default=False)
    relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    signals: Mapped[list] = mapped_column(JSONB, default=list)

    meeting: Mapped["Meeting"] = relationship(back_populates="sections")
    speakers: Mapped[list["SectionSpeaker"]] = relationship(back_populates="section")
    facts: Mapped[list["Fact"]] = relationship(back_populates="section")


class SectionSpeaker(Base):
    """A person speaking inside one section, with the caption span of that speech."""

    __tablename__ = "section_speakers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("sections.id"))
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("people.id"))
    role: Mapped[Optional[str]] = mapped_column(String(300))
    kind: Mapped[Optional[str]] = mapped_column(String(40))
    start_seconds: Mapped[Optional[float]] = mapped_column(Float)
    end_seconds: Mapped[Optional[float]] = mapped_column(Float)

    section: Mapped["Section"] = relationship(back_populates="speakers")
    person: Mapped["Person"] = relationship(back_populates="appearances")
