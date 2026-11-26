"""Calls to the JEV decision model. One state, one or more choice questions."""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
import urllib.error
import urllib.request

from app.config import env

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


class JevClient:
    """Asks JEV a fixed choice about a short block of caption text."""

    def __init__(self) -> None:
        """Load the API key. The key is never written into a result or a log."""
        self.key = env("JEV_API_KEY")
        self.calls = 0
        self.cache_hits = 0
        self._cache: dict[tuple, dict] = {}
        self._lock = threading.Lock()

    def ask(self, state: str, questions: dict) -> dict:
        """Post one state and its questions. An identical state is not sent twice."""
        key = (id(questions), state)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self.cache_hits += 1
                return cached
        answers = self._post(state, questions)
        with self._lock:
            self.calls += 1
            self._cache[key] = answers
        return answers

    def _post(self, state: str, questions: dict) -> dict:
        """Post one request and retry on timeouts, DNS blips, and busy responses."""
        body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
        last_error = None
        for attempt in range(6):
            request = urllib.request.Request(
                ENDPOINT,
                data=body,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.loads(response.read().decode())
                return payload["answers"]
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", "replace")[:400]
                last_error = f"HTTP {error.code}: {detail}"
                if error.code not in (408, 429, 500, 502, 503, 504):
                    raise RuntimeError(last_error) from error
            except (
                urllib.error.URLError,
                TimeoutError,
                socket.timeout,
                ConnectionError,
                http.client.HTTPException,
            ) as error:
                # DNS blips, read timeouts, and the server dropping the socket
                # are common on long ingest runs.
                last_error = str(error)
            time.sleep(min(20.0, 1.5 * (attempt + 1)))
        raise RuntimeError(last_error or "JEV request failed")

    @staticmethod
    def choice(answers: dict, name: str) -> tuple[str, float]:
        """Return the chosen label and its probability for one question."""
        answer = answers[name]
        picked = answer["choice"]
        probability = (answer.get("probabilities") or {}).get(picked, 0)
        return picked, float(probability)
