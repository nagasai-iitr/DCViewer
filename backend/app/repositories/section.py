"""Section rows."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Section


class SectionRepository:
    """Inserts sections."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def add(self, section: Section) -> Section:
        """Insert a section and return it with its id set."""
        self.session.add(section)
        self.session.flush()
        return section
