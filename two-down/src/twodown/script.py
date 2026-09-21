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
    NO_PICTURE_LINE,
    INTRO_GAP_SECONDS,
    INTRO_LINE,
    LETTERS_PAUSE_SECONDS,
    OUTRO_GAP_SECONDS,
    OUTRO_LINE,
    PARSE_ASIDE_PAUSE_SECONDS,
    SOURCE_GAP_SECONDS,
    THINK_PAUSE_SECONDS,
    THINK_PROMPT,
)
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
    text = text[:1].upper() + text[1:]
    if len(numbers) == 1 and "-" not in raw and "," not in raw:
        return f"That's {text.lower()} letters."
    return f"That's {text.lower()}."


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
        return "Here it is."
    return f"It's {spoken}."


def speak_parse_tokens(text: str) -> str:
    """Lowercase ALL-CAPS constructions in speech so TTS says words, not letters."""

    def _word(match: re.Match[str]) -> str:
        return speak_construction(match.group(0))

    return _ALL_CAPS_TOKEN.sub(_word, text)


_ASIDE = re.compile(r"\s*\(([^)]+)\)(?:,)?")


def speak_parse_asides(text: str) -> str:
    """Give parenthetical asides their own sentence so they do not glue to the construction."""

    def _aside(match: re.Match[str]) -> str:
        inner = re.sub(r"\s+", " ", match.group(1)).strip(" .")
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
    text = parse
    # 15² / Aled notation: LIKE="positive response" and anagram/"Doctor".
    notation = bool(re.search(r'="|\banagram\s*/', text))
    text = re.sub(r'="([^"]+)"', r" (\1)", text)
    text = re.sub(r'(?i)\banagram\s*/\s*"([^"]+)"', r"\1 (anagram indicator)", text)
    if "anagram indicator" in text.lower():
        text = re.sub(r"\(([^)]+)\)\*", r"\1", text)
        text = re.sub(r",?\s*e\.g\.[^.]*", "", text)
    text = text.replace("*", " anagram ")
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
    def has_picture(self) -> bool:
        return self.hint_speech.strip().casefold() != NO_PICTURE_LINE.strip().casefold()

    @property
    def full(self) -> str:
        hold = f"[pause {HINT_HOLD_SECONDS:.0f}s]\n" if self.has_picture else ""
        return (
            f"{self.intro_speech}\n"
            f"{self.clue_speech}\n"
            f"{self.letters_speech}\n"
            f"[pause {LETTERS_PAUSE_SECONDS:.0f}s]\n"
            f"{self.think_speech}\n"
            f"[pause {THINK_PAUSE_SECONDS:.0f}s]\n"
            f"{self.hint_speech}\n"
            f"{hold}"
            f"[pause {HINT_PAUSE_SECONDS:.1f}s]\n"
            f"{self.answer_speech}\n"
            f"[pause {ANSWER_PAUSE_SECONDS:.0f}s]\n"
            f"{self.parse_speech}\n"
            f"[pause {SOURCE_GAP_SECONDS:.2f}s]\n"
            f"{self.source_speech}\n"
            f"[pause {OUTRO_GAP_SECONDS:.1f}s]\n"
            f"{self.outro_speech}"
        )


def speak_source(clue: Clue) -> str:
    """Credit the setter, paper, and Fifteen Squared — spoken in a different voice."""
    setter = (clue.setter or "").strip()
    paper = (clue.paper or "").strip()
    if setter and paper:
        return f"That's {setter}, in the {paper} — via Fifteen Squared."
    if setter:
        return f"That's {setter} — via Fifteen Squared."
    return "That's via Fifteen Squared."


def write_parts(clue: Clue) -> ScriptParts:
    parse = speak_parse_tokens(_spoken_parse(clue.parse, clue.answer))
    meaning = ""
    if clue.definition:
        gloss = clue.definition.strip(" .")
        meaning = f" {gloss[0].upper()}{gloss[1:]}."
    return ScriptParts(
        intro_speech=INTRO_LINE,
        clue_speech=f"{clue.clue}.",
        letters_speech=speak_enumeration(clue.enumeration),
        think_speech=THINK_PROMPT,
        hint_speech=clue.hint_line or HINT_LINE,
        answer_speech=speak_answer(clue.answer),
        parse_speech=speak_parse_asides(speak_parse_tokens(f"{parse}{meaning}".strip())),
        source_speech=speak_source(clue),
        outro_speech=OUTRO_LINE,
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
    hint_hold = (
        f'<break time="{int(HINT_HOLD_SECONDS * 1000)}ms"/>' if parts.has_picture else ""
    )
    hint_ms = int(HINT_PAUSE_SECONDS * 1000)
    answer_ms = int(ANSWER_PAUSE_SECONDS * 1000)
    source_ms = int(SOURCE_GAP_SECONDS * 1000)
    outro_ms = int(OUTRO_GAP_SECONDS * 1000)
    return (
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
        f"{hint_hold}"
        f'<break time="{hint_ms}ms"/>'
        f"{html.escape(parts.answer_speech, quote=False)}"
        f'<break time="{answer_ms}ms"/>'
        f"{html.escape(parts.parse_speech, quote=False)}"
        f'<break time="{source_ms}ms"/>'
        f"{html.escape(parts.source_speech, quote=False)}"
        f'<break time="{outro_ms}ms"/>'
        f"{html.escape(parts.outro_speech, quote=False)}"
        "</speak>"
    )
