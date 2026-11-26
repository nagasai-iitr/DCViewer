"""Liveness probe."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Report that the API process is up."""
    return {"status": "ok"}
