# DCViewer evaluation (v1)

Small, manually reviewed accuracy harness for assignment §4.

Gold labels in `gold/relevance.jsonl` were written from **short corpus transcripts**
(hand-read), not copied from Postgres `relevant` flags.

1. **Meeting relevance** — gold vs offline hard-regex over the full caption file
2. **Passage hard-regex gate** — gold windows vs `data_center` hard patterns
3. **Citation span-check** — seeded DB `facts.excerpt` must appear in the source transcript

People / stance / timeline scoring is intentionally out of scope for v1.

## Prerequisites

- `docker compose up` so Postgres on `localhost:5434` has the seed (or ingested) data
- Corpus unzipped under `DCViewer/data_center_candidate_transcripts_2025-11-04_to_2026-11-04/`
- Python 3 with `psycopg`:

```bash
python3 -m pip install 'psycopg[binary]'
```

## Run

From the `DCViewer/` directory:

```bash
python3 eval/run_eval.py
```

Optional env:

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql://gathergov:gathergov@localhost:5434/gathergov` |
| `CORPUS_PATH` | `./data_center_candidate_transcripts_2025-11-04_to_2026-11-04` |

## Outputs

| File | Contents |
|------|----------|
| `eval/results/latest.json` | Precision / recall / F1 + citation support rate |
| `eval/results/errors.jsonl` | Concrete misses (FN/FP, excerpt not found, …) |

Gold labels live in `eval/gold/relevance.jsonl` (`positive` / `negative` / `ambiguous`). Ambiguous rows are listed but excluded from P/R.
