from __future__ import annotations

import html
import re
from dataclasses import dataclass

from twodown.config import THINK_PAUSE_SECONDS
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
    text = text.replace("*", " anagram ")
    text = re.sub(r"\[([^]]+)\]", r" \1 ", text)
    text = text.replace("+", " plus ")
    text = re.sub(r"\s+", " ", text)
    if answer:
        text = _drop_construction(text, answer)
    text = re.sub(r"\s+", " ", text).strip(" .;,-")
    if len(text) > 220:
        text = text[:217].rsplit(" ", 1)[0]
    if text and text[-1] not in ".!?":
        text += "."
    return text


@dataclass(frozen=True)
class ScriptParts:
    clue_speech: str
    breakdown: str

    @property
    def full(self) -> str:
        return f"{self.clue_speech}\n\n[pause {THINK_PAUSE_SECONDS:.0f}s]\n\n{self.breakdown}"


def write_parts(clue: Clue) -> ScriptParts:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    parse = _spoken_parse(clue.parse, clue.answer)
    definition = f" It means {clue.definition}." if clue.definition else ""
    clue_speech = f"The clue: {clue.clue}{enum}."
    breakdown = (
        f"The answer is {clue.answer}.{definition} {parse} "
        f"{clue.setter} in the {clue.paper}, via Fifteen Squared. cryptic.fun."
    )
    return ScriptParts(clue_speech=clue_speech, breakdown=breakdown)


def write_script(clue: Clue) -> str:
    return write_parts(clue).full


def to_ssml(parts: ScriptParts, pause_seconds: float = THINK_PAUSE_SECONDS) -> str:
    pause_ms = int(pause_seconds * 1000)
    clue_xml = html.escape(parts.clue_speech, quote=False)
    down_xml = html.escape(parts.breakdown, quote=False)
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-GB">'
        f"{clue_xml}<break time=\"{pause_ms}ms\"/>{down_xml}"
        "</speak>"
    )
