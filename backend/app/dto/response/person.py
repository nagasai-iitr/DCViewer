"""Person list item."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models import Person


class PersonResponse(BaseModel):
    """A person. kind is petitioner, resident, council, staff, or other."""

    person_id: uuid.UUID
    name: str
    address: str | None = None
    role: str | None = None
    kind: str | None = None

    @classmethod
    def from_person(cls, person: Person) -> "PersonResponse":
        """Map a stored person into the public response."""
        return cls(
            person_id=person.id,
            name=person.name,
            address=person.address,
            role=person.role,
            kind=person.kind,
        )
