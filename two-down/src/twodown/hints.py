"""Hand-picked definition stills — not an AI image-matcher.

Product rule: no general “match answer to picture” pipeline. Only the
DREAMLIKE study clue has a human-chosen definition still for “as in a
trance”. Do not add a matcher, embedder, or vision API here.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw

from twodown.config import PACKAGE_ROOT, USER_AGENT

HINTS_DIR = PACKAGE_ROOT / "assets" / "hints"


@dataclass(frozen=True)
class HintPhoto:
    slug: str
    label: str
    photographer: str
    license: str
    commons_file: str
    filename: str

    @property
    def path(self) -> Path:
        return HINTS_DIR / self.filename

    @property
    def commons_url(self) -> str:
        name = self.commons_file.replace(" ", "_")
        return "https://commons.wikimedia.org/wiki/File:" + quote(name, safe="_,()'-")

    @property
    def credit_line(self) -> str:
        return f"{self.label} · {self.photographer} / Wikimedia Commons ({self.license})"


# Trance / sleep still for DREAMLIKE's definition (“as in a trance”).
# Human-chosen. Not wordplay. Not a travel scene. Credited on the film.
MOONLIT = HintPhoto(
    slug="moonlit-moments",
    label="Moon",
    photographer="Linda Xu",
    license="CC0",
    commons_file="Moonlit Moments (Unsplash).jpg",
    filename="moonlit-moments.webp",
)

DEFAULT_HINT = MOONLIT


def get_hint_photo(slug: str | None = None) -> HintPhoto:
    if slug in {None, "", MOONLIT.slug, "dreamlike"}:
        return MOONLIT
    raise ValueError(f"Unknown hint photo {slug!r}")


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "image/*, application/json"}


def _fetch_commons(photo: HintPhoto, dest: Path) -> bool:
    api = (
        "https://commons.wikimedia.org/w/api.php"
        "?action=query&prop=imageinfo&iiprop=url&iiurlwidth=1280"
        f"&titles=File:{quote(photo.commons_file)}&format=json"
    )
    try:
        meta = requests.get(api, headers=_headers(), timeout=30)
        meta.raise_for_status()
        pages = meta.json()["query"]["pages"]
        info = next(iter(pages.values()))["imageinfo"][0]
        url = info.get("thumburl") or info["url"]
        raw = requests.get(url, headers=_headers(), timeout=60)
        raw.raise_for_status()
        image = Image.open(BytesIO(raw.content)).convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "WEBP", quality=82, method=6)
        return dest.exists() and dest.stat().st_size > 0
    except (OSError, KeyError, ValueError, requests.RequestException):
        return False


def _generate_moon_still(dest: Path) -> Path:
    """Last-resort still if Commons is unreachable. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 848), (16, 20, 32))
    draw = ImageDraw.Draw(img)
    draw.ellipse((140, 520, 620, 980), fill=(28, 34, 48))
    draw.ellipse((700, 90, 1040, 430), fill=(236, 226, 198))
    draw.ellipse((760, 70, 1080, 390), fill=(16, 20, 32))
    for box in ((80, 620, 420, 780), (360, 680, 820, 860), (700, 600, 1200, 820)):
        draw.ellipse(box, fill=(38, 44, 60))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def ensure_hint_photo(photo: HintPhoto | None = None) -> Path:
    resolved = photo or DEFAULT_HINT
    dest = resolved.path
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    if _fetch_commons(resolved, dest):
        return dest
    return _generate_moon_still(dest)
