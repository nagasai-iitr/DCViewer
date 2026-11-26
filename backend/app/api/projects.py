"""Project snapshot, findings, and people-view reads."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import facts, projects
from app.dto.response import ProjectFindingResponse, ProjectResponse, StatementResponse
from app.repositories import FactRepository, ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(limit: int = 100, repo: ProjectRepository = Depends(projects)) -> list[ProjectResponse]:
    """Return projects and policies, with the latest stage we have stored."""
    limit = min(max(limit, 1), 500)
    return [ProjectResponse.from_project(row) for row in repo.recent(limit)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: uuid.UUID, repo: ProjectRepository = Depends(projects)) -> ProjectResponse:
    """Return one project or policy snapshot."""
    project = repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse.from_project(project)


@router.get("/{project_id}/findings", response_model=list[ProjectFindingResponse])
def project_findings(
    project_id: uuid.UUID,
    repo: ProjectRepository = Depends(projects),
) -> list[ProjectFindingResponse]:
    """Return dated findings for one project, oldest first."""
    if repo.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    views = []
    for finding, meeting in repo.findings_for(project_id):
        views.append(
            ProjectFindingResponse(
                finding_id=finding.id,
                finding_date=finding.finding_date,
                transcript_id=meeting.transcript_id,
                title=meeting.title,
                kind=finding.kind,
                stage=finding.stage,
                prior_stage=finding.prior_stage,
                body=finding.body,
                excerpt=finding.excerpt,
                coverage=finding.coverage,
                signals=finding.signals or [],
                start_seconds=finding.start_seconds,
            )
        )
    return views


@router.get("/{project_id}/statements", response_model=list[StatementResponse])
def project_statements(
    project_id: uuid.UUID,
    projects_repo: ProjectRepository = Depends(projects),
    facts_repo: FactRepository = Depends(facts),
) -> list[StatementResponse]:
    """Return people views on one project in meeting order."""
    project = projects_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    rows = facts_repo.for_project(project_id)
    views = []
    previous: dict = {}
    for fact, meeting, person in rows:
        person_key = person.id if person is not None else None
        views.append(
            StatementResponse(
                fact_id=fact.id,
                meeting_date=meeting.meeting_date,
                transcript_id=meeting.transcript_id,
                title=meeting.title,
                stance=fact.stance,
                prior_stance=previous.get(person_key),
                evidence_kind=fact.evidence_kind,
                signals=fact.signals or [],
                topic=fact.topic,
                body=fact.body,
                excerpt=fact.excerpt,
                person_id=person.id if person is not None else None,
                person_name=person.name if person is not None else None,
                person_kind=person.kind if person is not None else None,
                project_id=project.id,
                project=project.name,
                project_kind=project.kind,
                start_seconds=fact.start_seconds,
            )
        )
        if person_key is not None and fact.stance:
            previous[person_key] = fact.stance
    return views
