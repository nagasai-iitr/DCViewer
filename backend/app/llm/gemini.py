"""Calls to Gemini for structured text. The model does not choose boundaries."""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
import urllib.error
import urllib.request

from app.config import env

MODELS = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
)


class GeminiClient:
    """Asks Gemini for JSON that matches a schema."""

    def __init__(self) -> None:
        """Load the API key. The key is never written into a result or a log."""
        self.key = env("GOOGLE_API_KEY")
        self.calls = 0
        self._lock = threading.Lock()

    def generate(self, prompt: str, schema: dict) -> dict:
        """Return the parsed JSON object from the first model that answers."""
        parsed = self._post(prompt, schema)
        with self._lock:
            self.calls += 1
        return parsed

    def _post(self, prompt: str, schema: dict) -> dict:
        """Post one prompt and retry when the service is busy."""
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                },
            }
        ).encode()
        last_error = None
        for model in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for attempt in range(3):
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers={"x-goog-api-key": self.key, "Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=120) as response:
                        payload = json.loads(response.read().decode())
                    text = payload["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
                except urllib.error.HTTPError as error:
                    detail = error.read().decode("utf-8", "replace")[:400]
                    last_error = f"{model} HTTP {error.code}: {detail}"
                    if error.code == 404:
                        break
                    if error.code not in (408, 429, 500, 502, 503, 504):
                        raise RuntimeError(last_error) from error
                except (
                    urllib.error.URLError,
                    TimeoutError,
                    socket.timeout,
                    ConnectionError,
                    http.client.HTTPException,
                ) as error:
                    last_error = f"{model} {error}"
                time.sleep(min(20.0, 1.5 * (attempt + 1)))
        raise RuntimeError(last_error or "Gemini request failed")
