from __future__ import annotations

from datetime import datetime
from pathlib import Path

from twodown.config import DEFAULT_OUTPUT, DEFAULT_VOICE_ALIAS
from twodown.ingest import LONDON, fetch_daily_posts, posts_for_london_date
from twodown.models import DailyPair, SpokenClue
from twodown.parse import parse_post
from twodown.render import draw_card, render_video
from twodown.script import write_script
from twodown.select import select_pair
from twodown.voice import resolve_voice, synthesise

# Re-export timezone helper without a circular import from config.
def _today_stamp(day: datetime | None) -> str:
    when = day or datetime.now(tz=LONDON)
    return when.astimezone(LONDON).date().isoformat()


def run_today(
    out_dir: Path | None = None,
    voice: str | None = DEFAULT_VOICE_ALIAS,
    day: datetime | None = None,
    speak: bool = True,
    video: bool = True,
) -> DailyPair:
    posts = fetch_daily_posts()
    todays = posts_for_london_date(posts, day)
    clues = [clue for post in todays for clue in parse_post(post)]
    pair = select_pair(clues, n=2)
    stamp = _today_stamp(day if todays else None)
    if todays:
        stamp = todays[0].date.astimezone(LONDON).date().isoformat()
    dest_root = Path(out_dir or DEFAULT_OUTPUT) / stamp
    dest_root.mkdir(parents=True, exist_ok=True)
    resolved_voice = resolve_voice(voice)
    spoken: list[SpokenClue] = []
    for clue in pair:
        script = write_script(clue)
        item = SpokenClue(clue=clue, script=script, voice=resolved_voice)
        slot = dest_root / clue.slug
        slot.mkdir(parents=True, exist_ok=True)
        (slot / "script.txt").write_text(script + "\n", encoding="utf-8")
        (slot / "clue.txt").write_text(
            f"{clue.paper} {clue.puzzle_id} by {clue.setter}\n"
            f"{clue.number} {clue.direction}\n{clue.clue} ({clue.enumeration})\n"
            f"{clue.answer}\n{clue.device}\n{clue.source_url}\n",
            encoding="utf-8",
        )
        card = draw_card(clue, slot / "card.png")
        item.card_path = str(card)
        if speak:
            audio = synthesise(script, slot / "voice.mp3", resolved_voice)
            item.audio_path = str(audio)
            if video:
                movie = render_video(card, audio, slot / "short.mp4")
                item.video_path = str(movie)
        spoken.append(item)
    result = DailyPair(
        date=stamp,
        voice=resolved_voice,
        clues=spoken,
        source_posts=[p.url for p in todays],
    )
    (dest_root / "pair.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
