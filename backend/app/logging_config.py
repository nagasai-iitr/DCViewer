"""Progress lines for the API and the ingest worker."""
from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Send progress lines to stderr so they show in the container logs."""
    logger = logging.getLogger("app")
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
