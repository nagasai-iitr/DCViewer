"""One dated finding or stage update on a project or policy."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProjectFinding(Base):
    """A dated remark on a project. Later meetings append; they do not erase earlier ones.

    kind is stage_change, update, decision, concern, or negative.
    Negative findings are stored only when coverage is sufficient.
    """

    __tablename__ = "project_findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"))
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("sections.id"))
    finding_date: Mapped[Optional[date]] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(40))
    stage: Mapped[Optional[str]] = mapped_column(String(40))
    prior_stage: Mapped[Optional[str]] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[Optional[str]] = mapped_column(Text)
    coverage: Mapped[str] = mapped_column(String(20), default="sufficient")
    signals: Mapped[list] = mapped_column(JSONB, default=list)
    start_seconds: Mapped[Optional[float]] = mapped_column(Float)
    end_seconds: Mapped[Optional[float]] = mapped_column(Float)

    project: Mapped["Project"] = relationship(back_populates="findings")
    meeting: Mapped["Meeting"] = relationship()
    section: Mapped[Optional["Section"]] = relationship()
