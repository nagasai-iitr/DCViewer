"""A data-center project, or a policy broadly tied to one, inside one location."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    """One named project or policy. Statements point here as evidence of a view.

    kind is project or policy. code is a petition, case, ordinance, or project
    code when the transcript gives one (for example Ordinance 2025-23 or
    Project Loon). Matching prefers code over name when a code is present.
    stage is the latest stage whose meeting date we have stored.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("locations.id"))
    name: Mapped[str] = mapped_column(String(300))
    name_key: Mapped[str] = mapped_column(String(300))
    code: Mapped[Optional[str]] = mapped_column(String(120))
    code_key: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    about: Mapped[Optional[str]] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(40), default="unknown")
    stage_as_of: Mapped[Optional[date]] = mapped_column(Date)
    data_center: Mapped[bool] = mapped_column(Boolean, default=False)
    signals: Mapped[list] = mapped_column(JSONB, default=list)

    location: Mapped[Optional["Location"]] = relationship()
    facts: Mapped[list["Fact"]] = relationship(back_populates="project")
    findings: Mapped[list["ProjectFinding"]] = relationship(back_populates="project")
