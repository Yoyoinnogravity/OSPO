from __future__ import annotations

import re

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


def write_script(clue: Clue) -> str:
    paper = clue.paper
    setter = clue.setter
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    device = DEVICE_LINE.get(clue.device, DEVICE_LINE["unknown"])
    parse = _spoken_parse(clue.parse, clue.answer)
    definition = f" It means {clue.definition}." if clue.definition else ""
    return (
        f"Two Down. {setter} in the {paper}. "
        f"The clue: {clue.clue}{enum}. "
        f"{device} {parse} "
        f"The answer is {clue.answer}.{definition} "
        f"Parse via Fifteen Squared, {clue.blogger}."
    )
