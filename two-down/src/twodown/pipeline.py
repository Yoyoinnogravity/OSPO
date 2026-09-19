from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2

from bs4 import BeautifulSoup

from twodown.config import (
    CLUES_PER_DAY,
    DEFAULT_OUTPUT,
    DEFAULT_VOICE_ALIAS,
    SITE_ORIGIN,
    SITE_ROOT,
    SOURCE_SITE,
    STUDY_SLUG,
    VOICES,
)
from twodown.hints import attach_hint
from twodown.ingest import LONDON, fetch_daily_posts, posts_for_london_date
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.parse import parse_post
from twodown.render import draw_beat, draw_clue_card, draw_reveal_card, render_video
from twodown.scenes import pick_scenes
from twodown.script import write_parts
from twodown.select import select_pair
from twodown.site import publish_site
from twodown.social import attach_site_videos, publish_pair, setup_hints
from twodown.voice import build_short_soundtrack, resolve_voice, synthesise_parts

_KICKER = re.compile(
    r"^(?P<paper>.+) (?P<puzzle_id>\d+) · (?P<setter>.+) · "
    r"(?P<number>\d+) (?P<direction>\w+) · (?P<device>.+)$"
)
_CLUE_LINE = re.compile(r"^(?P<clue>.+) \((?P<enum>[^)]+)\)$")


def _today_stamp(day: datetime | None) -> str:
    when = day or datetime.now(tz=LONDON)
    return when.astimezone(LONDON).date().isoformat()


def _voice_alias(name: str | None) -> str:
    if not name:
        return DEFAULT_VOICE_ALIAS
    key = name.strip().lower()
    return key if key in VOICES else DEFAULT_VOICE_ALIAS


def published_clue(slug: str, site_root: Path | None = None) -> Clue:
    """Read one already-published clue back from the static site."""
    root = Path(site_root or SITE_ROOT)
    for page in sorted((root / "d").glob("*/index.html")):
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
        article = soup.select_one(f'article.clue[data-slug="{slug}"]')
        if article is None:
            continue
        kicker = article.select_one("p.kicker")
        line = article.select_one("p.clue-text")
        answer = article.select_one("p.answer")
        parse = article.select_one("p.parse")
        credit = article.select_one("p.credit a")
        if not all([kicker, line, answer, parse, credit]):
            raise ValueError(f"Incomplete published clue {slug} on {page}")
        match = _KICKER.match(kicker.get_text(" ", strip=True))
        clue_match = _CLUE_LINE.match(line.get_text(" ", strip=True))
        if not match or not clue_match:
            raise ValueError(f"Could not parse published clue {slug}")
        blogger = credit.get_text(" ", strip=True).split("·", 1)[-1].strip()
        return Clue(
            source_url=str(credit["href"]),
            paper=match["paper"],
            puzzle_id=match["puzzle_id"],
            setter=match["setter"],
            blogger=blogger,
            number=match["number"],
            direction=match["direction"],
            clue=clue_match["clue"],
            enumeration=clue_match["enum"],
            answer=answer.get_text(" ", strip=True),
            parse=htmlmod.unescape(parse.get_text(" ", strip=True)),
            device=match["device"],
            enumeration_ok=True,
        )
    raise FileNotFoundError(f"No published clue {slug}")


# Guardian 30115 — Aled's study clues. Metadata from Fifteen Squared
# https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/
# (setter Brendan, blogger manehi). Clue/parse wording is Aled's / the blog.
_DREAMLIKE_PARSE = (
    'anagram/"Doctor" of (armed)*; plus LIKE="positive response" e.g. on social media. '
    '"Doctor" as a verb meaning to falsify or to tamper with, to indicate the anagram.'
)
_RASTA_SOURCE = (
    "https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/"
)


def dreamlike_clue() -> Clue:
    """Construct DREAMLIKE so we can study the locked beat off the published site.

    Aled's bar: auto / AI matching at about 80% closeness is good enough.
    attach_hint picks a trance/dream still from the definition text.
    The still must not print DREAMLIKE.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="12",
            direction="across",
            clue="Doctor armed with positive response, as in a trance",
            enumeration="9",
            answer="DREAMLIKE",
            definition="as in a trance",
            parse=_DREAMLIKE_PARSE,
            device="anagram",
            enumeration_ok=True,
        )
    )


def rasta_clue() -> Clue:
    """Guardian 30115 20a RASTA — leftover study construct. On Fifteen Squared.

    Definition still may be generated or selected if it is ~80% close.
    Hint the definition, not the wordplay. Do not print RASTA on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="20",
            direction="across",
            clue="One emperor backing follower of another",
            enumeration="5",
            answer="RASTA",
            definition="a RASTA may be a follower of the Emperor Haile Selassie",
            parse="A + TSAR, backing",
            device="reversal",
            enumeration_ok=True,
        )
    )


def fats_clue() -> Clue:
    """Guardian 30115 1d FATS — leftover study construct. On Fifteen Squared.

    Definition still may be generated or selected if it is ~80% close.
    Hint the definition (unhealthy foods), not the wordplay (FAST / twist).
    Do not print FATS on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="1",
            direction="down",
            clue="Refrain from eating, with final twist, such unhealthy foods",
            enumeration="4",
            answer="FATS",
            definition="such unhealthy foods",
            parse='FAST="Refrain from eating", with a final twist (last two letters change places)',
            device="unknown",
            enumeration_ok=True,
        )
    )


def wellington_clue() -> Clue:
    """Guardian 30115 3d WELLINGTON — leftover study construct. On Fifteen Squared.

    Hint the definition (Duke), not the wordplay (well in / G / ton).
    Do not print WELLINGTON on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="3",
            direction="down",
            clue="Duke is thoroughly acquainted with good style",
            enumeration="10",
            answer="WELLINGTON",
            definition="Duke",
            parse='WELL IN="thoroughly acquainted" + G (good) + TON="style"',
            device="charade",
            enumeration_ok=True,
        )
    )


def cole_clue() -> Clue:
    """Guardian 30115 8d COLE — leftover study construct. On Fifteen Squared.

    Hint Nat King Cole (definition), not Old King Cole / fiddlers three.
    Do not print COLE on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="8",
            direction="down",
            clue="So-called King of jazz, or another one accompanied by string trio",
            enumeration="4",
            answer="COLE",
            definition="King, as in Nat King Cole the jazz musician",
            parse=(
                "King as in Nat King Cole; or Old King Cole, who called for "
                "his fiddlers three, a string trio"
            ),
            device="double_def",
            enumeration_ok=True,
        )
    )


def smiles_clue() -> Clue:
    """Guardian 30115 2d SMILES — leftover study construct. On Fifteen Squared.

    Hint visibly pleased (definition), not school / miles.
    Do not print SMILES on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="2",
            direction="down",
            clue="First in school by a long way, is visibly pleased",
            enumeration="6",
            answer="SMILES",
            definition="visibly pleased",
            parse='S, first letter of school, plus MILES="a long way"',
            device="charade",
            enumeration_ok=True,
        )
    )


def davis_cup_clue() -> Clue:
    """Guardian 30115 18d DAVIS CUP — leftover. Aled said no. On ice.

    Hint the tennis-court definition, not divas / cricket C / UP.
    Do not print DAVIS CUP on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="18",
            direction="down",
            clue="Frenzied divas caught up in international court event",
            enumeration="5,3",
            answer="DAVIS CUP",
            definition="international court event",
            parse="Frenzied, anagram of divas, plus C, caught, plus UP",
            device="anagram",
            enumeration_ok=True,
        )
    )


def aimlessly_clue() -> Clue:
    """Guardian 30115 9a AIMLESSLY — leftover study construct. On Fifteen Squared.

    Hint end as a goal or aim, not sly / e-mails / recycle.
    Do not print AIMLESSLY on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_RASTA_SOURCE,
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="9",
            direction="across",
            clue="Sly e-mails recycled without end",
            enumeration="9",
            answer="AIMLESSLY",
            definition="end, as in a goal or aim",
            parse='anagram/"recycled" of (Sly e-mails)*',
            device="anagram",
            enumeration_ok=True,
        )
    )


_MASS_MEDIA_SOURCE = (
    "https://fifteensquared.net/2026/09/18/financial-times-18483-by-arrietty/"
)


def mass_media_clue() -> Clue:
    """FT 18483 1a MASS MEDIA — current study Short. On Fifteen Squared.

    Hint newspapers / the press, not maid / mess.
    Do not print MASS MEDIA on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_MASS_MEDIA_SOURCE,
            paper="Financial Times",
            puzzle_id="18483",
            setter="Arrietty",
            blogger="Turbolegs",
            number="1",
            direction="across",
            clue="Maid struggling with a mess — newspapers etc",
            enumeration="4,5",
            answer="MASS MEDIA",
            definition="newspapers, the press",
            parse='anagram/"struggling" of (Maid a mess)*',
            device="anagram",
            enumeration_ok=True,
        )
    )


def in_a_spin_clue() -> Clue:
    """FT 18483 26a IN A SPIN — next study Short. On Fifteen Squared.

    Hint panicking, not Indiana / snake / a spinning top that prints the answer.
    Do not print IN A SPIN on the hint card.
    """
    return attach_hint(
        Clue(
            source_url=_MASS_MEDIA_SOURCE,
            paper="Financial Times",
            puzzle_id="18483",
            setter="Arrietty",
            blogger="Turbolegs",
            number="26",
            direction="across",
            clue="Panicking, Indiana twice grabs snake",
            enumeration="2,1,4",
            answer="IN A SPIN",
            definition="Panicking",
            parse="IN IN (Indiana, twice) containing ASP (snake)",
            device="container",
            enumeration_ok=True,
        )
    )


def study_clues() -> dict[str, Clue]:
    """MASS MEDIA is the study default. Earlier study clues stay constructable."""
    dreamlike = dreamlike_clue()
    rasta = rasta_clue()
    fats = fats_clue()
    wellington = wellington_clue()
    cole = cole_clue()
    smiles = smiles_clue()
    davis = davis_cup_clue()
    aimlessly = aimlessly_clue()
    mass_media = mass_media_clue()
    in_a_spin = in_a_spin_clue()
    return {
        dreamlike.slug: dreamlike,
        "dreamlike": dreamlike,
        dreamlike.answer.lower(): dreamlike,
        rasta.slug: rasta,
        "rasta": rasta,
        "study-rasta-5": rasta,
        rasta.answer.lower(): rasta,
        fats.slug: fats,
        "fats": fats,
        "study-fats-4": fats,
        fats.answer.lower(): fats,
        wellington.slug: wellington,
        "wellington": wellington,
        "study-wellington-10": wellington,
        wellington.answer.lower(): wellington,
        cole.slug: cole,
        "cole": cole,
        "study-cole-4": cole,
        cole.answer.lower(): cole,
        smiles.slug: smiles,
        "smiles": smiles,
        "study-smiles-6": smiles,
        smiles.answer.lower(): smiles,
        davis.slug: davis,
        "davis": davis,
        "davis-cup": davis,
        "davis cup": davis,
        "study-davis-cup-5-3": davis,
        davis.answer.lower(): davis,
        aimlessly.slug: aimlessly,
        "aimlessly": aimlessly,
        "study-aimlessly-9": aimlessly,
        aimlessly.answer.lower(): aimlessly,
        mass_media.slug: mass_media,
        "mass-media": mass_media,
        "mass media": mass_media,
        "study-mass-media-4-5": mass_media,
        mass_media.answer.lower(): mass_media,
        STUDY_SLUG: mass_media,
        in_a_spin.slug: in_a_spin,
        "in-a-spin": in_a_spin,
        "in a spin": in_a_spin,
        in_a_spin.answer.lower(): in_a_spin,
    }


def study_clue(slug: str | None = None) -> Clue | None:
    """Return a constructed study Clue, or None if this slug is not a study clue."""
    return study_clues().get(slug or STUDY_SLUG)


def resolve_clue(slug: str, site_root: Path | None = None, clue: Clue | None = None) -> Clue:
    """Prefer a passed Clue, then a constructed study clue, then published site HTML."""
    if clue is not None:
        return clue
    constructed = study_clue(slug)
    if constructed is not None:
        return constructed
    return published_clue(slug, site_root)


def render_one_short(
    slug: str = STUDY_SLUG,
    dest: Path | None = None,
    voices: list[str] | None = None,
    publish: bool = True,
    clue: Clue | None = None,
) -> SpokenClue:
    """Rebuild one Short. Does not touch the other published films."""
    clue = resolve_clue(slug, clue=clue)
    aliases = list(voices or [DEFAULT_VOICE_ALIAS])
    primary = aliases[0]
    slot = Path(dest or DEFAULT_OUTPUT) / "study" / clue.slug
    slot.mkdir(parents=True, exist_ok=True)
    parts = write_parts(clue)
    (slot / "script.txt").write_text(parts.full + "\n", encoding="utf-8")
    item = SpokenClue(clue=clue, script=parts.full, voice=resolve_voice(primary))
    clue_card = draw_clue_card(clue, slot / "clue.png")
    draw_beat(clue, slot / "hint.png", "hint")
    reveal = draw_reveal_card(clue, slot / "card.png")
    item.clue_card_path = str(clue_card)
    item.card_path = str(reveal)
    paths: dict[str, str] = {}
    timings = None
    if primary == DEFAULT_VOICE_ALIAS:
        timings = build_short_soundtrack(parts, slot / f"voice-{primary}.mp3", primary)
        paths[primary] = str(slot / f"voice-{primary}.mp3")
        item.clue_hold_seconds = timings.until_answer
    else:
        audio = synthesise_parts(parts, slot / f"voice-{primary}.mp3", primary)
        paths[primary] = str(audio)
    for alias in aliases[1:]:
        audio = synthesise_parts(parts, slot / f"voice-{alias}.mp3", alias)
        paths[alias] = str(audio)
    item.voice_paths = paths
    item.audio_path = paths[primary]
    movie = render_video(
        clue_card,
        reveal,
        Path(paths[primary]),
        slot / "short.mp4",
        clue_hold=item.clue_hold_seconds,
        clue=clue,
        timings=timings,
    )
    item.video_path = str(movie)
    if publish:
        media = SITE_ROOT / "media"
        media.mkdir(parents=True, exist_ok=True)
        copy2(movie, media / f"{clue.slug}.mp4")
        for alias, path in paths.items():
            copy2(path, media / f"{clue.slug}-{alias}.mp3")
    return item


def published_date(site_root: Path | None, date: str) -> bool:
    """True when today's archive page is already on the static site."""
    root = Path(site_root or SITE_ROOT)
    return (root / "d" / date / "index.html").exists()


def site_day_page(date: str | None = None, site_root: Path | None = None) -> Path:
    """Latest (or named) published day page under two-down/site/d/."""
    root = Path(site_root or SITE_ROOT)
    if date:
        page = root / "d" / date / "index.html"
        if not page.exists():
            raise FileNotFoundError(f"No published day {date}")
        return page
    days = sorted((root / "d").glob("*/index.html"))
    if not days:
        raise FileNotFoundError("No published days on the site")
    return days[-1]


def site_pair(date: str | None = None, site_root: Path | None = None) -> DailyPair:
    """Rebuild a DailyPair from published site HTML and site/media films."""
    page = site_day_page(date, site_root)
    stamp = page.parent.name
    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
    slugs = [tag.get("data-slug") for tag in soup.select("article.clue[data-slug]")]
    slugs = [slug for slug in slugs if slug]
    if not slugs:
        raise FileNotFoundError(f"No clues on {page}")
    items: list[SpokenClue] = []
    for slug in slugs:
        clue = published_clue(slug, site_root)
        items.append(
            SpokenClue(
                clue=clue,
                script="",
                voice=resolve_voice(DEFAULT_VOICE_ALIAS),
                site_path=f"{SITE_ORIGIN}/c/{slug}/",
            )
        )
    pair = DailyPair(
        date=stamp,
        voice=resolve_voice(DEFAULT_VOICE_ALIAS),
        clues=items,
        site_index=str((site_root or SITE_ROOT) / "index.html"),
        already_published=True,
    )
    return attach_site_videos(pair, site_root)


def _load_complete_pair(dest_root: Path) -> DailyPair | None:
    path = dest_root / "pair.json"
    if not path.exists():
        return None
    pair = DailyPair.model_validate_json(path.read_text(encoding="utf-8"))
    if len(pair.clues) < CLUES_PER_DAY:
        return None
    for item in pair.clues:
        if not item.video_path or not Path(item.video_path).exists():
            return None
    return pair


def run_today(
    out_dir: Path | None = None,
    voice: str | None = DEFAULT_VOICE_ALIAS,
    day: datetime | None = None,
    speak: bool = True,
    video: bool = True,
    publish: bool = True,
    youtube: bool = True,
    youtube_privacy: str = "public",
    scene: str | None = None,
    tiktok: bool = True,
    instagram: bool = True,
    facebook: bool = True,
    force: bool = False,
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
    if not force:
        existing = _load_complete_pair(dest_root)
        if existing:
            existing.already_published = True
            if youtube or tiktok or instagram or facebook:
                notes = publish_pair(
                    existing,
                    youtube=youtube,
                    tiktok=tiktok,
                    instagram=instagram,
                    facebook=facebook,
                    youtube_privacy=youtube_privacy,
                )
                lines: list[str] = []
                hints = setup_hints()
                for platform, values in notes.items():
                    if values == [hints.get(platform)]:
                        lines.append(f"{platform}: skipped — {values[0]}")
                    elif values:
                        lines.append(f"{platform}: {', '.join(values)}")
                if lines:
                    (dest_root / "social-status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
                (dest_root / "pair.json").write_text(existing.model_dump_json(indent=2), encoding="utf-8")
            return existing
        if published_date(SITE_ROOT, stamp):
            try:
                skipped = site_pair(stamp)
            except FileNotFoundError:
                skipped = DailyPair(
                    date=stamp,
                    voice=resolve_voice(_voice_alias(voice)),
                    source_posts=[p.url for p in todays],
                    source_site=SOURCE_SITE,
                    site_index=str(SITE_ROOT / "index.html"),
                    already_published=True,
                )
            skipped.source_posts = [p.url for p in todays]
            skipped.already_published = True
            if skipped.clues and (youtube or tiktok or instagram or facebook):
                notes = publish_pair(
                    skipped,
                    youtube=youtube,
                    tiktok=tiktok,
                    instagram=instagram,
                    facebook=facebook,
                    youtube_privacy=youtube_privacy,
                )
                lines = []
                hints = setup_hints()
                for platform, values in notes.items():
                    if values == [hints.get(platform)]:
                        lines.append(f"{platform}: skipped — {values[0]}")
                    elif values:
                        lines.append(f"{platform}: {', '.join(values)}")
                if lines:
                    (dest_root / "social-status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            (dest_root / "already-published.txt").write_text(
                f"{stamp} already on cryptic.fit. Pass --force to rebuild.\n",
                encoding="utf-8",
            )
            if skipped.clues:
                (dest_root / "pair.json").write_text(skipped.model_dump_json(indent=2), encoding="utf-8")
            return skipped
    alias = _voice_alias(voice)
    resolved_voice = resolve_voice(alias)
    scene_slugs = pick_scenes(stamp, len(pair_clues), scene)
    spoken: list[SpokenClue] = []
    for clue, scene_slug in zip(pair_clues, scene_slugs, strict=True):
        parts = write_parts(clue)
        item = SpokenClue(clue=clue, script=parts.full, voice=resolved_voice, scene=scene_slug)
        slot = dest_root / clue.slug
        slot.mkdir(parents=True, exist_ok=True)
        (slot / "script.txt").write_text(parts.full + "\n", encoding="utf-8")
        (slot / "clue.txt").write_text(
            f"{clue.paper} {clue.puzzle_id} by {clue.setter}\n"
            f"{clue.number} {clue.direction}\n{clue.clue} ({clue.enumeration})\n"
            f"{clue.answer}\n{clue.device}\n{clue.source_url}\n"
            f"{scene_slug}\n",
            encoding="utf-8",
        )
        clue_card = draw_clue_card(clue, slot / "clue.png", scene=scene_slug)
        reveal = draw_reveal_card(clue, slot / "card.png", scene=scene_slug)
        item.clue_card_path = str(clue_card)
        item.card_path = str(reveal)
        if speak:
            paths: dict[str, str] = {}
            timings = build_short_soundtrack(parts, slot / f"voice-{alias}.mp3", alias)
            paths[alias] = str(slot / f"voice-{alias}.mp3")
            item.clue_hold_seconds = timings.until_answer
            for other in VOICES:
                if other == alias:
                    continue
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
                    clue=clue,
                    timings=timings,
                )
                item.video_path = str(movie)
        spoken.append(item)
    result = DailyPair(
        date=stamp,
        voice=resolved_voice,
        clues=spoken,
        source_posts=[p.url for p in todays],
        source_site=SOURCE_SITE,
    )
    if publish and spoken:
        site = publish_site(result, SITE_ROOT)
        result.site_index = str(site / "index.html")
        (dest_root / "site-url.txt").write_text(f"{SITE_ORIGIN}/\n", encoding="utf-8")
    if youtube or tiktok or instagram or facebook:
        notes = publish_pair(
            result,
            youtube=youtube,
            tiktok=tiktok,
            instagram=instagram,
            facebook=facebook,
            youtube_privacy=youtube_privacy,
        )
        lines: list[str] = []
        hints = setup_hints()
        for platform, values in notes.items():
            if values == [hints.get(platform)]:
                lines.append(f"{platform}: skipped — {values[0]}")
            elif values:
                lines.append(f"{platform}: {', '.join(values)}")
        if lines:
            (dest_root / "social-status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest_root / "pair.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
