"""Bulk ingest from a mounted corpus folder containing manifest.json."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import default_corpus_path
from app.dto.request.corpus import CorpusRunRequest
from app.dto.response.corpus_run import CorpusRunResponse
from app.repositories.corpus_run import CorpusRunRepository
from app.services.corpus_ingest import enqueue_corpus

router = APIRouter(prefix="/corpus", tags=["corpus"])
logger = logging.getLogger("app.api.corpus")


@router.get("/default-path")
def corpus_default_path() -> dict:
    """Return the default mounted corpus path for the UI."""
    return {"corpus_path": str(default_corpus_path())}


@router.post("/runs", response_model=CorpusRunResponse)
def start_corpus_run(body: CorpusRunRequest, db: Session = Depends(get_db)) -> CorpusRunResponse:
    """Queue transcript jobs from manifest.json under corpus_path, one by one via the worker.

    The browser cannot grant a real host filesystem path. Mount the corpus into the
    API container (Compose does this at /data/corpus) and pass that container path.
    """
    path = Path(body.corpus_path or default_corpus_path())
    try:
        run = enqueue_corpus(
            db,
            path,
            limit=body.limit,
            location_ids=body.location_ids,
            skip_existing=body.skip_existing,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("corpus enqueue failed")
        raise HTTPException(status_code=500, detail=str(error)) from error
    return CorpusRunResponse.from_run(run)


@router.get("/runs", response_model=list[CorpusRunResponse])
def list_corpus_runs(limit: int = 20, db: Session = Depends(get_db)) -> list[CorpusRunResponse]:
    """Return recent corpus runs."""
    limit = min(max(limit, 1), 100)
    rows = CorpusRunRepository(db).recent(limit)
    return [CorpusRunResponse.from_run(row) for row in rows]


@router.get("/runs/{run_id}", response_model=CorpusRunResponse)
def get_corpus_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> CorpusRunResponse:
    """Return one corpus run."""
    run = CorpusRunRepository(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Corpus run not found.")
    return CorpusRunResponse.from_run(run)
