"""Start a bulk corpus ingest from a mounted folder."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CorpusRunRequest(BaseModel):
    """Path is inside the API container (host folder must be volume-mounted)."""

    corpus_path: str = Field(
        default="/data/corpus",
        description="Absolute path to the folder that contains manifest.json and transcripts/.",
    )
    limit: int | None = Field(
        default=4,
        ge=1,
        le=500,
        description="Max new transcripts to queue in this run. Null means no extra cap.",
    )
    location_ids: list[int] | None = Field(
        default=None,
        description="Optional short location ids from the manifest. Null = all locations.",
    )
    skip_existing: bool = Field(
        default=True,
        description="Skip transcript ids that are already ingested or queued.",
    )
