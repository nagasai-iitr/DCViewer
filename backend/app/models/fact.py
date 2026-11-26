"""A statement a person made, or the result of a motion, tied to a section."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Fact(Base):
    """One claim or decision. A topic summary is a statement. A vote result is an action."""

    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("sections.id"))
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("people.id"))
    kind: Mapped[str] = mapped_column(String(20))
    topic: Mapped[Optional[str]] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text)
    mentions: Mapped[list] = mapped_column(JSONB, default=list)
    stance: Mapped[Optional[str]] = mapped_column(String(20))
    evidence_kind: Mapped[Optional[str]] = mapped_column(String(20))
    signals: Mapped[list] = mapped_column(JSONB, default=list)
    excerpt: Mapped[Optional[str]] = mapped_column(Text)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"))
    motion_on: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[Optional[str]] = mapped_column(String(40))
    tally: Mapped[Optional[str]] = mapped_column(String(200))
    start_seconds: Mapped[Optional[float]] = mapped_column(Float)
    end_seconds: Mapped[Optional[float]] = mapped_column(Float)

    meeting: Mapped["Meeting"] = relationship(back_populates="facts")
    section: Mapped["Section"] = relationship(back_populates="facts")
    person: Mapped[Optional["Person"]] = relationship(back_populates="facts")
    project: Mapped[Optional["Project"]] = relationship(back_populates="facts")
