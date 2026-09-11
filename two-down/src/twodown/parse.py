from __future__ import annotations

import html
import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from twodown.devices import classify_device
from twodown.ingest import is_fifteensquared
from twodown.models import Clue, PuzzlePost

SECTION_NAMES = {"across", "down"}
HEADER_CELLS = {"no", "detail", "clue", "entry", "answer", "wordplay", "parsing"}
SEE_ONLY = re.compile(r"^see\s+\d+", re.I)
ENUM = re.compile(r"\(([\d]+(?:[,\s-]+[\d]+)*)\)\s*$")
FIRST_ENUM = re.compile(r"\(([\d]+(?:[,\s-]+[\d]+)*)\)")
ANSWER_OK = re.compile(r"^[A-Z][A-Z \-']{1,40}$")


def _clean(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    return text.strip()


def _smart_strings(node: Tag) -> str:
    """Join highlighted single letters back into words (FT/Guardian letter spans)."""
    parts: list[str] = []
    for raw in node.strings:
        bit = raw.strip()
        if not bit:
            continue
        if (
            parts
            and bit.isalpha()
            and bit.islower()
            and len(bit) <= 2
            and parts[-1]
            and parts[-1][-1].islower()
        ):
            parts[-1] += bit
        else:
            parts.append(bit)
    return _clean(" ".join(parts))


def _cell_text(cell: Tag | None) -> str:
    if cell is None:
        return ""
    return _smart_strings(cell)


def _is_number(text: str) -> bool:
    return bool(re.match(r"^\d+[a-zA-Z]?$", text.strip()))


def _underlined(node: Tag) -> str | None:
    bits: list[str] = []
    for el in node.find_all(style=True):
        style = el.get("style") or ""
        if "underline" in style:
            bits.append(_clean(el.get_text(" ", strip=True)))
    joined = _clean(" ".join(bits))
    return joined or None


def _looks_like_answer(text: str) -> bool:
    compact = _clean(text).upper()
    if not compact or compact.lower() in SECTION_NAMES:
        return False
    return bool(ANSWER_OK.match(compact)) and any(c.isalpha() for c in compact)


def _split_enumeration(clue: str) -> tuple[str, str]:
    match = ENUM.search(clue)
    if not match:
        return clue, ""
    return _clean(clue[: match.start()]), match.group(1).replace(" ", "")


def _enumeration_ok(answer: str, enumeration: str) -> bool:
    parts = [int(p) for p in re.findall(r"\d+", enumeration)]
    words = [w for w in re.split(r"[ \-]+", answer.upper()) if w]
    if not parts or not words:
        return False
    return [len(w) for w in words] == parts


def _skip_reason(clue: str, answer: str, parse: str) -> str | None:
    if not clue or not answer:
        return "missing clue or answer"
    if SEE_ONLY.search(clue):
        return "cross-reference"
    if re.search(r"\bsee\s+\d+\s*(across|down)\b", clue, re.I):
        return "cross-reference"
    if re.search(r"\b([1-9]|[12]\d|3[0-2])s\b", clue):
        return "cross-reference"
    if re.search(r"\b\d+\s*(across|down)\b", clue, re.I):
        return "cross-reference"
    if len(parse) < 8:
        return "empty parse"
    return None


def _style_of(node: Tag | None) -> str:
    if not isinstance(node, Tag):
        return ""
    return node.get("style") or ""


def _first_blue_strong(cell: Tag) -> str | None:
    for strong in cell.find_all("strong"):
        styled = " ".join(
            [
                _style_of(strong),
                _style_of(strong.parent if isinstance(strong.parent, Tag) else None),
                *(_style_of(p) for p in strong.parents if isinstance(p, Tag) and p.name == "span"),
            ]
        )
        if "#0000ff" not in styled.lower() and "color: blue" not in styled.lower():
            continue
        text = _clean(strong.get_text(" ", strip=True)).upper()
        text = re.sub(r"\s+", " ", text)
        if _looks_like_answer(text) and len(text) < 48:
            return text
    return None


def _strip_leading_gloss(text: str) -> str:
    text = text.strip()
    if not text.startswith("("):
        return text
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i + 1 :].strip()
    return text


def _parse_detail_cell(cell: Tag) -> tuple[str, str, str, str | None, str]:
    """Independent-style No | Detail cell. Clue is often not wrapped in <p>."""
    full = _cell_text(cell)
    enum_match = FIRST_ENUM.search(full)
    if enum_match:
        clue = _clean(full[: enum_match.start()])
        enumeration = enum_match.group(1).replace(" ", "")
        rest = _clean(full[enum_match.end() :])
    else:
        clue, enumeration = _split_enumeration(full)
        rest = ""
    answer = _first_blue_strong(cell) or ""
    if not answer:
        first = _clean(re.split(r"\s+\(", rest, maxsplit=1)[0]).upper()
        if _looks_like_answer(first):
            answer = first
    parse = rest
    if answer and parse.upper().startswith(answer):
        parse = _strip_leading_gloss(parse[len(answer) :].strip(" .;—-"))
    definition = _underlined(cell)
    return clue, enumeration, answer, definition, _clean(parse)


def _direction_from(text: str, current: str) -> str:
    lower = text.lower().strip()
    if lower in SECTION_NAMES:
        return lower
    return current


def parse_post(post: PuzzlePost) -> list[Clue]:
    if not is_fifteensquared(post.url):
        return []
    soup = BeautifulSoup(post.html, "lxml")
    clues: list[Clue] = []
    for table in soup.find_all("table"):
        clues.extend(_parse_table(post, table))
    return clues


def _parse_table(post: PuzzlePost, table: Tag) -> list[Clue]:
    clues: list[Clue] = []
    direction = "across"
    rows = table.find_all("tr")
    i = 0
    while i < len(rows):
        cells = rows[i].find_all(["td", "th"], recursive=False)
        texts = [_cell_text(c) for c in cells]
        joined = " ".join(texts).strip()
        if not texts:
            i += 1
            continue
        if any(t.lower() in SECTION_NAMES for t in texts if t):
            for t in texts:
                direction = _direction_from(t, direction)
            i += 1
            continue
        if all(not t or t.lower() in HEADER_CELLS for t in texts):
            i += 1
            continue

        # Format B: number | ANSWER | clue, parse on the following row.
        if len(cells) >= 3 and _is_number(texts[0]) and _looks_like_answer(texts[1]):
            clue_text, enumeration = _split_enumeration(texts[2])
            parse = ""
            if i + 1 < len(rows):
                nxt = rows[i + 1].find_all(["td", "th"], recursive=False)
                nxt_text = [_cell_text(c) for c in nxt]
                if not (nxt_text and _is_number(nxt_text[0])):
                    parse = nxt_text[-1] if nxt_text else ""
                    i += 1
            definition = _underlined(cells[2])
            clues.append(
                _make_clue(
                    post,
                    number=texts[0],
                    direction=direction,
                    clue=clue_text,
                    enumeration=enumeration,
                    answer=texts[1].upper(),
                    definition=definition,
                    parse=parse,
                )
            )
            i += 1
            continue

        # Format A: number | clue + answer + parse in one cell.
        if len(cells) == 2 and _is_number(texts[0]):
            clue_text, enumeration, answer, definition, parse = _parse_detail_cell(cells[1])
            clues.append(
                _make_clue(
                    post,
                    number=texts[0],
                    direction=direction,
                    clue=clue_text,
                    enumeration=enumeration,
                    answer=answer,
                    definition=definition,
                    parse=parse,
                )
            )
            i += 1
            continue

        i += 1
    return clues


def _make_clue(
    post: PuzzlePost,
    number: str,
    direction: str,
    clue: str,
    enumeration: str,
    answer: str,
    definition: str | None,
    parse: str,
) -> Clue:
    answer = _clean(answer).upper()
    clue = _clean(clue)
    parse = _clean(parse)
    skipped = _skip_reason(clue, answer, parse)
    enum_ok = _enumeration_ok(answer, enumeration) if enumeration else False
    return Clue(
        source_url=post.url,
        paper=post.paper,
        puzzle_id=post.puzzle_id,
        setter=post.setter,
        blogger=post.blogger,
        number=number,
        direction=direction,
        clue=clue,
        enumeration=enumeration,
        answer=answer,
        definition=definition,
        parse=parse,
        device=classify_device(parse, clue),
        enumeration_ok=enum_ok,
        skipped_reason=skipped,
    )


def usable(clues: Iterable[Clue]) -> list[Clue]:
    return [c for c in clues if not c.skipped_reason]
