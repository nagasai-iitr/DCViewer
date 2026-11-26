"""Fact rows."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import Fact, Meeting, Person, Project


class FactRepository:
    """Inserts statements and motion results."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def add(self, fact: Fact) -> Fact:
        """Insert a statement or a motion result."""
        self.session.add(fact)
        self.session.flush()
        return fact

    def for_person(self, person_id: uuid.UUID) -> list[tuple[Fact, Meeting, Project | None]]:
        """Return one person's statements in meeting order.

        Each row stays separate. A later stance does not replace an earlier one.
        """
        return (
            self.session.query(Fact, Meeting, Project)
            .join(Meeting, Fact.meeting_id == Meeting.id)
            .outerjoin(Project, Fact.project_id == Project.id)
            .filter(Fact.person_id == person_id, Fact.kind == "statement")
            .order_by(Meeting.meeting_date.asc().nulls_last(), Fact.start_seconds.asc().nulls_last())
            .all()
        )

    def for_project(self, project_id: uuid.UUID) -> list[tuple[Fact, Meeting, Person | None]]:
        """Return statements linked to one project, oldest first.

        Each row stays separate so stance changes across meetings stay visible.
        """
        return (
            self.session.query(Fact, Meeting, Person)
            .join(Meeting, Fact.meeting_id == Meeting.id)
            .outerjoin(Person, Fact.person_id == Person.id)
            .filter(Fact.project_id == project_id, Fact.kind == "statement")
            .order_by(Meeting.meeting_date.asc().nulls_last(), Fact.start_seconds.asc().nulls_last())
            .all()
        )
