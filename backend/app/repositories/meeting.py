"""Meeting rows."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Fact, Meeting, Section, SectionSpeaker


class MeetingRepository:
    """Reads and inserts meetings."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def for_transcript(self, transcript_id: int) -> Meeting | None:
        """Return the meeting already stored for this transcript, if any."""
        return self.session.query(Meeting).filter_by(transcript_id=transcript_id).one_or_none()

    def add(self, meeting: Meeting) -> Meeting:
        """Insert a meeting and return it with its id set."""
        self.session.add(meeting)
        self.session.flush()
        return meeting

    def recent(self, limit: int, relevant_only: bool = False) -> list[Meeting]:
        """Return the newest meetings. relevant_only drops transcripts with no signals."""
        query = self.session.query(Meeting)
        if relevant_only:
            query = query.filter_by(relevant=True)
        return query.order_by(Meeting.meeting_date.desc().nulls_last()).limit(limit).all()

    def counts(self, meeting: Meeting) -> dict:
        """Count sections, distinct people, and facts stored for one meeting."""
        sections = self.session.query(Section).filter_by(meeting_id=meeting.id).count()
        people = (
            self.session.query(SectionSpeaker.person_id)
            .join(Section)
            .filter(Section.meeting_id == meeting.id)
            .distinct()
            .count()
        )
        facts = self.session.query(Fact).filter_by(meeting_id=meeting.id).count()
        return {"sections": sections, "people": people, "facts": facts}
