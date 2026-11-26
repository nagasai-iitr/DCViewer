"""Environment and paths. Secrets stay in the environment and are never logged."""
from __future__ import annotations

import os
from pathlib import Path

# backend/ (Docker WORKDIR /app)
BACKEND_ROOT = Path(__file__).resolve().parents[1]
# prototype_5/ on the host; inside the image this may not exist — env vars still win.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    """Read .env files without overwriting values already set in the process."""
    for path in (PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def env(name: str) -> str:
    """Return one required environment value."""
    load_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is missing")
    return value


def database_url() -> str:
    """Return the Postgres URL, defaulting to the local Docker database."""
    load_env()
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://gathergov:gathergov@localhost:5434/gathergov",
    )


def model_concurrency() -> int:
    """How many model requests may be in flight at once."""
    load_env()
    raw = os.environ.get("MODEL_CONCURRENCY", "8").strip() or "8"
    try:
        value = int(raw)
    except ValueError:
        value = 8
    return max(1, value)


def upload_dir() -> Path:
    """Directory where uploaded / staged caption files wait for a worker."""
    load_env()
    path = Path(os.environ.get("UPLOAD_DIR", str(BACKEND_ROOT / "uploads")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_corpus_path() -> Path:
    """Default mounted corpus folder inside the API container."""
    load_env()
    return Path(os.environ.get("CORPUS_PATH", "/data/corpus"))
