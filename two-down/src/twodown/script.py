from __future__ import annotations

import html
import re
from dataclasses import dataclass

from twodown.config import (
    ANSWER_PAUSE_SECONDS,
    CLUE_LETTERS_GAP_SECONDS,
    HINT_HOLD_SECONDS,
    HINT_LINE,
    HINT_PAUSE_SECONDS,
    INTRO_GAP_SECONDS,
    INTRO_LINE,
    LETTERS_PAUSE_SECONDS,
    OUTRO_GAP_SECONDS,
    OUTRO_LINE,
    PARSE_ASIDE_PAUSE_SECONDS,
    SOURCE_GAP_SECONDS,
    THINK_PAUSE_SECONDS,
    THINK_PROMPT,
    pick_wisdom,
)
from twodown.hints import attach_hint
from twodown.models import Clue

DEVICE_LINE = {
    "anagram": "The wordplay is an anagram.",
    "hidden": "The answer is hidden in the clue.",
    "reversal": "The wordplay is a reversal.",
    "container": "One lot of letters goes inside another.",
    "charade": "The answer is built in pieces.",
    "homophone": "The wordplay is a homophone — it sounds like something else.",
    "deletion": "Some letters are taken away.",
    "double_def": "Two definitions, one answer.",
    "unknown": "Here is the wordplay.",
}

_ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty")


def _number_word(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 60:
        tens, ones = divmod(n, 10)
        return _TENS[tens] if ones == 0 else f"{_TENS[tens]}-{_ONES[ones]}"
    return str(n)


def speak_enumeration(enumeration: str) -> str:
    """Speak the letter count after the clue, never as part of it."""
    raw = (enumeration or "").strip()
    if not raw:
        return "Count the letters."
    tokens = re.findall(r"\d+|[-,]", raw.replace(" ", ""))
    numbers = [t for t in tokens if t.isdigit()]
    spoken: list[str] = []
    for token in tokens:
        if token.isdigit():
            spoken.append(_number_word(int(token)))
        elif token == "-":
            spoken.append("hyphen")
        elif token == ",":
            spoken.append(",")
    text = " ".join(spoken).replace(" ,", ",")
    count = text[:1].upper() + text[1:].lower()
    if len(numbers) == 1 and "-" not in raw and "," not in raw:
        return f"{count} letters."
    return f"{count}."


# ALL-CAPS crossword lights/fodder (PIN-UP, PUP, END RESULT). Leave numbers
# and ordinary sentence case alone so Edge-TTS does not spell them.
_ALL_CAPS_TOKEN = re.compile(r"(?<![A-Za-z])[A-Z]{2,}(?:-[A-Z]+)*(?![A-Za-z])")


def speak_construction(text: str) -> str:
    """Speak a crossword light as a word, not letter-by-letter."""
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def speak_answer(answer: str) -> str:
    """Speak the crossword light as a word, not letter-by-letter."""
    spoken = speak_construction(answer)
    if not spoken:
        return "Work it out."
    return f"It's {spoken}."


def speak_parse_tokens(text: str) -> str:
    """Lowercase ALL-CAPS constructions in speech so TTS says words, not letters."""

    def _word(match: re.Match[str]) -> str:
        return speak_construction(match.group(0))

    return _ALL_CAPS_TOKEN.sub(_word, text)


# A blog address or a site name is not part of the clue or the solution.
_SITE_ADDRESS = re.compile(
    r"https?://\S+|www\.\S+|\bcryptic\.fun\b|fifteensquared(?:\.net)?|fifteen\s+squared|\b15²\b",
    re.I,
)


def _strip_site_code(text: str) -> str:
    """Keep speech on the clue and the solution. Drop addresses and blog tokens."""
    text = re.sub(r"\banagram\s+AInd\b", "anagram indicator", text, flags=re.I)
    text = re.sub(r"\bAInd\b", "anagram indicator", text)
    text = re.sub(r"&Lit\.?", "and the whole clue is the definition", text, flags=re.I)
    text = _SITE_ADDRESS.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s+([.;,:])", r"\1", text)
    return text.strip(" ,;")


_ASIDE = re.compile(r"\s*\(([^)]+)\)(?:,)?")


def speak_parse_asides(text: str) -> str:
    """Give parenthetical asides their own sentence so they do not glue to the construction."""

    def _aside(match: re.Match[str]) -> str:
        inner = re.sub(r"\s+", " ", match.group(1)).strip(" .\"'\u201c\u201d\u2018\u2019")
        if not inner:
            return ""
        return f". {inner}."

    opened = _ASIDE.sub(_aside, text)
    opened = re.sub(r"\.\s*\.", ".", opened)
    opened = re.sub(r"\.\s*,", ".", opened)
    opened = re.sub(r"\s+", " ", opened).strip()
    opened = re.sub(r"\s+([.;,:])", r"\1", opened)

    def _cap(match: re.Match[str]) -> str:
        return match.group(1) + match.group(2).upper()

    opened = re.sub(r"(^|[.!?]\s+)([a-z])", _cap, opened)
    if opened and opened[-1] not in ".!?":
        opened += "."
    return opened


def _drop_construction(text: str, answer: str) -> str:
    tokens = text.split()
    compact = re.sub(r"[^A-Z]", "", answer.upper())
    for n in range(2, min(8, len(tokens)) + 1):
        tail = "".join(re.sub(r"[^A-Z]", "", t.upper()) for t in tokens[-n:])
        if tail == compact:
            return " ".join(tokens[:-n]).rstrip(" .;,-")
    return text


def _spoken_parse(parse: str, answer: str = "") -> str:
    text = parse.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    # 15² / Aled notation: LIKE="positive response" and anagram/"Doctor".
    notation = bool(re.search(r'="|\banagram\s*/', text))
    text = re.sub(r'="([^"]+)"', r" (\1)", text)
    text = re.sub(r'(?i)\banagram\s*/\s*"([^"]+)"', r"\1 (anagram indicator)", text)
    if "anagram indicator" in text.lower():
        text = re.sub(r"\(([^)]+)\)\*", r"\1", text)
        text = re.sub(r",?\s*e\.g\.[^.]*", "", text)
    text = text.replace("*", " anagram ")
    # U[kraine] is the word with the unused tail marked, not two tokens.
    def _glue_tail(match: re.Match[str]) -> str:
        head, tail = match.group(1), match.group(2)
        if len(tail) == 1:
            return head + (tail.upper() if head.isupper() else tail.lower())
        return head + tail.lower()

    text = re.sub(r"([A-Za-z])\[([a-z]+|[A-Z])\]", _glue_tail, text)
    text = re.sub(r"\[([^]]+)\]", r" \1 ", text)
    text = text.replace("+", " plus ")
    text = re.sub(r"\s+", " ", text)
    if answer:
        text = _drop_construction(text, answer)
    text = re.sub(r"\s+", " ", text).strip(" .;,-")
    if notation and "anagram indicator" in text.lower():
        first = re.split(r"(?<=\.)\s+", text, maxsplit=1)[0].strip(" .;,-")
        if first:
            text = first
    text = _strip_site_code(text)
    text = re.sub(r"\s+([.;,:])", r"\1", text)
    if len(text) > 220:
        text = text[:217].rsplit(" ", 1)[0]
    if text and text[-1] not in ".!?":
        text += "."
    return text


@dataclass(frozen=True)
class ScriptParts:
    intro_speech: str
    clue_speech: str
    letters_speech: str
    think_speech: str
    hint_speech: str
    answer_speech: str
    parse_speech: str
    source_speech: str
    outro_speech: str

    @property
    def breakdown(self) -> str:
        return f"{self.answer_speech} {self.parse_speech}"

    @property
    def full(self) -> str:
        lines = [
            self.intro_speech,
            self.clue_speech,
            self.letters_speech,
            f"[pause {LETTERS_PAUSE_SECONDS:.0f}s]",
            self.think_speech,
            f"[pause {THINK_PAUSE_SECONDS:.0f}s]",
            self.hint_speech,
            f"[pause {HINT_HOLD_SECONDS:.0f}s]",
            f"[pause {HINT_PAUSE_SECONDS:.1f}s]",
            self.answer_speech,
            f"[pause {ANSWER_PAUSE_SECONDS:.0f}s]",
            self.parse_speech,
        ]
        if self.source_speech:
            lines.append(f"[pause {SOURCE_GAP_SECONDS:.2f}s]")
            lines.append(self.source_speech)
        lines.append(f"[pause {OUTRO_GAP_SECONDS:.1f}s]")
        lines.append(self.outro_speech)
        return "\n".join(lines)


def speak_paper(paper: str) -> str:
    """Say the paper the way a person would: the Guardian, the Financial Times."""
    name = (paper or "").strip()
    if not name:
        return ""
    if name.lower().startswith("the "):
        return name
    return f"the {name}"


def speak_intro(clue: Clue) -> str:
    """Andrew's invite: we are AI, then the paper and setter once."""
    paper = speak_paper(clue.paper)
    setter = (clue.setter or "").strip()
    if paper and setter:
        source = f"Today's clue is from {paper}, by {setter}."
    elif paper:
        source = f"Today's clue is from {paper}."
    elif setter:
        source = f"Today's clue is by {setter}."
    else:
        source = "Today's clue is from the papers."
    return f"{INTRO_LINE} {source}"


def speak_source(clue: Clue) -> str:
    """Paper and setter are in the invite. Do not credit them again at the end."""
    del clue
    return ""


def speak_outro(clue: Clue) -> str:
    """Ava's closer: one piece of wisdom, then the site name once."""
    wisdom = pick_wisdom(clue.slug)
    if wisdom:
        return f"{wisdom} {OUTRO_LINE}"
    return OUTRO_LINE


def write_parts(clue: Clue) -> ScriptParts:
    clue = attach_hint(clue)
    parse = speak_parse_tokens(_spoken_parse(clue.parse, clue.answer))
    meaning = ""
    if clue.definition:
        gloss = clue.definition.strip(" .")
        meaning = f" {gloss[0].upper()}{gloss[1:]}."
    return ScriptParts(
        intro_speech=_strip_site_code(speak_intro(clue)),
        clue_speech=_strip_site_code(f"{clue.clue}."),
        letters_speech=_strip_site_code(speak_enumeration(clue.enumeration)),
        think_speech=_strip_site_code(THINK_PROMPT),
        hint_speech=_strip_site_code(clue.hint_line or HINT_LINE),
        answer_speech=_strip_site_code(speak_answer(clue.answer)),
        parse_speech=_strip_site_code(
            speak_parse_asides(speak_parse_tokens(f"{parse}{meaning}".strip()))
        ),
        source_speech=_strip_site_code(speak_source(clue)),
        outro_speech=_strip_site_code(speak_outro(clue)),
    )


def write_script(clue: Clue) -> str:
    return write_parts(clue).full


def parse_to_ssml(text: str) -> str:
    """Speak the parse with air around each aside / sentence."""
    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not pieces:
        pieces = [text]
    pause_ms = int(PARSE_ASIDE_PAUSE_SECONDS * 1000)
    body = f'<break time="{pause_ms}ms"/>'.join(
        html.escape(part, quote=False) for part in pieces
    )
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-GB">'
        f"{body}"
        "</speak>"
    )


def to_ssml(parts: ScriptParts, pause_seconds: float | None = None) -> str:
    think_ms = int((pause_seconds if pause_seconds is not None else THINK_PAUSE_SECONDS) * 1000)
    intro_ms = int(INTRO_GAP_SECONDS * 1000)
    gap_ms = int(CLUE_LETTERS_GAP_SECONDS * 1000)
    letters_ms = int(LETTERS_PAUSE_SECONDS * 1000)
    hint_hold_ms = int(HINT_HOLD_SECONDS * 1000)
    hint_ms = int(HINT_PAUSE_SECONDS * 1000)
    answer_ms = int(ANSWER_PAUSE_SECONDS * 1000)
    source_ms = int(SOURCE_GAP_SECONDS * 1000)
    outro_ms = int(OUTRO_GAP_SECONDS * 1000)
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-GB">'
        f"{html.escape(parts.intro_speech, quote=False)}"
        f'<break time="{intro_ms}ms"/>'
        f"{html.escape(parts.clue_speech, quote=False)}"
        f'<break time="{gap_ms}ms"/>'
        f"{html.escape(parts.letters_speech, quote=False)}"
        f'<break time="{letters_ms}ms"/>'
        f"{html.escape(parts.think_speech, quote=False)}"
        f'<break time="{think_ms}ms"/>'
        f"{html.escape(parts.hint_speech, quote=False)}"
        f'<break time="{hint_hold_ms}ms"/>'
        f'<break time="{hint_ms}ms"/>'
        f"{html.escape(parts.answer_speech, quote=False)}"
        f'<break time="{answer_ms}ms"/>'
        f"{html.escape(parts.parse_speech, quote=False)}"
    )
    if parts.source_speech:
        ssml += (
            f'<break time="{source_ms}ms"/>'
            f"{html.escape(parts.source_speech, quote=False)}"
        )
    ssml += (
        f'<break time="{outro_ms}ms"/>'
        f"{html.escape(parts.outro_speech, quote=False)}"
        "</speak>"
    )
    return ssml
