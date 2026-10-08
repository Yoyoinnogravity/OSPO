"""One clue, then the existing speak / render / publish / upload path.

The London date picks a slot. The slot picks a source. If that source has
no answered clue, the next slot is tried, so the day still ships.

Guardian clues come from https://fifteensquared.net/. Times, the Telegraph,
and homemade clues come only from own-clues.json, and only when the answer
and the parse are already written. Those papers are not fetched.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from twodown.config import OWN_CLUES, SITE_ORIGIN
from twodown.ingest import canonical_source_url
from twodown.models import Clue
from twodown.parse import _enumeration_ok, _skip_reason, usable
from twodown.select import select_pair

# Stable cycle. date.toordinal() % 5 walks this list. No weekday table to maintain.
ROTATION = (
    "guardian",
    "times",
    "telegraph",
    "own",
    "clue-of-the-day",
)
CLUE_OF_THE_DAY = "Clue of the day"
_DEVICES: set[str] = {
    "anagram",
    "hidden",
    "reversal",
    "container",
    "charade",
    "homophone",
    "deletion",
    "double_def",
    "unknown",
}


@dataclass(frozen=True)
class DailyPick:
    clue: Clue
    slot: str
    source: str


def rotation_slot(day: date) -> str:
    return ROTATION[day.toordinal() % len(ROTATION)]


def _paper_key(paper: str) -> str:
    key = " ".join((paper or "").lower().split())
    for prefix in ("the ", "daily "):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    if key in {"ft", "financial times"}:
        return "financial times"
    return key


def _own_id(raw: dict, clue_text: str) -> str:
    given = str(raw.get("id") or "").strip()
    if given:
        return given
    return hashlib.sha256(clue_text.encode("utf-8")).hexdigest()[:12]


def _own_clue(raw: dict) -> Clue | None:
    if not isinstance(raw, dict):
        return None
    clue_text = str(raw.get("clue") or "").strip()
    answer = str(raw.get("answer") or "").strip()
    parse = str(raw.get("parse") or "").strip()
    if _skip_reason(clue_text, answer, parse):
        return None
    enumeration = str(raw.get("enumeration") or "").strip()
    paper = str(raw.get("paper") or "Own").strip() or "Own"
    setter = str(raw.get("setter") or "Aled").strip() or "Aled"
    source = canonical_source_url(str(raw.get("source_url") or ""))
    if source:
        blogger = str(raw.get("blogger") or "the blogger").strip() or "the blogger"
    else:
        source = f"{SITE_ORIGIN}/suggest.html"
        blogger = setter
    device = str(raw.get("device") or "unknown").strip()
    if device not in _DEVICES:
        device = "unknown"
    direction = str(raw.get("direction") or "across").strip().lower()
    if direction not in {"across", "down"}:
        direction = "across"
    number = str(raw.get("number") or "1").strip() or "1"
    puzzle_id = str(raw.get("puzzle_id") or "").strip() or _own_id(raw, clue_text)
    definition = str(raw.get("definition") or "").strip() or None
    return Clue(
        source_url=source,
        paper=paper,
        puzzle_id=puzzle_id,
        setter=setter,
        blogger=blogger,
        number=number,
        direction=direction,
        clue=clue_text,
        enumeration=enumeration,
        answer=answer,
        definition=definition,
        parse=parse,
        device=device,  # type: ignore[arg-type]
        enumeration_ok=_enumeration_ok(answer, enumeration) if enumeration else False,
        own_id=_own_id(raw, clue_text),
    )


def load_own_clues(path: Path | None = None, day: date | None = None) -> list[Clue]:
    """Answered clues from the file. A row with no answer is ignored.

    A row already filmed on another day is ignored. The same day can run again.
    """
    file = Path(path or OWN_CLUES)
    if not file.exists():
        return []
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    stamp = day.isoformat() if day else None
    clues: list[Clue] = []
    for raw in data.get("clues") or []:
        if not isinstance(raw, dict):
            continue
        used = str(raw.get("used_on") or "").strip()
        if used and stamp and used != stamp:
            continue
        if used and stamp is None:
            continue
        clue = _own_clue(raw)
        if clue:
            clues.append(clue)
    return clues


def mark_own_clue_used(clue: Clue, day: str, path: Path | None = None) -> bool:
    """Remember that this written clue was filmed, so tomorrow takes the next one."""
    if not clue.own_id:
        return False
    file = Path(path or OWN_CLUES)
    if not file.exists():
        return False
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    changed = False
    for raw in data.get("clues") or []:
        if not isinstance(raw, dict):
            continue
        if _own_id(raw, str(raw.get("clue") or "").strip()) != clue.own_id:
            continue
        if str(raw.get("used_on") or "") == day:
            return False
        raw["used_on"] = day
        changed = True
        break
    if changed:
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def _best(clues: list[Clue]) -> Clue | None:
    chosen = select_pair(usable(clues), n=1)
    return chosen[0] if chosen else None


def _pool(name: str, blog: list[Clue], own: list[Clue]) -> list[Clue]:
    if name == "guardian":
        return [c for c in blog if _paper_key(c.paper) == "guardian"]
    if name == "times":
        return [c for c in own if _paper_key(c.paper) == "times"]
    if name == "telegraph":
        return [c for c in own if _paper_key(c.paper) == "telegraph"]
    if name == "own":
        homemade = [c for c in own if _paper_key(c.paper) not in {"times", "telegraph"}]
        return homemade or list(own)
    if name == "clue-of-the-day":
        return list(blog)
    return []


def pick_clue_of_the_day(
    blog_clues: list[Clue],
    day: date,
    own_path: Path | None = None,
) -> DailyPick | None:
    """The one clue for this London date. None only when nothing answered is available."""
    slot = rotation_slot(day)
    own = load_own_clues(own_path, day)
    start = ROTATION.index(slot)
    order = ROTATION[start:] + ROTATION[:start]
    for name in order:
        clue = _best(_pool(name, blog_clues, own))
        if clue is None:
            continue
        if name == "clue-of-the-day":
            clue = clue.model_copy(update={"theme": CLUE_OF_THE_DAY})
        return DailyPick(clue=clue, slot=slot, source=name)
    return None
