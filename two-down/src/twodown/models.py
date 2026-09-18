from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from twodown.config import SOURCE_SITE

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
    # Human-chosen definition still only. Never an AI-selected match.
    # Leave None on published clues — there is no general picture matcher.
    hint_image: str | None = None
    hint_credit: str | None = None
    hint_line: str | None = None

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
    clue_card_path: str | None = None
    video_path: str | None = None
    youtube_id: str | None = None
    tiktok_id: str | None = None
    instagram_id: str | None = None
    facebook_id: str | None = None
    site_path: str | None = None
    voice_paths: dict[str, str] = Field(default_factory=dict)
    clue_hold_seconds: float | None = None
    scene: str | None = None


class DailyPair(BaseModel):
    date: str
    voice: str
    clues: list[SpokenClue] = Field(default_factory=list)
    source_posts: list[str] = Field(default_factory=list)
    source_site: str = SOURCE_SITE
    youtube_ids: list[str] = Field(default_factory=list)
    tiktok_ids: list[str] = Field(default_factory=list)
    instagram_ids: list[str] = Field(default_factory=list)
    facebook_ids: list[str] = Field(default_factory=list)
    site_index: str | None = None
    already_published: bool = False
