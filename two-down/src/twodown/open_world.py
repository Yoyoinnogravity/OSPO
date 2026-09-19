from __future__ import annotations

import re
from pathlib import Path

from twodown.config import DEFAULT_OUTPUT, SITE_ROOT

SLUG_MP4 = re.compile(
    r"^(independent|independent-on-sunday|financial-times|guardian)-\d+-\d+[ad]\.mp4$"
)


def _clue_from_script(slug: str) -> str | None:
    script = DEFAULT_OUTPUT / "bomb" / "study" / slug / "script.txt"
    if not script.exists():
        return None
    lines = [line.strip() for line in script.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    clue = lines[1]
    if clue.lower().startswith("it's ") or clue.lower().startswith("hi i am"):
        return None
    return clue


def _clue_from_published(slug: str, root: Path) -> str | None:
    page = root / "c" / slug / "index.html"
    if not page.exists():
        return None
    text = page.read_text(encoding="utf-8")
    match = re.search(r'<p class="clue-text">(.*?)</p>', text, re.S)
    if not match:
        return None
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def open_films(root: Path | None = None) -> list[dict[str, str]]:
    """Public films only. Clue text, no answers."""
    site = Path(root or SITE_ROOT)
    media = site / "media"
    rows: list[dict[str, str]] = []
    if not media.exists():
        return rows
    for path in sorted(media.glob("*.mp4")):
        if not SLUG_MP4.match(path.name):
            continue
        if path.stat().st_size < 1000:
            continue
        slug = path.stem
        clue = _clue_from_published(slug, site) or _clue_from_script(slug) or slug
        rows.append({"slug": slug, "clue": clue, "video": f"media/{slug}.mp4"})
    return rows
