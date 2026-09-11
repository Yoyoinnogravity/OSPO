from __future__ import annotations

from datetime import datetime
from pathlib import Path

from twodown.config import DEFAULT_OUTPUT, DEFAULT_VOICE_ALIAS, SITE_ROOT
from twodown.ingest import LONDON, fetch_daily_posts, posts_for_london_date
from twodown.models import DailyPair, SpokenClue
from twodown.parse import parse_post
from twodown.render import draw_clue_card, draw_reveal_card, render_video
from twodown.script import write_script
from twodown.select import select_pair
from twodown.site import publish_site
from twodown.voice import resolve_voice, synthesise
from twodown.youtube import upload_short, youtube_ready


def _today_stamp(day: datetime | None) -> str:
    when = day or datetime.now(tz=LONDON)
    return when.astimezone(LONDON).date().isoformat()


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
    pair_clues = select_pair(clues, n=2)
    stamp = _today_stamp(day if todays else None)
    if todays:
        stamp = todays[0].date.astimezone(LONDON).date().isoformat()
    dest_root = Path(out_dir or DEFAULT_OUTPUT) / stamp
    dest_root.mkdir(parents=True, exist_ok=True)
    resolved_voice = resolve_voice(voice)
    spoken: list[SpokenClue] = []
    for clue in pair_clues:
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
        clue_card = draw_clue_card(clue, slot / "clue.png")
        reveal = draw_reveal_card(clue, slot / "card.png")
        item.clue_card_path = str(clue_card)
        item.card_path = str(reveal)
        if speak:
            audio = synthesise(script, slot / "voice.mp3", resolved_voice)
            item.audio_path = str(audio)
            if video:
                movie = render_video(clue_card, reveal, audio, slot / "short.mp4")
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
