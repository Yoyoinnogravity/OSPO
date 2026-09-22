from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter

from twodown.config import HINT_LINE, NO_PICTURE_LINE, PACKAGE_ROOT, USER_AGENT
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
        "this",
        "that",
        "these",
        "those",
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
        return HINT_LINE if self.close_enough else NO_PICTURE_LINE


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


# Definition still for MASS MEDIA: newspapers / the press.
# Not maid, not mess. Never print MASS MEDIA.
PAPERS = HintPhoto(
    slug="papers-still",
    label="Newspapers",
    source="generated still",
    license="generated",
    filename="papers-still.webp",
    keywords=frozenset(
        {
            "newspaper",
            "newspapers",
            "newspap",
            "paper",
            "papers",
            "press",
            "pres",
            "news",
            "media",
        }
    ),
)


# Definition still for AIMLESSLY: end as a goal or aim.
# Not sly, not e-mails, not recycle. Never print AIMLESSLY.
AIM = HintPhoto(
    slug="aim-still",
    label="A goal",
    source="generated still",
    license="generated",
    filename="aim-still.webp",
    keywords=frozenset(
        {
            "end",
            "ends",
            "ending",
            "goal",
            "goals",
            "aim",
            "aims",
            "target",
            "purpose",
            "bullseye",
        }
    ),
)


# Definition still for DAVIS CUP: tennis court / international court event.
# Not divas, not cricket, not UP. Never print DAVIS CUP.
DAVIS = HintPhoto(
    slug="davis-cup-still",
    label="Tennis courts",
    source="generated still",
    license="generated",
    filename="davis-cup-still.webp",
    keywords=frozenset(
        {
            "international",
            "internation",
            "court",
            "courts",
            "event",
            "tennis",
            "lawn",
            "match",
            "sport",
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


# Daily pair films. Hint the definition, never print the answer.
MAKEUP = HintPhoto(
    slug="makeup-still",
    label="Make-up",
    source="generated still",
    license="generated",
    filename="makeup-still.webp",
    keywords=frozenset({"make", "makeup", "cosmetic", "cosmetics", "lipstick", "powder"}),
)

CRASH = HintPhoto(
    slug="crash-still",
    label="A car crash",
    source="generated still",
    license="generated",
    filename="crash-still.webp",
    keywords=frozenset({"car", "crash", "wreck", "collision", "accident"}),
)

PHOTO = HintPhoto(
    slug="photo-still",
    label="A photograph",
    source="generated still",
    license="generated",
    filename="photo-still.webp",
    keywords=frozenset({"photo", "photos", "photograph", "attractive", "person", "appearing", "model", "portrait"}),
)

AUTHOR = HintPhoto(
    slug="author-still",
    label="The author",
    source="generated still",
    license="generated",
    filename="author-still.webp",
    keywords=frozenset({"author", "writer", "novelist", "book"}),
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
    DAVIS.slug: DAVIS,
    AIM.slug: AIM,
    PAPERS.slug: PAPERS,
    MAKEUP.slug: MAKEUP,
    CRASH.slug: CRASH,
    PHOTO.slug: PHOTO,
    AUTHOR.slug: AUTHOR,
    LION.slug: LION,
    "makeup": MAKEUP,
    "make-up": MAKEUP,
    "guardian-30112-1a": MAKEUP,
    "crash": CRASH,
    "car-crash": CRASH,
    "guardian-30112-5a": CRASH,
    "photo": PHOTO,
    "photograph": PHOTO,
    "independent-12462-6a": PHOTO,
    "author": AUTHOR,
    "guardian-30113-9a": AUTHOR,
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
    "davis": DAVIS,
    "davis-cup": DAVIS,
    "guardian-30115-18d": DAVIS,
    "study-davis-cup-5-3": DAVIS,
    "aim": AIM,
    "aimlessly": AIM,
    "guardian-30115-9a": AIM,
    "study-aimlessly-9": AIM,
    "papers": PAPERS,
    "newspapers": PAPERS,
    "mass-media": PAPERS,
    "mass media": PAPERS,
    "financial-times-18483-1a": PAPERS,
    "study-mass-media-4-5": PAPERS,
}

DEFAULT_HINT = TRANCE


def _catalog() -> tuple[HintPhoto, ...]:
    return (
        TRANCE,
        MOONLIT,
        RASTA,
        FATS,
        WELLINGTON,
        COLE,
        SMILES,
        DAVIS,
        AIM,
        PAPERS,
        MAKEUP,
        CRASH,
        PHOTO,
        AUTHOR,
        LION,
    )


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


def get_hint_photo(slug: str | None = None) -> HintPhoto | None:
    """Resolve a still by slug. Unknown slugs auto-match when close enough."""
    if slug in PHOTOS:
        return PHOTOS[slug]
    if not slug:
        return DEFAULT_HINT
    matched = match_hint(slug)
    return matched.photo if matched.close_enough else None


def infer_definition(clue: Clue) -> str:
    """Definition text for the picture clue. Prefer the stored gloss, then the parse."""
    if clue.definition:
        return clue.definition
    mapped = PHOTOS.get(clue.slug)
    if mapped is not None:
        return mapped.label
    parse = (clue.parse or "").replace("–", ".").replace("—", ".")
    parts = [part.strip() for part in re.split(r"[.]", parse) if part.strip()]
    if parts:
        last = parts[-1]
        if not re.search(r"\b(anagram|charade|container|reversal|homophone)\b", last, re.I):
            return last
    return clue.clue


def _photo_from_clue_fields(clue: Clue) -> HintPhoto | None:
    if clue.hint_image:
        found = PHOTOS.get(clue.hint_image)
        if found is not None:
            return found
        name = Path(clue.hint_image).name
        for photo in _catalog():
            if photo.filename == name or photo.slug == clue.hint_image:
                return photo
    if clue.slug in PHOTOS:
        return PHOTOS[clue.slug]
    return None


def hint_for_clue(clue: Clue) -> HintPhoto | None:
    """Return a still only when one is chosen. Weak matches stay off the card."""
    if (clue.hint_line or "").strip().casefold() == NO_PICTURE_LINE.strip().casefold():
        return None
    found = _photo_from_clue_fields(clue)
    if found is not None:
        return found
    matched = match_hint(infer_definition(clue))
    return matched.photo if matched.close_enough else None


def has_picture_clue(clue: Clue) -> bool:
    return hint_for_clue(clue) is not None


def attach_hint(clue: Clue) -> Clue:
    """Carry a picture clue when the still is ~80% close. Otherwise say so."""
    definition = infer_definition(clue)
    matched = match_hint(definition)
    photo = _photo_from_clue_fields(clue)
    if photo is None and matched.close_enough:
        photo = matched.photo
    updates: dict[str, str] = {}
    if not clue.definition:
        updates["definition"] = definition
    if photo is not None:
        if not clue.hint_image:
            updates["hint_image"] = f"assets/hints/{photo.filename}"
        if not clue.hint_credit:
            updates["hint_credit"] = photo.credit_line
        if not clue.hint_line:
            updates["hint_line"] = HINT_LINE
    elif not clue.hint_line:
        updates["hint_line"] = NO_PICTURE_LINE
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


def _generate_davis_still(dest: Path) -> Path:
    """Last-resort tennis-court colours if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (62, 122, 48))
    draw = ImageDraw.Draw(img)
    draw.rectangle((80, 80, 1200, 640), fill=(86, 148, 64))
    draw.rectangle((620, 80, 660, 640), fill=(248, 248, 244))
    draw.rectangle((80, 340, 1200, 380), fill=(248, 248, 244))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_aim_still(dest: Path) -> Path:
    """Last-resort target / goal if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (243, 234, 214))
    draw = ImageDraw.Draw(img)
    draw.ellipse((340, 60, 940, 660), fill=(252, 247, 236))
    draw.ellipse((400, 120, 880, 600), fill=(184, 28, 41))
    draw.ellipse((490, 210, 790, 510), fill=(252, 247, 236))
    draw.ellipse((560, 280, 720, 440), fill=(184, 28, 41))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_makeup_still(dest: Path) -> Path:
    """Last-resort compact / lipstick colours. No MASCARA text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (248, 228, 220))
    draw = ImageDraw.Draw(img)
    draw.ellipse((160, 80, 620, 540), fill=(196, 48, 72))
    draw.ellipse((210, 130, 570, 490), fill=(232, 140, 150))
    draw.rectangle((720, 120, 1120, 620), fill=(36, 28, 26))
    draw.rectangle((760, 180, 1080, 560), fill=(184, 28, 41))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_crash_still(dest: Path) -> Path:
    """Last-resort wreck colours. No SMASH-UP text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (72, 76, 80))
    draw = ImageDraw.Draw(img)
    draw.polygon([(80, 420), (420, 180), (980, 220), (1200, 480), (160, 620)], fill=(140, 36, 36))
    draw.polygon([(200, 260), (560, 140), (900, 280), (640, 400)], fill=(196, 196, 200))
    draw.ellipse((860, 360, 1180, 680), fill=(28, 28, 30))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_photo_still(dest: Path) -> Path:
    """Last-resort camera / portrait colours. No PIN-UP text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (32, 32, 34))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((180, 80, 1100, 640), radius=28, fill=(244, 236, 220))
    draw.ellipse((430, 140, 850, 560), fill=(212, 176, 140))
    draw.ellipse((520, 240, 600, 320), fill=(40, 32, 28))
    draw.ellipse((680, 240, 760, 320), fill=(40, 32, 28))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_author_still(dest: Path) -> Path:
    """Last-resort desk / book colours. No SELF text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (48, 36, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle((160, 80, 620, 640), fill=(232, 220, 196))
    draw.rectangle((220, 140, 560, 180), fill=(26, 21, 16))
    draw.rectangle((220, 210, 500, 230), fill=(26, 21, 16))
    draw.rectangle((700, 200, 1160, 640), fill=(184, 28, 41))
    draw.rectangle((760, 260, 1100, 580), fill=(243, 234, 214))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_papers_still(dest: Path) -> Path:
    """Last-resort newspaper stack if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (92, 78, 64))
    draw = ImageDraw.Draw(img)
    draw.rectangle((180, 80, 1040, 220), fill=(228, 216, 188))
    draw.rectangle((220, 200, 1100, 380), fill=(243, 234, 214))
    draw.rectangle((160, 340, 1080, 620), fill=(252, 247, 236))
    draw.rectangle((220, 400, 980, 430), fill=(26, 21, 16))
    draw.rectangle((220, 460, 860, 480), fill=(26, 21, 16))
    draw.rectangle((220, 500, 720, 516), fill=(92, 78, 64))
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
    if resolved.slug in {DAVIS.slug, "davis", "davis-cup"}:
        return _generate_davis_still(dest)
    if resolved.slug in {AIM.slug, "aim", "aimlessly"}:
        return _generate_aim_still(dest)
    if resolved.slug in {PAPERS.slug, "papers", "newspapers", "mass-media"}:
        return _generate_papers_still(dest)
    if resolved.slug in {MAKEUP.slug, "makeup", "make-up"}:
        return _generate_makeup_still(dest)
    if resolved.slug in {CRASH.slug, "crash", "car-crash"}:
        return _generate_crash_still(dest)
    if resolved.slug in {PHOTO.slug, "photo", "photograph"}:
        return _generate_photo_still(dest)
    if resolved.slug in {AUTHOR.slug, "author"}:
        return _generate_author_still(dest)
    return _generate_trance_still(dest)
