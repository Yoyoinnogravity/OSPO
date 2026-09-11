from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Device = Literal[
    "anagram",
    "hidden",
    "reversal",
    "container",
    "charade",
    "homophone",
    "deletion",
    "double_def",
    "unknown",
]


class PuzzlePost(BaseModel):
    post_id: int
    url: str
    title: str
    date: datetime
    paper: str
    puzzle_id: str
    setter: str
    blogger: str
    category_slugs: list[str]
    html: str


class Clue(BaseModel):
    source_url: str
    paper: str
    puzzle_id: str
    setter: str
    blogger: str
    number: str
    direction: str
    clue: str
    enumeration: str
    answer: str
    definition: str | None = None
    parse: str
    device: Device = "unknown"
    enumeration_ok: bool = False
    skipped_reason: str | None = None

    @property
    def slug(self) -> str:
        paper = self.paper.lower().replace(" ", "-")
        return f"{paper}-{self.puzzle_id}-{self.number}{self.direction[:1]}"


class SpokenClue(BaseModel):
    clue: Clue
    script: str
    voice: str
    audio_path: str | None = None
    card_path: str | None = None
    video_path: str | None = None


class DailyPair(BaseModel):
    date: str
    voice: str
    clues: list[SpokenClue] = Field(default_factory=list)
    source_posts: list[str] = Field(default_factory=list)
