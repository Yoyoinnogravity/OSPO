from __future__ import annotations

from collections import defaultdict

from twodown.devices import PREFERRED
from twodown.models import Clue
from twodown.parse import usable

LETTER_SWEET_SPOT = range(4, 13)


def _score(clue: Clue) -> float:
    score = 0.0
    if clue.device in PREFERRED:
        score += 4
    if clue.device == "unknown":
        score -= 2
    letters = len(re_letters(clue.answer))
    if letters in LETTER_SWEET_SPOT:
        score += 2
    elif letters > 16:
        score -= 1
    if clue.enumeration_ok:
        score += 2
    else:
        score -= 1
    if 24 <= len(clue.parse) <= 280:
        score += 1
    if len(clue.parse) > 400:
        score -= 1
    return score


def re_letters(answer: str) -> str:
    return "".join(c for c in answer.upper() if c.isalpha())


def select_pair(clues: list[Clue], n: int = 2) -> list[Clue]:
    candidates = sorted(usable(clues), key=_score, reverse=True)
    if not candidates:
        return []
    first = candidates[0]
    chosen: list[Clue] = [first]
    rest = [c for c in candidates if c.answer != first.answer]
    rest.sort(
        key=lambda c: (
            0 if c.paper != first.paper else 1,
            0 if c.device != first.device else 1,
            -_score(c),
        )
    )
    for clue in rest:
        chosen.append(clue)
        if len(chosen) >= n:
            break
    return chosen[:n]


def group_by_paper(clues: list[Clue]) -> dict[str, list[Clue]]:
    grouped: dict[str, list[Clue]] = defaultdict(list)
    for clue in usable(clues):
        grouped[clue.paper].append(clue)
    return grouped
