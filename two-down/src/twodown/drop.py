from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from twodown.captions import HASHTAGS
from twodown.config import BRAND, SITE_ORIGIN, SITE_ROOT, YOUTUBE_HANDLE
from twodown.models import DailyPair

CREATE = (
    ("YouTube channel", "https://www.youtube.com/create_channel"),
    ("Facebook Page", "https://www.facebook.com/pages/create"),
    ("Instagram", "https://www.instagram.com/"),
    ("TikTok", "https://www.tiktok.com/signup"),
)
UPLOAD = (
    ("YouTube Shorts", "https://www.youtube.com/upload"),
    ("Facebook Reels", "https://www.facebook.com/reels/create"),
    ("Instagram", "https://www.instagram.com/"),
    ("TikTok", "https://www.tiktok.com/tiktokstudio/upload"),
)
EXTRAS = (
    ("guardian-30115-23d", "Name of girl making second statement on first birthday (6)", "Guardian 30115 · Brendan"),
    ("financial-times-18483-26a", "Panicking, Indiana twice grabs snake (2,1,4)", "FT 18483 · Arrietty"),
    ("financial-times-18483-1a", "Maid struggling with a mess — newspapers etc (4,5)", "FT 18483 · Arrietty"),
)


@dataclass(frozen=True)
class DropFilm:
    slug: str
    clue: str
    credit: str
    video: Path | None

    @property
    def caption(self) -> str:
        return drop_caption(self.clue, self.credit)


def drop_caption(clue: str, credit: str) -> str:
    return (
        f"{BRAND} · {clue}\n\n"
        f"Have a think. The parse is in the video.\n"
        f"{credit}\n"
        f"{SITE_ORIGIN}/\n"
        f"{HASHTAGS}"
    )


def collect_drops(pair: DailyPair, root: Path | None = None) -> list[DropFilm]:
    root = Path(root or SITE_ROOT)
    films: list[DropFilm] = []
    seen: set[str] = set()
    for item in pair.clues:
        clue = item.clue
        enum = f" ({clue.enumeration})" if clue.enumeration else ""
        video = _video_for(item.video_path, root / "media" / f"{clue.slug}.mp4")
        films.append(
            DropFilm(
                clue.slug,
                f"{clue.clue}{enum}",
                f"{clue.paper} {clue.puzzle_id} · {clue.setter}",
                video,
            )
        )
        seen.add(clue.slug)
    for slug, line, credit in EXTRAS:
        if slug in seen:
            continue
        video = _video_for(None, root / "media" / f"{slug}.mp4")
        if video is None:
            continue
        films.append(DropFilm(slug, line, credit, video))
    return films


def how_to_invade() -> str:
    create = "\n".join(f"  {label}  {url}" for label, url in CREATE)
    upload = "\n".join(f"  {label}  {url}" for label, url in UPLOAD)
    return (
        f"{BRAND} — hand drop\n"
        f"Name every account {BRAND}.\n"
        f"Handle if it is free: @{YOUTUBE_HANDLE}\n"
        "Do not use @crypticfun.\n\n"
        "Create the four accounts, then upload each film as a Short or Reel.\n\n"
        f"Create:\n{create}\n\n"
        f"Upload:\n{upload}\n\n"
        "Captions are clue only. The answer stays in the film.\n"
    )


def write_drop_pack(pair: DailyPair, dest: Path | None = None, root: Path | None = None) -> Path:
    root = Path(root or SITE_ROOT)
    dest = Path(dest or (root / "drop.zip"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(dest, "w", ZIP_DEFLATED) as zf:
        zf.writestr("HOW.txt", how_to_invade())
        for film in collect_drops(pair, root):
            if film.video is None:
                continue
            zf.write(film.video, f"{film.slug}.mp4")
            zf.writestr(f"{film.slug}.txt", film.caption + "\n")
    return dest


def _video_for(explicit: str | None, fallback: Path) -> Path | None:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
    if fallback.exists():
        return fallback
    return None
