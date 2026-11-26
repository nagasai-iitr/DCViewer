"""Links between a section and a person who spoke in it."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SectionSpeaker


class SectionSpeakerRepository:
    """Inserts section speakers."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def add(self, speaker: SectionSpeaker) -> SectionSpeaker:
        """Link a person to the section they spoke in."""
        self.session.add(speaker)
        self.session.flush()
        return speaker
