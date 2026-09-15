from __future__ import annotations

import re

from twodown.models import Device

ANAGRAM = re.compile(
    r"\banagrams?\b|\banagrind\b|\banag\.?\b|\(.*\)\*|jumbled|scrambled|\bvarious\b",
    re.I,
)
HIDDEN = re.compile(r"\bhidden\b|hidden answer|lurking in|some \.\.\.|concealed", re.I)
REVERSAL = re.compile(r"\brevers(?:e|ed|al)\b|\bback\b|returning|upon reflection|on return", re.I)
CONTAINER = re.compile(
    r"\bcontain(?:s|ed|ing)?\b|\binside\b|\baround\b|\bcups\b|\bgobbled\b|\binvading\b|inserted",
    re.I,
)
HOMOPHONE = re.compile(r"\bhomophone\b|we hear|sounds like|picked up|some say", re.I)
DELETION = re.compile(r"\bminus\b|without the|excluding|removing|abandoned|goes missing", re.I)
DOUBLE = re.compile(r"double def|two definitions|dd\b", re.I)
CHARADE = re.compile(r"\bcharade\b|\bplus\b|\+", re.I)

PREFERRED: tuple[Device, ...] = (
    "anagram",
    "hidden",
    "reversal",
    "container",
    "charade",
    "homophone",
    "deletion",
    "double_def",
)


def classify_device(parse: str, clue: str = "") -> Device:
    text = f"{parse} {clue}"
    if ANAGRAM.search(text):
        return "anagram"
    if HIDDEN.search(text):
        return "hidden"
    if HOMOPHONE.search(text):
        return "homophone"
    if REVERSAL.search(parse):
        return "reversal"
    if CONTAINER.search(parse):
        return "container"
    if DELETION.search(parse):
        return "deletion"
    if DOUBLE.search(parse):
        return "double_def"
    if CHARADE.search(parse):
        return "charade"
    return "unknown"
