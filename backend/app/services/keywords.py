"""Hybrid cues: cheap regex first, then JEV only on borderline windows.

Hard patterns open a signal immediately. Soft patterns mean "maybe" — those
windows go to JEV for the missing signals. Soft lists are provisional.
"""
from __future__ import annotations

import re

# Hard hit → signal is on. No model call needed.
DATA_CENTER_PATTERN = re.compile(
    r"""
    \b(
        data[\s\-]?cent(?:er|re)s?
        | datacent(?:er|re)s?
        | hyperscale(?:\s+(?:facility|campus|project))?
        | server\s+farms?
        | colocation\s+(?:facility|center|centre|campus)
        | colo\s+(?:facility|center|centre|campus)
        | digital\s+infrastructure\s+(?:facility|campus)
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

CUE_PATTERNS = {
    "water": re.compile(
        r"\b(water\s+(?:use|usage|supply|demand|consumption)|cooling\s+water|wastewater|well\s+water)\b",
        re.I,
    ),
    "power": re.compile(
        r"\b(megawatts?|substation|grid\s+capacity|electric(?:ity)?\s+(?:demand|load|capacity)|power\s+(?:demand|load|capacity))\b",
        re.I,
    ),
    "noise": re.compile(r"\b(noise|humming|sound\s+pollution)\b", re.I),
    "radiation": re.compile(r"\b(radiation|electromagnetic|emf)\b", re.I),
    "jobs": re.compile(r"\b(jobs?|employment|workforce)\b", re.I),
    "tax": re.compile(r"\b(tax\s+(?:abatement|incentive|break|revenue)|pilot\b|tif\b)\b", re.I),
    "siting": re.compile(
        r"\b(zoning|special\s+use|conditional\s+use|moratorium|site\s+plan|rezon(?:e|ing))\b",
        re.I,
    ),
}

# Soft hit → ask JEV for that signal when the hard pattern did not fire.
SOFT_PATTERNS = {
    "data_center": re.compile(
        r"""
        \b(
            data\s+senters?
            | dater\s+centers?
            | computing\s+campus
            | server\s+buildings?
            | building\s+full\s+of\s+servers
            | cloud\s+(?:company|campus|facility|project)
            | colocation
            | \bcolo\b
            | digital\s+infrastructure
            | hyperscale
        )\b
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
    "water": re.compile(r"\b(water|wells?|gallons?|cooling|aquifer|waste\s*water)\b", re.I),
    "power": re.compile(r"\b(electric|electricity|megawatt|grid|substation|kilowatt|power\s+line)\b", re.I),
    "noise": re.compile(r"\b(noise|hum|buzz|loud|sound)\b", re.I),
    "radiation": re.compile(r"\b(radiation|electromagnetic|emf|radio\s+frequency)\b", re.I),
    "jobs": re.compile(r"\b(jobs?|employment|workforce|hiring|careers?)\b", re.I),
    "tax": re.compile(r"\b(tax|abatement|incentive|pilot|tif|revenue)\b", re.I),
    "siting": re.compile(r"\b(zoning|rezon|permit|moratorium|site\s+plan|special\s+use|land\s+use)\b", re.I),
}


def data_center_matches(text: str) -> list[str]:
    """Return the distinct hard data-center spellings found in text."""
    return sorted({match.group(0).casefold() for match in DATA_CENTER_PATTERN.finditer(text or "")})


def hard_signals(text: str) -> list[str]:
    """Signals the hard regex is sure about."""
    found = [name for name, pattern in CUE_PATTERNS.items() if pattern.search(text or "")]
    if data_center_matches(text):
        found.append("data_center")
    return sorted(set(found))


def soft_signals(text: str) -> list[str]:
    """Signals that look possible and should get a JEV second look when hard missed them."""
    return sorted(name for name, pattern in SOFT_PATTERNS.items() if pattern.search(text or ""))


def scan_caption_windows(captions: list[dict], window_size: int = 36) -> list[dict]:
    """Walk every window with regex. Windows that need JEV list the missing signal names.

    Each row:
      start, end, text, signals (hard only for now), keywords, ask_jev (signal names).
    """
    rows = []
    for start in range(0, len(captions), window_size):
        end = min(len(captions), start + window_size)
        text = " ".join((caption.get("text") or "") for caption in captions[start:end])
        hard = hard_signals(text)
        soft = soft_signals(text)
        ask_jev = sorted(set(soft) - set(hard))
        rows.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "signals": hard,
                "keywords": data_center_matches(text),
                "ask_jev": ask_jev,
                "sources": {name: "regex" for name in hard},
            }
        )
    return rows
