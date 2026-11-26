"""Project and policy rows, reused by code when present, otherwise by name."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Meeting, Project, ProjectFinding
from app.utils import code_key, codes_match, name_looks_like_code, normalize, project_names_match

STAGES = {"proposed", "hearing", "approved", "denied", "moratorium", "withdrawn", "unknown"}
FINDING_KINDS = {"stage_change", "update", "decision", "concern", "negative"}
COVERAGE = {"sufficient", "limited", "insufficient"}


def _signals(values) -> list[str]:
    """Keep only the signal names the pipeline knows."""
    allowed = {"data_center", "water", "power", "noise", "radiation", "jobs", "tax", "siting"}
    return sorted({item for item in (values or []) if item in allowed})


def _spoken_code(spoken: dict) -> tuple[str | None, str | None]:
    """Return display code and normalized code_key from model output.

    Accepts either `code` (project extract) or `project_code` (speech/voices).
    When the model left code empty but the name is itself an ordinance,
    resolution, petition, or project code, use the name as the code.
    """
    raw = (spoken.get("code") or spoken.get("project_code") or "").strip() or None
    if not raw:
        name = (spoken.get("name") or "").strip()
        if name_looks_like_code(name):
            raw = name
    return raw, code_key(raw)


class ProjectRepository:
    """Reads and inserts projects, policies, and their dated findings."""

    def __init__(self, session: Session) -> None:
        """Keep the session this repository writes through."""
        self.session = session

    def find_or_create(self, location_id, spoken: dict, meeting_date: date | None) -> Project:
        """Reuse a project when code matches, otherwise when the name matches.

        A petition, case, ordinance, or project code is the stable identifier
        when the transcript gives one. Name matching is the fallback.
        """
        name = (spoken.get("name") or "").strip()
        name_key = normalize(name)
        code, key = _spoken_code(spoken)
        found = self._find_existing(location_id, name, name_key, code, key)
        if found is None:
            stage = spoken.get("stage") if spoken.get("stage") in STAGES else "unknown"
            found = Project(
                location_id=location_id,
                name=name or code or "unnamed",
                name_key=name_key or key or "unnamed",
                code=code,
                code_key=key,
                kind=spoken.get("kind") if spoken.get("kind") in {"project", "policy"} else "project",
                about=spoken.get("about"),
                stage=stage,
                stage_as_of=meeting_date,
                data_center=bool(spoken.get("data_center")),
                signals=_signals(spoken.get("signals")),
            )
            self.session.add(found)
            self.session.flush()
            return found
        self._fill_gaps(found, spoken, code, key)
        return found

    def _find_existing(
        self, location_id, name: str, name_key: str, code: str | None, key: str | None
    ) -> Project | None:
        """Prefer code match inside the location, then exact name, then fuzzy name."""
        query = self.session.query(Project)
        if location_id is None:
            query = query.filter(Project.location_id.is_(None))
        else:
            query = query.filter_by(location_id=location_id)

        if key:
            by_code = query.filter_by(code_key=key).one_or_none()
            if by_code is not None:
                return by_code
            # Soft code match for label variants (Ordinance 2025-23 vs 2025-23).
            coded = query.filter(Project.code_key.is_not(None)).all()
            close_codes = [row for row in coded if codes_match(code, row.code)]
            if len(close_codes) == 1:
                return close_codes[0]

        if name_key:
            exact = query.filter_by(name_key=name_key).one_or_none()
            if exact is not None:
                return exact
            candidates = query.all()
            close = [row for row in candidates if project_names_match(name, row.name)]
            if len(close) == 1:
                return close[0]
        return None

    def _fill_gaps(self, found: Project, spoken: dict, code: str | None, key: str | None) -> None:
        """Fill blank fields; never erase an existing code with a weaker blank."""
        if not found.about and spoken.get("about"):
            found.about = spoken.get("about")
        if spoken.get("data_center"):
            found.data_center = True
        found.signals = sorted(set(found.signals or []) | set(_signals(spoken.get("signals"))))
        if code and key:
            if not found.code_key:
                found.code = code
                found.code_key = key
            elif codes_match(code, found.code) and len(code) > len(found.code or ""):
                # Keep the more explicit spoken form (Ordinance 2025-23 over 2025-23).
                found.code = code
                found.code_key = key

    def add_finding(
        self,
        project: Project,
        meeting,
        section,
        spoken: dict,
        meeting_date: date | None,
        prior_stage: str | None = None,
    ) -> ProjectFinding | None:
        """Append one dated finding. Negative findings need sufficient coverage."""
        kind = spoken.get("kind") if spoken.get("kind") in FINDING_KINDS else "update"
        coverage = spoken.get("coverage") if spoken.get("coverage") in COVERAGE else "sufficient"
        if kind == "negative" and coverage != "sufficient":
            return None
        body = (spoken.get("body") or spoken.get("about") or "").strip()
        if not body:
            return None
        stage = spoken.get("stage") if spoken.get("stage") in STAGES else None
        finding = ProjectFinding(
            project=project,
            meeting=meeting,
            section=section,
            finding_date=meeting_date,
            kind=kind,
            stage=stage,
            prior_stage=prior_stage,
            body=body,
            excerpt=spoken.get("excerpt"),
            coverage=coverage,
            signals=_signals(spoken.get("signals") or project.signals),
            start_seconds=getattr(section, "start_seconds", None) if section is not None else None,
            end_seconds=getattr(section, "end_seconds", None) if section is not None else None,
        )
        self.session.add(finding)
        self.session.flush()
        return finding

    def record_meeting_update(
        self,
        project: Project,
        meeting,
        section,
        spoken: dict,
        meeting_date: date | None,
    ) -> list[ProjectFinding]:
        """Append findings for this meeting and move the current stage when dated newer."""
        prior_stage = project.stage
        stage = spoken.get("stage") if spoken.get("stage") in STAGES else None
        created: list[ProjectFinding] = []
        code, key = _spoken_code(spoken)
        self._fill_gaps(project, spoken, code, key)

        if stage and (project.stage_as_of is None or (meeting_date and meeting_date >= project.stage_as_of)):
            if stage != prior_stage:
                row = self.add_finding(
                    project,
                    meeting,
                    section,
                    {
                        "kind": "stage_change",
                        "stage": stage,
                        "body": spoken.get("about") or f"Stage moved from {prior_stage} to {stage}.",
                        "excerpt": spoken.get("excerpt"),
                        "coverage": "sufficient",
                        "signals": spoken.get("signals"),
                    },
                    meeting_date,
                    prior_stage=prior_stage,
                )
                if row is not None:
                    created.append(row)
            project.stage = stage
            project.stage_as_of = meeting_date

        for item in spoken.get("findings") or []:
            if not isinstance(item, dict):
                item = {"body": str(item), "kind": "update"}
            row = self.add_finding(
                project,
                meeting,
                section,
                item,
                meeting_date,
                prior_stage=prior_stage if item.get("kind") == "stage_change" else None,
            )
            if row is not None:
                created.append(row)

        if not created and (spoken.get("about") or "").strip():
            row = self.add_finding(
                project,
                meeting,
                section,
                {
                    "kind": "update",
                    "stage": stage,
                    "body": spoken.get("about"),
                    "excerpt": spoken.get("excerpt"),
                    "coverage": spoken.get("coverage") or "sufficient",
                    "signals": spoken.get("signals"),
                },
                meeting_date,
            )
            if row is not None:
                created.append(row)
        return created

    def get(self, project_id) -> Project | None:
        """Return one project."""
        return self.session.get(Project, project_id)

    def recent(self, limit: int) -> list[Project]:
        """Return projects, data-center ones first."""
        return (
            self.session.query(Project)
            .order_by(Project.data_center.desc(), Project.name)
            .limit(limit)
            .all()
        )

    def findings_for(self, project_id) -> list[tuple[ProjectFinding, Meeting]]:
        """Return dated findings for one project, oldest first."""
        return (
            self.session.query(ProjectFinding, Meeting)
            .join(Meeting, ProjectFinding.meeting_id == Meeting.id)
            .filter(ProjectFinding.project_id == project_id)
            .order_by(ProjectFinding.finding_date.asc().nulls_last(), ProjectFinding.id.asc())
            .all()
        )
