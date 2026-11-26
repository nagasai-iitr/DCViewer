"""People and person-timeline reads."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import facts, people
from app.dto.response import PersonResponse, StatementResponse
from app.repositories import FactRepository, PersonRepository

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[PersonResponse])
def list_people(limit: int = 100, repo: PersonRepository = Depends(people)) -> list[PersonResponse]:
    """Return people. The same person is reused when name and address match closely."""
    limit = min(max(limit, 1), 500)
    return [PersonResponse.from_person(row) for row in repo.recent(limit)]


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: uuid.UUID, repo: PersonRepository = Depends(people)) -> PersonResponse:
    """Return one person."""
    person = repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")
    return PersonResponse.from_person(person)


@router.get("/{person_id}/statements", response_model=list[StatementResponse])
def person_statements(
    person_id: uuid.UUID,
    people_repo: PersonRepository = Depends(people),
    facts_repo: FactRepository = Depends(facts),
) -> list[StatementResponse]:
    """Return one person's views in meeting order.

    prior_stance is the previous stance on the same project.
    """
    person = people_repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")
    rows = facts_repo.for_person(person_id)
    views = []
    previous: dict = {}
    for fact, meeting, project in rows:
        key = project.id if project is not None else None
        views.append(
            StatementResponse(
                fact_id=fact.id,
                meeting_date=meeting.meeting_date,
                transcript_id=meeting.transcript_id,
                title=meeting.title,
                stance=fact.stance,
                prior_stance=previous.get(key),
                evidence_kind=fact.evidence_kind,
                signals=fact.signals or [],
                topic=fact.topic,
                body=fact.body,
                excerpt=fact.excerpt,
                person_id=person.id,
                person_name=person.name,
                person_kind=person.kind,
                project_id=project.id if project is not None else None,
                project=project.name if project is not None else None,
                project_kind=project.kind if project is not None else None,
                start_seconds=fact.start_seconds,
            )
        )
        if fact.stance:
            previous[key] = fact.stance
    return views
