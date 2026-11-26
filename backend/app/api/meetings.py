"""Meeting list reads."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import meetings
from app.dto.response import MeetingResponse
from app.repositories import MeetingRepository

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    limit: int = 50,
    relevant_only: bool = False,
    repo: MeetingRepository = Depends(meetings),
) -> list[MeetingResponse]:
    """Return stored meetings. relevant_only keeps transcripts that named a data center."""
    limit = min(max(limit, 1), 200)
    return [MeetingResponse.from_meeting(row) for row in repo.recent(limit, relevant_only)]
