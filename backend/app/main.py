"""DCViewer API entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.database import init_db
from app.logging_config import configure_logging
from app.workers.ingest_worker import JobWorker

configure_logging()
logger = logging.getLogger("app.api")
worker = JobWorker()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create tables and start the background ingest worker."""
    init_db()
    worker.start()
    yield
    worker.stop()


app = FastAPI(
    title="DCViewer",
    description=(
        "Ingest public meeting captions, extract data-center discussions, and read "
        "location sentiment, projects, and people timelines. Bulk corpus ingest reads "
        "a mounted folder with manifest.json and queues transcripts for the worker."
    ),
    lifespan=lifespan,
)
app.include_router(api_router)
