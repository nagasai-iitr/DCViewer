"""Read aggregates for the location sentiment UI."""
from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Fact, Location, Meeting, Person, Project, ProjectFinding

_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def parse_month(value: str) -> tuple[date, date]:
    """Return inclusive start and exclusive end dates for YYYY-MM."""
    match = _MONTH.match((value or "").strip())
    if not match:
        raise ValueError("month must be YYYY-MM")
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise ValueError("month must be YYYY-MM")
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def tone_for(oppose: int, support: int, other: int) -> str:
    """Map stance counts to a tile tone."""
    total = oppose + support + other
    if total == 0:
        return "none"
    if oppose / total >= 0.70:
        return "oppose"
    if support / total >= 0.70:
        return "support"
    return "mixed"


class LocationViewsRepository:
    """Sentiment tiles and per-location statement lists by month."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, location_id: uuid.UUID) -> Location | None:
        """Return one location."""
        return self.session.get(Location, location_id)

    def latest_month_with_statements(self) -> str | None:
        """Return YYYY-MM for the newest meeting that has a statement, if any."""
        row = (
            self.session.query(Meeting.meeting_date)
            .join(Fact, Fact.meeting_id == Meeting.id)
            .filter(Fact.kind == "statement", Meeting.meeting_date.is_not(None))
            .order_by(Meeting.meeting_date.desc())
            .first()
        )
        if row is None or row[0] is None:
            return None
        return f"{row[0].year:04d}-{row[0].month:02d}"

    def sentiment_for_month(self, month: str) -> list[dict]:
        """Return every location with stance counts for the given month."""
        start, end = parse_month(month)
        locations = self.session.query(Location).order_by(Location.name).all()
        counts: dict[uuid.UUID, dict[str, int]] = {
            location.id: {"oppose": 0, "support": 0, "other": 0} for location in locations
        }
        rows = (
            self.session.query(Meeting.location_id, Fact.stance)
            .join(Fact, Fact.meeting_id == Meeting.id)
            .filter(
                Fact.kind == "statement",
                Fact.stance.is_not(None),
                Meeting.location_id.is_not(None),
                Meeting.meeting_date >= start,
                Meeting.meeting_date < end,
            )
            .all()
        )
        for location_id, stance in rows:
            if location_id not in counts:
                continue
            if stance == "oppose":
                counts[location_id]["oppose"] += 1
            elif stance == "support":
                counts[location_id]["support"] += 1
            else:
                counts[location_id]["other"] += 1

        result = []
        for location in locations:
            bucket = counts[location.id]
            oppose = bucket["oppose"]
            support = bucket["support"]
            other = bucket["other"]
            total = oppose + support + other
            result.append(
                {
                    "location_id": location.id,
                    "name": location.name,
                    "oppose": oppose,
                    "support": support,
                    "other": other,
                    "total": total,
                    "tone": tone_for(oppose, support, other),
                }
            )
        return result

    def statements_for_month(self, location_id: uuid.UUID, month: str) -> list[dict]:
        """Return dated statements for one location in the given month."""
        start, end = parse_month(month)
        rows = (
            self.session.query(Fact, Meeting, Person, Project)
            .join(Meeting, Fact.meeting_id == Meeting.id)
            .outerjoin(Person, Fact.person_id == Person.id)
            .outerjoin(Project, Fact.project_id == Project.id)
            .filter(
                Fact.kind == "statement",
                Meeting.location_id == location_id,
                Meeting.meeting_date >= start,
                Meeting.meeting_date < end,
            )
            .order_by(Meeting.meeting_date.asc().nulls_last(), Fact.start_seconds.asc().nulls_last())
            .all()
        )
        views = []
        for fact, meeting, person, project in rows:
            views.append(
                {
                    "fact_id": fact.id,
                    "person_id": person.id if person is not None else None,
                    "person_name": person.name if person is not None else None,
                    "person_kind": person.kind if person is not None else None,
                    "stance": fact.stance,
                    "body": fact.body or "",
                    "excerpt": fact.excerpt,
                    "project_id": project.id if project is not None else None,
                    "project_name": project.name if project is not None else None,
                    "meeting_date": meeting.meeting_date,
                    "start_seconds": fact.start_seconds,
                }
            )
        return views

    def projects_for_month(self, location_id: uuid.UUID, month: str) -> list[dict]:
        """Return projects/policies discussed or updated in the selected month.

        Only includes a project when that month has at least one linked statement
        or dated finding. Empty months return an empty list (no all-projects fallback).
        """
        start, end = parse_month(month)
        count_rows = (
            self.session.query(Fact.project_id, func.count(Fact.id))
            .join(Meeting, Fact.meeting_id == Meeting.id)
            .filter(
                Fact.kind == "statement",
                Fact.project_id.is_not(None),
                Meeting.location_id == location_id,
                Meeting.meeting_date >= start,
                Meeting.meeting_date < end,
            )
            .group_by(Fact.project_id)
            .all()
        )
        statement_counts = {project_id: count for project_id, count in count_rows}

        finding_rows = (
            self.session.query(ProjectFinding)
            .join(Project, ProjectFinding.project_id == Project.id)
            .filter(
                Project.location_id == location_id,
                ProjectFinding.finding_date >= start,
                ProjectFinding.finding_date < end,
            )
            .order_by(ProjectFinding.finding_date.asc().nulls_last(), ProjectFinding.id.asc())
            .all()
        )
        findings_by_project: dict[uuid.UUID, list] = {}
        for finding in finding_rows:
            findings_by_project.setdefault(finding.project_id, []).append(finding)

        project_ids = set(statement_counts) | set(findings_by_project)
        if not project_ids:
            return []

        projects = (
            self.session.query(Project)
            .filter(Project.id.in_(project_ids))
            .order_by(Project.data_center.desc(), Project.name)
            .all()
        )

        views = []
        for project in projects:
            month_findings = findings_by_project.get(project.id, [])
            views.append(
                {
                    "project_id": project.id,
                    "name": project.name,
                    "code": project.code,
                    "kind": project.kind,
                    "about": project.about,
                    "stage": project.stage,
                    "stage_as_of": project.stage_as_of,
                    "data_center": bool(project.data_center),
                    "signals": project.signals or [],
                    "statement_count": statement_counts.get(project.id, 0),
                    "findings": [
                        {
                            "finding_id": finding.id,
                            "finding_date": finding.finding_date,
                            "kind": finding.kind,
                            "stage": finding.stage,
                            "body": finding.body,
                            "excerpt": finding.excerpt,
                        }
                        for finding in month_findings
                    ],
                }
            )
        return views
