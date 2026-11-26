"""Caption reading, cleanup, windowing, and fuzzy text compare."""
from __future__ import annotations

import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

# Speech-to-text often warps a name or street by a letter or two.
NAME_MATCH = 0.90
ADDRESS_MATCH = 0.88
PROJECT_NAME_MATCH = 0.88

# Dropped from the front of a code so "Ordinance 2025-23" and "2025-23" share a key.
_CODE_LABEL = re.compile(
    r"^(?:ordinance|resolution|petition|case|file(?:\s+no\.?)?|application|project)\s+",
    re.IGNORECASE,
)
# Names that are themselves formal identifiers (used when the model left code null).
_CODEISH_NAME = re.compile(
    r"^(?:ordinance|resolution|petition|case|project)\s+[\w./-]+$",
    re.IGNORECASE,
)


def normalize(value: str | None) -> str:
    """Lowercase and collapse whitespace so name and address compares are stable."""
    return " ".join((value or "").casefold().split())


def similar(left: str | None, right: str | None) -> float:
    """Return how alike two normalized strings are, from 0 to 1."""
    a = normalize(left)
    b = normalize(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def names_match(left: str | None, right: str | None) -> bool:
    """True when two spoken names are the same person at high confidence."""
    return similar(left, right) >= NAME_MATCH


def addresses_match(left: str | None, right: str | None) -> bool:
    """True when two spoken addresses are the same place at high confidence."""
    return similar(left, right) >= ADDRESS_MATCH


def project_names_match(left: str | None, right: str | None) -> bool:
    """True when two project or policy names are the same item at high confidence."""
    return similar(left, right) >= PROJECT_NAME_MATCH


def code_key(value: str | None) -> str | None:
    """Normalize a petition, case, ordinance, or project code for matching.

    Strips a leading label so 'Ordinance 2025-23', 'ordinance 2025 23', and
    '2025-23' share one key. Keeps letters and digits only.
    """
    raw = normalize(value)
    if not raw:
        return None
    stripped = _CODE_LABEL.sub("", raw).strip() or raw
    compact = "".join(ch for ch in stripped if ch.isalnum())
    return compact or None


def codes_match(left: str | None, right: str | None) -> bool:
    """True when two formal codes point at the same project or policy."""
    a = code_key(left)
    b = code_key(right)
    if not a or not b:
        return False
    if a == b:
        return True
    # One side may still carry extra digits/letters the other dropped.
    shorter, longer = sorted([a, b], key=len)
    if len(shorter) >= 3 and longer.endswith(shorter):
        return True
    # Short ASR near-misses (LON vs Loon) after labels are stripped.
    return len(shorter) >= 3 and similar(a, b) >= 0.85


def name_looks_like_code(name: str | None) -> bool:
    """True when the spoken name is itself an ordinance, resolution, petition, or project code."""
    return bool(_CODEISH_NAME.match((name or "").strip()))


def clean_caption(text: str | None) -> str:
    """Unescape a caption and drop the speaker mark from the readable text."""
    return " ".join(html.unescape(text or "").replace(">>", " ").split())


def caption_pieces(text: str | None) -> list[str]:
    """Split one caption on the speaker mark into non-empty pieces."""
    parts = html.unescape(text or "").split(">>")
    return [" ".join(part.split()) for part in parts if " ".join(part.split())]


def load_captions(path: Path) -> list[dict]:
    """Read a caption file of objects with text, start, and end."""
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} is not a caption list")
    return data


def window_lines(captions: list[dict], index: int, before: int, after: int) -> str:
    """Build the numbered window around one caption. The center line is the one to judge."""
    lines = []
    last = len(captions) - 1
    for offset in range(-before, after + 1):
        other = index + offset
        if other < 0 or other > last:
            continue
        caption = captions[other]
        role = "judge this caption only" if offset == 0 else (
            "earlier context" if offset < 0 else "later context"
        )
        lines.append(
            f"Caption {offset:+d} ({role}, {caption['start']:.1f}-{caption['end']:.1f}s): "
            f"{clean_caption(caption.get('text'))}"
        )
    return "\n".join(lines)


def section_kind(boundary_text: str) -> str:
    """Classify a boundary caption as awards, closing, or an agenda item."""
    words = boundary_text.casefold()
    if "award" in words or "recognition" in words:
        return "awards"
    if "closed session" in words or "adjourn" in words:
        return "closing"
    return "agenda"


def chair_handoff(line: str) -> bool:
    """True when a line is the chair calling someone or giving a short thanks.

    A phrase such as 'the trees come down' is not a handoff. A line such as
    'first of all thank you for' is the speaker continuing.
    """
    words = line.casefold()
    phrases = (
        "next speaker",
        "please come down",
        "three minute",
        "public forum",
        "we will now move",
        "we now have one more speaker",
        "we also have",
    )
    if any(phrase in words for phrase in phrases):
        return True
    allowed = {"thank", "you", "so", "much", "very", "madam", "mayor", "all", "right"}
    tokens = words.replace(".", "").replace(",", "").split()
    return 0 < len(tokens) <= 5 and "thank" in tokens and all(token in allowed for token in tokens)


def text_between(captions: list[dict], start: float, end: float) -> str:
    """Join the captions whose start time falls inside a section."""
    lines = [
        clean_caption(caption.get("text"))
        for caption in captions
        if start <= caption["start"] < end and clean_caption(caption.get("text"))
    ]
    return " ".join(lines)
