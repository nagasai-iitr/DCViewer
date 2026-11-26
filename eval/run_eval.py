#!/usr/bin/env python3
"""Score DCViewer against gold relevance labels + citation span-check.

Run from the DCViewer directory with Compose Postgres up:

  python eval/run_eval.py

Writes eval/results/latest.json and eval/results/errors.jsonl.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.keywords import data_center_matches, soft_signals  # noqa: E402

GOLD_PATH = Path(__file__).resolve().parent / "gold" / "relevance.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_DB = "postgresql://gathergov:gathergov@localhost:5434/gathergov"
DEFAULT_CORPUS = ROOT / "data_center_candidate_transcripts_2025-11-04_to_2026-11-04"

WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return WS_RE.sub(" ", (text or "").casefold()).strip()


def load_gold(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def connect(database_url: str):
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "psycopg is required. Install with: python3 -m pip install 'psycopg[binary]'"
        ) from exc
    # Accept SQLAlchemy-style URLs from .env
    url = database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def fetch_meeting_relevance(conn) -> dict[int, bool]:
    with conn.cursor() as cur:
        cur.execute("SELECT transcript_id, relevant FROM meetings")
        return {int(tid): bool(rel) for tid, rel in cur.fetchall()}


def fetch_facts_with_excerpts(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.id::text, m.transcript_id, f.excerpt
            FROM facts f
            JOIN meetings m ON m.id = f.meeting_id
            WHERE f.excerpt IS NOT NULL AND length(btrim(f.excerpt)) > 0
            """
        )
        return [
            {"fact_id": fid, "transcript_id": int(tid), "excerpt": excerpt}
            for fid, tid, excerpt in cur.fetchall()
        ]


def corpus_file_for(corpus_path: Path, transcript_id: int) -> Path | None:
    matches = list((corpus_path / "transcripts").glob(f"*_{transcript_id}.json"))
    return matches[0] if matches else None


def transcript_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return " ".join((row.get("text") or "") for row in data if isinstance(row, dict))
    if isinstance(data, dict):
        caps = data.get("captions") or data.get("segments") or []
        if isinstance(caps, list):
            return " ".join((row.get("text") or "") for row in caps if isinstance(row, dict))
    return ""


_transcript_cache: dict[int, str | None] = {}


def load_transcript(corpus_path: Path, transcript_id: int) -> str | None:
    if transcript_id in _transcript_cache:
        return _transcript_cache[transcript_id]
    path = corpus_file_for(corpus_path, transcript_id)
    if path is None:
        _transcript_cache[transcript_id] = None
        return None
    text = transcript_text(path)
    _transcript_cache[transcript_id] = text
    return text


def prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
    }


def predict_meeting_hard_gate(corpus_path: Path, transcript_ids: set[int]) -> dict[int, bool | None]:
    """Offline first-stage gate: hard DC regex over the full caption text.

    Production also runs JEV on soft windows; this harness scores the cheap stage
    so gold can cover small transcripts that were never ingested into Postgres.
    """
    out: dict[int, bool | None] = {}
    for tid in transcript_ids:
        text = load_transcript(corpus_path, tid)
        if text is None:
            out[tid] = None
            continue
        out[tid] = bool(data_center_matches(text))
    return out


def score_meeting(
    gold: list[dict],
    predictions: dict[int, bool | None],
    *,
    predictor: str,
) -> tuple[dict, list[dict]]:
    tp = fp = fn = 0
    errors: list[dict] = []
    ambiguous: list[dict] = []
    missing: list[dict] = []
    scored = 0

    for row in gold:
        if row.get("level") != "meeting":
            continue
        label = row["label"]
        tid = int(row["transcript_id"])
        if label == "ambiguous":
            ambiguous.append({"id": row["id"], "transcript_id": tid, "notes": row.get("notes")})
            continue
        pred = predictions.get(tid, None)
        if pred is None:
            missing.append({"id": row["id"], "transcript_id": tid, "notes": row.get("notes")})
            errors.append(
                {
                    "kind": "meeting_missing",
                    "id": row["id"],
                    "transcript_id": tid,
                    "gold": label,
                    "notes": row.get("notes"),
                }
            )
            continue
        gold_pos = label == "positive"
        scored += 1
        if gold_pos and pred:
            tp += 1
        elif gold_pos and not pred:
            fn += 1
            errors.append(
                {
                    "kind": "meeting_fn",
                    "id": row["id"],
                    "transcript_id": tid,
                    "gold": label,
                    "pred_relevant": pred,
                    "notes": row.get("notes"),
                }
            )
        elif not gold_pos and pred:
            fp += 1
            errors.append(
                {
                    "kind": "meeting_fp",
                    "id": row["id"],
                    "transcript_id": tid,
                    "gold": label,
                    "pred_relevant": pred,
                    "notes": row.get("notes"),
                }
            )

    metrics = prf(tp, fp, fn)
    metrics.update(
        {
            "scored": scored,
            "ambiguous": len(ambiguous),
            "missing_meetings": len(missing),
            "ambiguous_rows": ambiguous,
            "missing_rows": missing,
            "predictor": predictor,
        }
    )
    return metrics, errors


def score_passage(gold: list[dict]) -> tuple[dict, list[dict]]:
    tp = fp = fn = 0
    errors: list[dict] = []
    ambiguous_notes: list[dict] = []
    scored = 0

    for row in gold:
        if row.get("level") != "passage":
            continue
        passage = row.get("passage") or ""
        hard = bool(data_center_matches(passage))
        soft = soft_signals(passage)
        label = row["label"]
        if label == "ambiguous":
            ambiguous_notes.append(
                {
                    "id": row["id"],
                    "transcript_id": row["transcript_id"],
                    "hard_match": hard,
                    "soft_signals": soft,
                    "notes": row.get("notes"),
                }
            )
            continue
        gold_pos = label == "positive"
        scored += 1
        if gold_pos and hard:
            tp += 1
        elif gold_pos and not hard:
            fn += 1
            errors.append(
                {
                    "kind": "passage_fn",
                    "id": row["id"],
                    "transcript_id": row["transcript_id"],
                    "gold": label,
                    "hard_match": hard,
                    "soft_signals": soft,
                    "notes": row.get("notes"),
                }
            )
        elif not gold_pos and hard:
            fp += 1
            errors.append(
                {
                    "kind": "passage_fp",
                    "id": row["id"],
                    "transcript_id": row["transcript_id"],
                    "gold": label,
                    "hard_match": hard,
                    "soft_signals": soft,
                    "notes": row.get("notes"),
                }
            )

    metrics = prf(tp, fp, fn)
    metrics.update(
        {
            "scored": scored,
            "ambiguous": len(ambiguous_notes),
            "ambiguous_rows": ambiguous_notes,
            "note": "Hard regex only; production gate also uses JEV on soft windows.",
        }
    )
    return metrics, errors


def score_citations(conn, corpus_path: Path, max_errors: int = 50) -> tuple[dict, list[dict]]:
    facts = fetch_facts_with_excerpts(conn)
    counts = Counter()
    errors: list[dict] = []

    for fact in facts:
        excerpt = fact["excerpt"] or ""
        norm_ex = normalize(excerpt)
        if len(norm_ex) < 8:
            counts["too_short"] += 1
            if len(errors) < max_errors:
                errors.append(
                    {
                        "kind": "citation_too_short",
                        "fact_id": fact["fact_id"],
                        "transcript_id": fact["transcript_id"],
                        "excerpt": excerpt[:160],
                    }
                )
            continue
        text = load_transcript(corpus_path, fact["transcript_id"])
        if text is None:
            counts["transcript_missing"] += 1
            if len(errors) < max_errors:
                errors.append(
                    {
                        "kind": "citation_transcript_missing",
                        "fact_id": fact["fact_id"],
                        "transcript_id": fact["transcript_id"],
                    }
                )
            continue
        if norm_ex in normalize(text):
            counts["pass"] += 1
        else:
            counts["not_found"] += 1
            if len(errors) < max_errors:
                errors.append(
                    {
                        "kind": "citation_not_found",
                        "fact_id": fact["fact_id"],
                        "transcript_id": fact["transcript_id"],
                        "excerpt": excerpt[:220],
                    }
                )

    eligible = counts["pass"] + counts["not_found"] + counts["too_short"] + counts["transcript_missing"]
    support_rate = (counts["pass"] / eligible) if eligible else None
    metrics = {
        "eligible_facts": eligible,
        "pass": counts["pass"],
        "not_found": counts["not_found"],
        "too_short": counts["too_short"],
        "transcript_missing": counts["transcript_missing"],
        "support_rate": round(support_rate, 4) if support_rate is not None else None,
        "note": "Normalized substring check; does not score semantic entailment.",
        "errors_listed": min(len(errors), max_errors),
    }
    return metrics, errors


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DB)
    corpus_env = os.environ.get("CORPUS_PATH")
    corpus_path = Path(corpus_env) if corpus_env else DEFAULT_CORPUS
    if not corpus_path.is_absolute():
        corpus_path = (ROOT / corpus_path).resolve()

    if not GOLD_PATH.exists():
        raise SystemExit(f"Missing gold file: {GOLD_PATH}")
    if not (corpus_path / "transcripts").is_dir():
        raise SystemExit(
            f"Corpus not found at {corpus_path}. Unzip the assignment corpus into DCViewer/."
        )

    gold = load_gold(GOLD_PATH)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    meeting_ids = {int(r["transcript_id"]) for r in gold if r.get("level") == "meeting"}
    meeting_preds = predict_meeting_hard_gate(corpus_path, meeting_ids)
    meeting_metrics, meeting_errors = score_meeting(
        gold,
        meeting_preds,
        predictor="corpus_hard_regex",
    )
    passage_metrics, passage_errors = score_passage(gold)

    citation_metrics: dict = {
        "eligible_facts": 0,
        "pass": 0,
        "not_found": 0,
        "too_short": 0,
        "transcript_missing": 0,
        "support_rate": None,
        "note": "Skipped (database unavailable).",
        "errors_listed": 0,
    }
    citation_errors: list[dict] = []
    try:
        with connect(database_url) as conn:
            citation_metrics, citation_errors = score_citations(conn, corpus_path)
    except Exception as exc:  # noqa: BLE001 - eval should still report gate metrics
        citation_metrics["note"] = f"Skipped ({exc.__class__.__name__}: {exc})"

    all_errors = meeting_errors + passage_errors + citation_errors
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_path": str(GOLD_PATH.relative_to(ROOT)),
        "corpus_path": str(corpus_path),
        "gold_rows": len(gold),
        "gold_note": (
            "Hand labels on small corpus transcripts (not copied from DB relevant flags). "
            "Meeting predictor = hard regex over full caption text."
        ),
        "meeting": meeting_metrics,
        "passage": passage_metrics,
        "citation": citation_metrics,
        "limitations": [
            "Meeting/passage scores use hard regex only (production also uses JEV).",
            "Does not score people, stances, or timelines.",
            "Citation check is span containment on seeded DB facts, not claim entailment.",
        ],
    }

    latest = RESULTS_DIR / "latest.json"
    latest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    errors_path = RESULTS_DIR / "errors.jsonl"
    with errors_path.open("w", encoding="utf-8") as handle:
        for row in all_errors:
            handle.write(json.dumps(row) + "\n")

    print("DCViewer eval")
    print(
        f"  meeting  P={meeting_metrics['precision']} R={meeting_metrics['recall']} "
        f"F1={meeting_metrics['f1']} (scored={meeting_metrics['scored']})"
    )
    print(
        f"  passage  P={passage_metrics['precision']} R={passage_metrics['recall']} "
        f"F1={passage_metrics['f1']} (scored={passage_metrics['scored']})"
    )
    print(
        f"  citation support_rate={citation_metrics['support_rate']} "
        f"pass={citation_metrics['pass']}/{citation_metrics['eligible_facts']}"
    )
    print(f"  wrote {latest.relative_to(ROOT)}")
    print(f"  wrote {errors_path.relative_to(ROOT)} ({len(all_errors)} error rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
