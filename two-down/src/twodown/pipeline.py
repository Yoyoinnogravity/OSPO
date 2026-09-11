from __future__ import annotations

from datetime import datetime
from pathlib import Path

from twodown.config import (
    CLUES_PER_DAY,
    DEFAULT_OUTPUT,
    DEFAULT_VOICE_ALIAS,
    SITE_ROOT,
    THINK_PAUSE_SECONDS,
    VOICES,
)
from twodown.ingest import LONDON, fetch_daily_posts, posts_for_london_date
from twodown.models import DailyPair, SpokenClue
from twodown.parse import parse_post
from twodown.render import audio_seconds, draw_clue_card, draw_reveal_card, render_video
from twodown.script import write_parts
from twodown.select import select_pair
from twodown.site import publish_site
from twodown.voice import resolve_voice, synthesise, synthesise_parts
from twodown.youtube import upload_short, youtube_ready


def _today_stamp(day: datetime | None) -> str:
    when = day or datetime.now(tz=LONDON)
    return when.astimezone(LONDON).date().isoformat()


def _voice_alias(name: str | None) -> str:
    if not name:
        return DEFAULT_VOICE_ALIAS
    key = name.strip().lower()
    return key if key in VOICES else DEFAULT_VOICE_ALIAS


def run_today(
    out_dir: Path | None = None,
    voice: str | None = DEFAULT_VOICE_ALIAS,
    day: datetime | None = None,
    speak: bool = True,
    video: bool = True,
    publish: bool = True,
    youtube: bool = True,
    youtube_privacy: str = "unlisted",
) -> DailyPair:
    posts = fetch_daily_posts()
    todays = posts_for_london_date(posts, day)
    clues = [clue for post in todays for clue in parse_post(post)]
    pair_clues = select_pair(clues, n=CLUES_PER_DAY)
    stamp = _today_stamp(day if todays else None)
    if todays:
        stamp = todays[0].date.astimezone(LONDON).date().isoformat()
    dest_root = Path(out_dir or DEFAULT_OUTPUT) / stamp
    dest_root.mkdir(parents=True, exist_ok=True)
    alias = _voice_alias(voice)
    resolved_voice = resolve_voice(alias)
    spoken: list[SpokenClue] = []
    for clue in pair_clues:
        parts = write_parts(clue)
        item = SpokenClue(clue=clue, script=parts.full, voice=resolved_voice)
        slot = dest_root / clue.slug
        slot.mkdir(parents=True, exist_ok=True)
        (slot / "script.txt").write_text(parts.full + "\n", encoding="utf-8")
        (slot / "clue.txt").write_text(
            f"{clue.paper} {clue.puzzle_id} by {clue.setter}\n"
            f"{clue.number} {clue.direction}\n{clue.clue} ({clue.enumeration})\n"
            f"{clue.answer}\n{clue.device}\n{clue.source_url}\n",
            encoding="utf-8",
        )
        clue_card = draw_clue_card(clue, slot / "clue.png")
        reveal = draw_reveal_card(clue, slot / "card.png")
        item.clue_card_path = str(clue_card)
        item.card_path = str(reveal)
        if speak:
            clue_only = synthesise(parts.clue_speech, slot / "clue-only.mp3", alias)
            item.clue_hold_seconds = audio_seconds(clue_only) + THINK_PAUSE_SECONDS
            paths: dict[str, str] = {}
            for other in VOICES:
                audio = synthesise_parts(parts, slot / f"voice-{other}.mp3", other)
                paths[other] = str(audio)
            item.voice_paths = paths
            item.audio_path = paths[alias]
            if video:
                movie = render_video(
                    clue_card,
                    reveal,
                    Path(paths[alias]),
                    slot / "short.mp4",
                    clue_hold=item.clue_hold_seconds,
                )
                item.video_path = str(movie)
        spoken.append(item)
    result = DailyPair(
        date=stamp,
        voice=resolved_voice,
        clues=spoken,
        source_posts=[p.url for p in todays],
    )
    if publish and spoken:
        site = publish_site(result, SITE_ROOT)
        result.site_index = str(site / "index.html")
        (dest_root / "site-url.txt").write_text("https://cryptic.fun/\n", encoding="utf-8")
    if youtube:
        if not youtube_ready():
            (dest_root / "youtube-skipped.txt").write_text(
                "No YouTube OAuth token. Set TWODOWN_YOUTUBE_TOKEN to an authorized user JSON.\n",
                encoding="utf-8",
            )
        else:
            for item in spoken:
                video_id = upload_short(item, privacy=youtube_privacy)
                if video_id:
                    result.youtube_ids.append(video_id)
    (dest_root / "pair.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
