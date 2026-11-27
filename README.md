# DCViewer

Student assignment submission: extract **data-center** discussions from municipal meeting captions, store people / projects / stances, and explore them in a simple web UI.

Evaluators should be able to clone this repo, add API keys + the provided transcript corpus, and run everything with Docker Compose — no dependency on other prototypes.

## Capabilities

- **Hybrid relevance gate** — regex for clear “data center / datacenter / …” phrases, then JEV on soft/borderline windows; full LLM extraction only when a data center is found.
- **People & dated stances** — residents, petitioners, council, staff.
- **Projects & policies** — optional formal **codes** (ordinance / project codes) preferred over name matching.
- **UI**
  - Monthly location tiles colored by community stance
  - Side panel: projects + people for that month
  - Project view: findings + people’s views
  - Person view: stance timeline over meetings
  - **Run corpus**: queue transcripts from the local corpus folder (processed one-by-one by the worker)

## Prerequisites

- Docker Desktop
- The assignment corpus zip, unzipped **into this repo directory** so you have:

```text
DCViewer/
  data_center_candidate_transcripts_2025-11-04_to_2026-11-04/
    manifest.json
    transcripts/
      ....json
```

- API keys in `.env` (see `.env.example`):

```bash
cp .env.example .env
# set JEV_API_KEY and GOOGLE_API_KEY
```

## Run

```bash
cd DCViewer
docker compose up --build
```

| Service | URL |
|---------|-----|
| UI | http://localhost:8080 |
| API / OpenAPI | http://localhost:8001/docs |
| Postgres | localhost:5434 |

### Demo database

On **first** Postgres start, `db/seed.sql` loads a demo dataset (Hermantown, Joliet, Clinton, Augusta meetings already processed) so you can explore the UI without waiting for LLM ingest.

To reset the database and reload the seed:

```bash
docker compose down -v
docker compose up --build
```

(`-v` deletes the Postgres volume; init scripts run again.)

### Ingest more transcripts

1. Confirm the corpus folder path above exists in this directory.
2. Open the UI → **Run from folder**.
3. Leave path as `/data/corpus` (Compose mounts your local corpus folder there).
4. Set a small **Max new transcripts** (e.g. 2–4) and click **Run**.

Browsers cannot grant a host filesystem path to the server. That is why the corpus must live **inside this project** and be mounted into the API container.

## Project layout

```text
DCViewer/
  README.md
  CONCEPTS.md                   # definitions: section, fact, project, …
  ARCHITECTURE.pdf              # system design boards
  DCViewer_walkthrough_vo.mp4   # short evaluator walkthrough
  docker-compose.yml
  .env.example
  db/seed.sql                   # demo data for first boot
  data_center_candidate_.../    # YOU add this (unzipped corpus)
  backend/                      # FastAPI
  frontend/                     # Vite + React + nginx
  eval/                         # relevance + citation accuracy harness
```

## Evaluation

With Compose up and the corpus folder present:

```bash
python3 -m pip install 'psycopg[binary]'
python3 eval/run_eval.py
```

See `eval/README.md`. Metrics land in `eval/results/latest.json`.

## Notes for evaluators

- Definitions of **location / meeting / section / person / fact / project / finding**: see [`CONCEPTS.md`](CONCEPTS.md).
- Full corpus ingest (~3k transcripts) is slow and costs model calls — use `limit` in the Run panel.
- ASR noise can create near-duplicate project/person names; codes help when present.
- Architecture boards: `ARCHITECTURE.pdf`. Walkthrough video: `DCViewer_walkthrough_vo.mp4`.
