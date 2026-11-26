"""Import every model so the metadata includes each table."""
from __future__ import annotations


from app.models.base import Base
from app.models.corpus_run import CorpusRun
from app.models.fact import Fact
from app.models.job import Job
from app.models.location import Location
from app.models.meeting import Meeting
from app.models.person import Person
from app.models.project import Project
from app.models.project_finding import ProjectFinding
from app.models.section import Section, SectionSpeaker

__all__ = [
    "Base",
    "CorpusRun",
    "Fact",
    "Job",
    "Location",
    "Meeting",
    "Person",
    "Project",
    "ProjectFinding",
    "Section",
    "SectionSpeaker",
]
