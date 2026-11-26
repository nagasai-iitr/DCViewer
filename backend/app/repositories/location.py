"""Location rows."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Location


class LocationRepository:
    """Reads and inserts locations."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def find_or_create(self, external_id: int | None, name: str) -> Location:
        """Return the location with this manifest id or name, creating it when missing."""
        found = None
        if external_id is not None:
            found = self.session.query(Location).filter_by(external_id=external_id).one_or_none()
        if found is None:
            found = self.session.query(Location).filter_by(name=name).one_or_none()
        if found is None:
            found = Location(external_id=external_id, name=name)
            self.session.add(found)
            self.session.flush()
        return found
