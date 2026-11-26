"""Repositories, one module per stored model."""
from __future__ import annotations

from app.repositories.corpus_run import CorpusRunRepository
from app.repositories.fact import FactRepository
from app.repositories.job import JobRepository
from app.repositories.location import LocationRepository
from app.repositories.location_views import LocationViewsRepository
from app.repositories.meeting import MeetingRepository
from app.repositories.person import PersonRepository
from app.repositories.project import ProjectRepository
from app.repositories.section import SectionRepository
from app.repositories.section_speaker import SectionSpeakerRepository

__all__ = [
    "CorpusRunRepository",
    "FactRepository",
    "JobRepository",
    "LocationRepository",
    "LocationViewsRepository",
    "MeetingRepository",
    "PersonRepository",
    "ProjectRepository",
    "SectionRepository",
    "SectionSpeakerRepository",
]
