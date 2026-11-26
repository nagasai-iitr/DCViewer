"""HTTP routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import corpus, health, jobs, locations, meetings, people, projects, transcripts

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router)
api_router.include_router(meetings.router)
api_router.include_router(people.router)
api_router.include_router(locations.router)
api_router.include_router(projects.router)
api_router.include_router(transcripts.router)
api_router.include_router(corpus.router)
