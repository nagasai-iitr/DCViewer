"""Location sentiment tiles and monthly detail reads."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import location_views
from app.dto.response import (
    LocationProjectResponse,
    LocationSentimentResponse,
    LocationStatementResponse,
)
from app.repositories import LocationViewsRepository

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/default-month")
def default_month(repo: LocationViewsRepository = Depends(location_views)) -> dict:
    """Return the newest month with statement data, or 2026-12 when none exist."""
    return {"month": repo.latest_month_with_statements() or "2026-12"}


@router.get("/sentiment", response_model=list[LocationSentimentResponse])
def location_sentiment(
    month: str,
    repo: LocationViewsRepository = Depends(location_views),
) -> list[LocationSentimentResponse]:
    """Return every location with stance totals and tone for one calendar month."""
    try:
        rows = repo.sentiment_for_month(month)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return [LocationSentimentResponse(**row) for row in rows]


@router.get("/{location_id}/statements", response_model=list[LocationStatementResponse])
def location_statements(
    location_id: uuid.UUID,
    month: str,
    repo: LocationViewsRepository = Depends(location_views),
) -> list[LocationStatementResponse]:
    """Return people and stance excerpts for one location in one calendar month."""
    if repo.get(location_id) is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    try:
        rows = repo.statements_for_month(location_id, month)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return [LocationStatementResponse(**row) for row in rows]


@router.get("/{location_id}/projects", response_model=list[LocationProjectResponse])
def location_projects(
    location_id: uuid.UUID,
    month: str,
    repo: LocationViewsRepository = Depends(location_views),
) -> list[LocationProjectResponse]:
    """Return projects and policies for one location in one calendar month."""
    if repo.get(location_id) is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    try:
        rows = repo.projects_for_month(location_id, month)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return [LocationProjectResponse(**row) for row in rows]
