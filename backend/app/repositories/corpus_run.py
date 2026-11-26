"""Corpus run persistence."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import CorpusRun


class CorpusRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: uuid.UUID) -> CorpusRun | None:
        return self.session.get(CorpusRun, run_id)

    def recent(self, limit: int) -> list[CorpusRun]:
        return (
            self.session.query(CorpusRun)
            .order_by(CorpusRun.created_at.desc())
            .limit(limit)
            .all()
        )
