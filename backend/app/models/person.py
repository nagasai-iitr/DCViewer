"""A person, reused across transcripts only when name and address both match.

kind is the role supported by a transcript: petitioner, resident, council, staff, or other.
The role on a single appearance is stored with that appearance, so a later meeting can differ.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Person(Base):
    """Someone named in a caption. Identity is the pair of name and address."""

    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("name_key", "address_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300))
    name_key: Mapped[str] = mapped_column(String(300))
    address: Mapped[Optional[str]] = mapped_column(String(400))
    address_key: Mapped[Optional[str]] = mapped_column(String(400))
    role: Mapped[Optional[str]] = mapped_column(String(300))
    kind: Mapped[Optional[str]] = mapped_column(String(40))
    department: Mapped[Optional[str]] = mapped_column(String(200))

    appearances: Mapped[list["SectionSpeaker"]] = relationship(back_populates="person")
    facts: Mapped[list["Fact"]] = relationship(back_populates="person")
