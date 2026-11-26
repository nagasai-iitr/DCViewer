"""A city or other place a meeting belongs to."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Location(Base):
    """The place a meeting was held, keyed by the manifest location id."""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(200))

    meetings: Mapped[list["Meeting"]] = relationship(back_populates="location")
