"""Location sentiment for one calendar month."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class LocationSentimentResponse(BaseModel):
    """Stance totals and dominant tone for one location in one month."""

    location_id: uuid.UUID
    name: str
    oppose: int
    support: int
    other: int
    total: int
    tone: str
