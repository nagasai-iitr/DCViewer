"""Person rows. Reuse when name and address match, including close speech-to-text variants."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Person
from app.utils import addresses_match, names_match, normalize


def _known_kind(value: str | None) -> str | None:
    """Return a role the pipeline stores, or None when the model left it blank."""
    if value in {"petitioner", "resident", "council", "staff", "other"}:
        return value
    return None


class PersonRepository:
    """Reads and inserts people."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def find_or_create(self, spoken: dict) -> Person:
        """Reuse a person when name and address already match closely enough.

        Exact name+address wins first. Otherwise a high-confidence fuzzy match
        covers speech-to-text drift. A resident or petitioner with no address is
        a new row. A council member or staff member with no address is reused
        when one address-less row already has that name and role.
        """
        name = (spoken.get("name") or "").strip()
        address = (spoken.get("address") or "").strip() or None
        name_key = normalize(name)
        address_key = normalize(address) if address else None
        kind = _known_kind(spoken.get("kind"))
        found = self._find_existing(name, name_key, address, address_key, kind)
        if found is not None:
            self._fill_gaps(found, spoken, kind)
            return found
        person = Person(
            name=name,
            name_key=name_key,
            address=address,
            address_key=address_key,
            role=spoken.get("role"),
            kind=kind,
            department=spoken.get("department"),
        )
        self.session.add(person)
        self.session.flush()
        return person

    def _find_existing(self, name, name_key, address, address_key, kind) -> Person | None:
        """Return the best existing person for this spoken identity, or None."""
        if name_key and address_key:
            exact = (
                self.session.query(Person)
                .filter_by(name_key=name_key, address_key=address_key)
                .one_or_none()
            )
            if exact is not None:
                return exact
            return self._fuzzy_name_and_address(name, address)

        if name_key and kind in {"council", "staff"}:
            matches = (
                self.session.query(Person)
                .filter_by(kind=kind)
                .filter(Person.address_key.is_(None))
                .all()
            )
            close = [row for row in matches if names_match(name, row.name)]
            if len(close) == 1:
                return close[0]
        return None

    def _fuzzy_name_and_address(self, name: str, address: str) -> Person | None:
        """Match speech-to-text variants of name and address at high confidence."""
        candidates = self.session.query(Person).filter(Person.address_key.is_not(None)).all()
        close = [
            row
            for row in candidates
            if names_match(name, row.name) and addresses_match(address, row.address)
        ]
        if len(close) == 1:
            return close[0]
        return None

    def _fill_gaps(self, found: Person, spoken: dict, kind: str | None) -> None:
        """Keep the first solid role we saw; fill blanks only."""
        if found.kind in (None, "", "other") and kind not in (None, "other"):
            found.kind = kind
        if not found.role and spoken.get("role"):
            found.role = spoken.get("role")
        if not found.department and spoken.get("department"):
            found.department = spoken.get("department")

    def get(self, person_id) -> Person | None:
        """Return one person."""
        return self.session.get(Person, person_id)

    def recent(self, limit: int) -> list[Person]:
        """Return people ordered by name."""
        return self.session.query(Person).order_by(Person.name).limit(limit).all()
