from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter

from twodown.config import HINT_LINE, PACKAGE_ROOT, USER_AGENT
from twodown.models import Clue

HINTS_DIR = PACKAGE_ROOT / "assets" / "hints"
# Aled's bar: auto / AI matching at about 80% closeness is good enough.
# Do not ban AI matching. Do not wait for a perfect image.
# A curated-only / human-only gate is superseded.
CLOSE_ENOUGH = 0.8
_STOP = frozenset(
    {
        "as",
        "in",
        "a",
        "an",
        "the",
        "of",
        "to",
        "and",
        "or",
        "for",
        "with",
        "on",
        "at",
        "by",
        "from",
        "into",
        "one",
        "ones",
        "one's",
        "may",
        "be",
        "another",
        "such",
    }
)


@dataclass(frozen=True)
class HintPhoto:
    slug: str
    label: str
    source: str
    license: str
    filename: str
    keywords: frozenset[str]
    commons_file: str | None = None

    @property
    def path(self) -> Path:
        return HINTS_DIR / self.filename

    @property
    def commons_url(self) -> str | None:
        if not self.commons_file:
            return None
        name = self.commons_file.replace(" ", "_")
        return "https://commons.wikimedia.org/wiki/File:" + quote(name, safe="_,()'-")

    @property
    def photographer(self) -> str:
        return self.source

    @property
    def credit_line(self) -> str:
        if self.commons_file:
            return f"{self.label} · {self.source} / Wikimedia Commons ({self.license})"
        return f"{self.label} · {self.source}"


@dataclass(frozen=True)
class MatchedHint:
    photo: HintPhoto
    closeness: float
    close_enough: bool

    @property
    def slug(self) -> str:
        return self.photo.slug

    @property
    def line(self) -> str:
        return HINT_LINE


# Sleeping face in soft haze. Reads as trance / dream / as-in-a-trance ~80% of the time.
# Generated still (AI matching allowed). No answer text.
TRANCE = HintPhoto(
    slug="trance-still",
    label="As in a trance",
    source="generated still",
    license="generated",
    filename="trance-still.webp",
    keywords=frozenset(
        {
            "trance",
            "dream",
            "dreamlike",
            "sleep",
            "asleep",
            "hypnosis",
            "reverie",
            "daze",
            "swoon",
            "doze",
        }
    ),
)

# Optional Commons alternate. Night / moon — not the DREAMLIKE default.
MOONLIT = HintPhoto(
    slug="moonlit-moments",
    label="Moon",
    source="Linda Xu",
    license="CC0",
    filename="moonlit-moments.webp",
    keywords=frozenset({"moon", "moonlight", "night", "lunar"}),
    commons_file="Moonlit Moments (Unsplash).jpg",
)

# Definition still for RASTA: Rastafari / follower of Haile Selassie.
# Generated still (AI matching allowed). No answer text, no wordplay.
RASTA = HintPhoto(
    slug="rasta-still",
    label="Rastafari",
    source="generated still",
    license="generated",
    filename="rasta-still.webp",
    keywords=frozenset(
        {
            "rasta",
            "rastafari",
            "rastafarian",
            "follower",
            "emperor",
            "haile",
            "selassie",
            "ethiopia",
            "ethiopian",
            "dreadlock",
            "dreadlocks",
            "lion",
            "judah",
        }
    ),
)

# Definition still for FATS: unhealthy foods, not fasting / FAST.
# Generated still (AI matching allowed). No answer text, no wordplay.
FATS = HintPhoto(
    slug="fats-still",
    label="Unhealthy foods",
    source="generated still",
    license="generated",
    filename="fats-still.webp",
    keywords=frozenset(
        {
            "fat",
            "fats",
            "food",
            "foods",
            "unhealthy",
            "unhealth",
            "greasy",
            "fried",
            "butter",
            "chips",
            "oil",
            "burger",
        }
    ),
)


# Definition still for WELLINGTON: a Duke, not boots / well-in / ton.
WELLINGTON = HintPhoto(
    slug="wellington-still",
    label="Duke",
    source="generated still",
    license="generated",
    filename="wellington-still.webp",
    keywords=frozenset(
        {
            "duke",
            "ducal",
            "noble",
            "aristocrat",
            "military",
            "portrait",
            "general",
        }
    ),
)


# Definition still for SMILES: visibly pleased, not school / miles.
SMILES = HintPhoto(
    slug="smiles-still",
    label="Visibly pleased",
    source="generated still",
    license="generated",
    filename="smiles-still.webp",
    keywords=frozenset(
        {
            "pleased",
            "pleas",
            "visibly",
            "visibl",
            "visible",
            "smile",
            "smiling",
            "happy",
            "grin",
            "joyful",
            "delighted",
            "beaming",
        }
    ),
)


# Definition still for COLE: Nat King Cole / jazz, not fiddlers three.
COLE = HintPhoto(
    slug="cole-still",
    label="Jazz king",
    source="generated still",
    license="generated",
    filename="cole-still.webp",
    keywords=frozenset(
        {
            "cole",
            "jazz",
            "king",
            "nat",
            "musician",
            "pianist",
            "singer",
            "trio",
        }
    ),
)


# Commons alternate: imperial Ethiopian / Rastafari Lion of Judah flag.
LION = HintPhoto(
    slug="lion-of-judah",
    label="Lion of Judah",
    source="Oren neu dag",
    license="public domain",
    filename="lion-of-judah.webp",
    keywords=frozenset({"lion", "judah", "ethiopia", "ethiopian", "flag", "imperial"}),
    commons_file="Flag of Ethiopia (1897–1974).svg",
)

PHOTOS: dict[str, HintPhoto] = {
    TRANCE.slug: TRANCE,
    MOONLIT.slug: MOONLIT,
    RASTA.slug: RASTA,
    FATS.slug: FATS,
    WELLINGTON.slug: WELLINGTON,
    COLE.slug: COLE,
    SMILES.slug: SMILES,
    LION.slug: LION,
    "dreamlike": TRANCE,
    "trance": TRANCE,
    "rasta": RASTA,
    "fats": FATS,
    "guardian-30115-20a": RASTA,
    "study-rasta-5": RASTA,
    "guardian-30115-1d": FATS,
    "study-fats-4": FATS,
    "guardian-30115-12a": TRANCE,
    "wellington": WELLINGTON,
    "guardian-30115-3d": WELLINGTON,
    "study-wellington-10": WELLINGTON,
    "cole": COLE,
    "guardian-30115-8d": COLE,
    "study-cole-4": COLE,
    "smiles": SMILES,
    "guardian-30115-2d": SMILES,
    "study-smiles-6": SMILES,
}

DEFAULT_HINT = TRANCE


def _catalog() -> tuple[HintPhoto, ...]:
    return (TRANCE, MOONLIT, RASTA, FATS, WELLINGTON, COLE, SMILES, LION)


def _tokens(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    kept = {w for w in words if w not in _STOP and len(w) > 2}
    stems = set(kept)
    for word in kept:
        for suffix in ("ing", "ed", "es", "like", "y", "s"):
            root = word[: -len(suffix)] if word.endswith(suffix) else ""
            if root and len(root) >= 4:
                stems.add(root)
    return frozenset(stems)


def _closeness(needles: frozenset[str], keywords: frozenset[str]) -> float:
    if not needles:
        return 0.0
    return len(needles & keywords) / len(needles)


def match_hint(definition: str, answer: str | None = None) -> MatchedHint:
    """Pick a still from the definition text. 80% close is enough; never refuse AI."""
    del answer  # Hint the definition, not the light — do not leak the answer.
    needles = _tokens(definition)
    best = DEFAULT_HINT
    score = _closeness(needles, best.keywords)
    for photo in _catalog():
        closeness = _closeness(needles, photo.keywords)
        if closeness > score:
            best, score = photo, closeness
    return MatchedHint(photo=best, closeness=score, close_enough=score >= CLOSE_ENOUGH)


def get_hint_photo(slug: str | None = None) -> HintPhoto:
    """Resolve a still by slug. Unknown slugs auto-match. AI stills are allowed."""
    if slug in PHOTOS:
        return PHOTOS[slug]
    if not slug:
        return DEFAULT_HINT
    return match_hint(slug).photo


def hint_for_clue(clue: Clue) -> HintPhoto:
    if clue.hint_image:
        found = PHOTOS.get(clue.hint_image)
        if found is not None:
            return found
        name = Path(clue.hint_image).name
        for photo in _catalog():
            if photo.filename == name or photo.slug == clue.hint_image:
                return photo
    return match_hint(clue.definition or "").photo


def attach_hint(clue: Clue) -> Clue:
    """Study helper: carry hint_image + hint_line matched to the definition (~80%)."""
    matched = match_hint(clue.definition or "")
    photo = matched.photo
    updates: dict[str, str] = {}
    if not clue.hint_image:
        updates["hint_image"] = f"assets/hints/{photo.filename}"
    if not clue.hint_credit:
        updates["hint_credit"] = photo.credit_line
    if not clue.hint_line:
        updates["hint_line"] = HINT_LINE
    return clue.model_copy(update=updates) if updates else clue


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "image/*, application/json"}


def _fetch_commons(photo: HintPhoto, dest: Path) -> bool:
    if not photo.commons_file:
        return False
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


def _generate_trance_still(dest: Path) -> Path:
    """Last-resort dreamy still if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (36, 40, 52))
    draw = ImageDraw.Draw(img)
    draw.ellipse((280, 80, 1080, 780), fill=(232, 226, 214))
    draw.ellipse((520, 160, 900, 620), fill=(198, 188, 176))
    draw.ellipse((620, 250, 700, 320), fill=(48, 44, 42))
    draw.ellipse((780, 250, 860, 320), fill=(48, 44, 42))
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_rasta_still(dest: Path) -> Path:
    """Last-resort Rastafari colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (16, 92, 45))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1280, 240), fill=(16, 120, 52))
    draw.rectangle((0, 240, 1280, 480), fill=(232, 196, 48))
    draw.rectangle((0, 480, 1280, 720), fill=(184, 28, 41))
    draw.ellipse((490, 190, 790, 530), fill=(168, 112, 48))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_fats_still(dest: Path) -> Path:
    """Last-resort greasy-food colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (168, 96, 32))
    draw = ImageDraw.Draw(img)
    draw.ellipse((180, 80, 620, 520), fill=(232, 176, 64))
    draw.ellipse((520, 220, 1100, 700), fill=(120, 56, 24))
    draw.ellipse((700, 40, 1180, 400), fill=(212, 148, 48))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_wellington_still(dest: Path) -> Path:
    """Last-resort ducal colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (28, 24, 22))
    draw = ImageDraw.Draw(img)
    draw.ellipse((420, 60, 860, 560), fill=(176, 48, 40))
    draw.ellipse((520, 140, 760, 420), fill=(196, 156, 120))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_smiles_still(dest: Path) -> Path:
    """Last-resort pleased-face colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (236, 214, 188))
    draw = ImageDraw.Draw(img)
    draw.ellipse((420, 40, 860, 620), fill=(232, 196, 160))
    draw.ellipse((520, 220, 600, 300), fill=(48, 36, 32))
    draw.ellipse((680, 220, 760, 300), fill=(48, 36, 32))
    draw.arc((500, 280, 780, 520), start=20, end=160, fill=(140, 64, 56), width=18)
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_cole_still(dest: Path) -> Path:
    """Last-resort jazz-club colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (24, 16, 12))
    draw = ImageDraw.Draw(img)
    draw.ellipse((380, 80, 980, 680), fill=(196, 140, 64))
    draw.rectangle((200, 480, 1080, 640), fill=(48, 32, 24))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def ensure_hint_photo(photo: HintPhoto | None = None) -> Path:
    resolved = photo or DEFAULT_HINT
    dest = resolved.path
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    if _fetch_commons(resolved, dest):
        return dest
    if resolved.slug in {RASTA.slug, LION.slug, "rasta"}:
        return _generate_rasta_still(dest)
    if resolved.slug in {FATS.slug, "fats"}:
        return _generate_fats_still(dest)
    if resolved.slug in {WELLINGTON.slug, "wellington"}:
        return _generate_wellington_still(dest)
    if resolved.slug in {COLE.slug, "cole"}:
        return _generate_cole_still(dest)
    if resolved.slug in {SMILES.slug, "smiles"}:
        return _generate_smiles_still(dest)
    return _generate_trance_still(dest)
