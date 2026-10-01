from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter

from twodown.config import HINT_LINE, HINT_MISS, PACKAGE_ROOT, USER_AGENT
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
# Surface gender words are not a definition. They must never pick TRANCE / sleep.
_GENDER = frozenset(
    {
        "female",
        "male",
        "woman",
        "women",
        "lady",
        "ladies",
        "girl",
        "girls",
        "man",
        "men",
        "she",
        "her",
        "hers",
        "him",
        "his",
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
    photo: HintPhoto | None
    closeness: float
    close_enough: bool

    @property
    def slug(self) -> str:
        return self.photo.slug if self.photo else ""

    @property
    def line(self) -> str:
        if self.close_enough and self.photo is not None:
            return HINT_LINE
        return HINT_MISS


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



# Definition still for ELICIT: bring out / draw forth.
# Generated still (AI matching allowed). Never print ELICIT.
BRING = HintPhoto(
    slug="bring-still",
    label="Bring out",
    source="generated still",
    license="generated",
    filename="bring-still.webp",
    keywords=frozenset({"bring", "out", "draw", "extract", "evoke", "obtain", "educe"}),
)


# Definition still for CHICAGO: a place in the USA. Generic skyline. Never print CHICAGO.
USA = HintPhoto(
    slug="usa-still",
    label="A place in the USA",
    source="generated still",
    license="generated",
    filename="usa-still.webp",
    keywords=frozenset({"place", "usa", "city", "america", "american", "states"}),
)


# Definition still for PIN-UP: a model, not pup / in.
MODEL = HintPhoto(
    slug="model-still",
    label="A model",
    source="generated still",
    license="generated",
    filename="model-still.webp",
    keywords=frozenset({"model", "models", "pose", "glamour", "portrait"}),
)


# Definition still for SELF: this author / Will, not sell / fiction.
AUTHOR = HintPhoto(
    slug="author-still",
    label="This author",
    source="generated still",
    license="generated",
    filename="author-still.webp",
    keywords=frozenset({"will", "author", "writer", "novelist", "book"}),
)


# Definition still for MASCARA: make-up, not old ladies / artist.
MAKEUP = HintPhoto(
    slug="makeup-still",
    label="Make-up",
    source="generated still",
    license="generated",
    filename="makeup-still.webp",
    keywords=frozenset({"makeup", "make", "cosmetic", "cosmetics", "paint"}),
)


# Definition still for SMASH-UP: a car crash, not sabbath / remix.
CRASH = HintPhoto(
    slug="crash-still",
    label="A car crash",
    source="generated still",
    license="generated",
    filename="crash-still.webp",
    keywords=frozenset({"car", "crash", "smash", "wreck", "collision"}),
)


# Definition still for CAPSULE: space unit / life-supporting. Never print CAPSULE.
CAPSULE = HintPhoto(
    slug="capsule-still",
    label="Space unit",
    source="generated still",
    license="generated",
    filename="capsule-still.webp",
    keywords=frozenset({"space", "unit", "life", "supporting", "craft"}),
)


# A grassy field. That is not the definition of SPHERE (globe / orb / ball).
# Do not map SPHERE or "female" here. The catalog has no globe still.
FIELD = HintPhoto(
    slug="field-still",
    label="A field",
    source="generated still",
    license="generated",
    filename="field-still.webp",
    keywords=frozenset({"field", "fields", "meadow", "pasture", "grassland"}),
)


# Definition still for THE SPECTATOR: a weekly, not the title.
WEEKLY = HintPhoto(
    slug="weekly-still",
    label="A weekly",
    source="generated still",
    license="generated",
    filename="weekly-still.webp",
    keywords=frozenset({"weekly", "magazine", "periodical", "journal"}),
)


# Definition still for FUMING: cross / angry, not a Manchu dynasty.
CROSS = HintPhoto(
    slug="cross-still",
    label="Cross",
    source="generated still",
    license="generated",
    filename="cross-still.webp",
    keywords=frozenset({"cross", "angry", "anger", "annoyed", "ire"}),
)


# Definition still for UPROOTS: pulls out completely.
UPROOT = HintPhoto(
    slug="uproot-still",
    label="Pulls out completely",
    source="generated still",
    license="generated",
    filename="uproot-still.webp",
    keywords=frozenset({"pull", "pulls", "completely", "uproot", "remove"}),
)


# Definition still for EXTREMITIES: ties and tails (hands and feet).
TIPS = HintPhoto(
    slug="tips-still",
    label="Ties and tails",
    source="generated still",
    license="generated",
    filename="tips-still.webp",
    keywords=frozenset({"ties", "tails", "hands", "feet", "ends"}),
)


# Definition still for BELLHOP: hotel worker, not guts / work.
PORTER = HintPhoto(
    slug="porter-still",
    label="Hotel worker",
    source="generated still",
    license="generated",
    filename="porter-still.webp",
    keywords=frozenset({"hotel", "worker", "porter", "bell", "page"}),
)


# Definition still for AXES: X, Y and Z. Never print AXES.
XYZ = HintPhoto(
    slug="xyz-still",
    label="X, Y and Z",
    source="generated still",
    license="generated",
    filename="xyz-still.webp",
    keywords=frozenset({"x", "y", "z"}),
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
    BRING.slug: BRING,
    USA.slug: USA,
    MODEL.slug: MODEL,
    AUTHOR.slug: AUTHOR,
    MAKEUP.slug: MAKEUP,
    CRASH.slug: CRASH,
    CAPSULE.slug: CAPSULE,
    FIELD.slug: FIELD,
    WEEKLY.slug: WEEKLY,
    CROSS.slug: CROSS,
    UPROOT.slug: UPROOT,
    TIPS.slug: TIPS,
    PORTER.slug: PORTER,
    XYZ.slug: XYZ,
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
    "bring": BRING,
    "elicit": BRING,
    "guardian-30124-9a": BRING,
    "usa": USA,
    "chicago": USA,
    "independent-12473-1a": USA,
    "model": MODEL,
    "pin-up": MODEL,
    "pinup": MODEL,
    "independent-12462-6a": MODEL,
    "author": AUTHOR,
    "self": AUTHOR,
    "guardian-30113-9a": AUTHOR,
    "makeup": MAKEUP,
    "mascara": MAKEUP,
    "guardian-30112-1a": MAKEUP,
    "crash": CRASH,
    "smash-up": CRASH,
    "guardian-30112-5a": CRASH,
    "capsule": CAPSULE,
    "financial-times-18478-1a": CAPSULE,
    "field": FIELD,
    "weekly": WEEKLY,
    "spectator": WEEKLY,
    "independent-on-sunday-1907-1a": WEEKLY,
    "cross": CROSS,
    "fuming": CROSS,
    "independent-on-sunday-1907-9a": CROSS,
    "uproot": UPROOT,
    "uproots": UPROOT,
    "independent-12459-8a": UPROOT,
    "tips": TIPS,
    "extremities": TIPS,
    "independent-12459-12a": TIPS,
    "porter": PORTER,
    "bellhop": PORTER,
    "independent-12458-11a": PORTER,
    "xyz": XYZ,
    "axes": XYZ,
    "financial-times-18477-14a": XYZ,
}

# No leftover still. Trance / the sleeping woman is only for trance or dream clues.
# Unknown text and the word "female" must not fall back to TRANCE.
DEFAULT_HINT = None



def _catalog() -> tuple[HintPhoto, ...]:
    return (
        TRANCE, MOONLIT, RASTA, FATS, WELLINGTON, COLE, SMILES, DAVIS, AIM, PAPERS,
        BRING, USA, MODEL, AUTHOR, MAKEUP, CRASH, CAPSULE, FIELD, WEEKLY, CROSS,
        UPROOT, TIPS, PORTER, XYZ, LION,
    )


def _tokens(text: str) -> frozenset[str]:
    raw = (text or "").lower()
    words = re.findall(r"[a-z]+", raw)
    kept = {
        w
        for w in words
        if w not in _STOP and w not in _GENDER and (len(w) > 2 or w in {"x", "y", "z"})
    }
    for compound in re.findall(r"[a-z]+-[a-z]+", raw):
        kept.add(compound.replace("-", ""))
    stems = set(kept)
    for word in kept:
        for suffix in ("ing", "ed", "es", "like", "y", "s"):
            root = word[: -len(suffix)] if word.endswith(suffix) else ""
            if root and len(root) >= 4:
                stems.add(root)
    return frozenset(stems)


def _edge_phrases(text: str) -> tuple[str, ...]:
    """First and last few words — the usual home of a cryptic definition."""
    words = re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", text or "")
    if not words:
        return ()
    phrases = [text]
    for n in range(1, 5):
        if len(words) >= n:
            phrases.append(" ".join(words[:n]))
            phrases.append(" ".join(words[-n:]))
    return tuple(phrases)


def hint_texts(definition: str, clue: str = "", parse: str = "") -> tuple[str, ...]:
    """Definition first. Never the printed answer.

    Score the whole clue or parse only as a block. A leftover surface word
    such as "field" is wordplay or the wrong sense, not an 80% still.
    """
    texts: list[str] = []
    if definition:
        texts.extend(_edge_phrases(definition))
    for block in (clue, parse):
        if block:
            texts.append(block)
    seen: list[str] = []
    for text in texts:
        if text and text not in seen:
            seen.append(text)
    return tuple(seen)


def _closeness(needles: frozenset[str], keywords: frozenset[str]) -> float:
    if not needles:
        return 0.0
    return len(needles & keywords) / len(needles)


def match_hint(
    definition: str,
    answer: str | None = None,
    clue: str = "",
    parse: str = "",
) -> MatchedHint:
    """Pick a still from the definition. 80% close is enough; never refuse AI.

    A miss is honest: close_enough is False and photo is None.
    Never fall back to TRANCE / the sleeping woman. Gender words are ignored.
    Do not treat a leftover surface word as the definition of the answer.
    """
    del answer  # Hint the definition, not the light — do not leak the answer.
    best: HintPhoto | None = None
    score = 0.0
    for text in hint_texts(definition, clue, parse):
        needles = _tokens(text)
        if not needles:
            continue
        for photo in _catalog():
            if photo.slug == TRANCE.slug and not (needles & photo.keywords):
                continue
            closeness = _closeness(needles, photo.keywords)
            if closeness > score:
                best, score = photo, closeness
    close_enough = bool(best is not None and score >= CLOSE_ENOUGH)
    if not close_enough:
        return MatchedHint(photo=None, closeness=score, close_enough=False)
    return MatchedHint(photo=best, closeness=score, close_enough=True)


def get_hint_photo(slug: str | None = None) -> HintPhoto | None:
    """Resolve a still by slug. Unknown slugs auto-match when close enough."""
    if slug in PHOTOS:
        return PHOTOS[slug]
    if not slug:
        return None
    matched = match_hint(slug)
    return matched.photo if matched.close_enough else PHOTOS.get(slug)


def _photo_from_path(name: str) -> HintPhoto | None:
    found = PHOTOS.get(name)
    if found is not None:
        return found
    stem = Path(name).name
    for photo in _catalog():
        if photo.filename == stem or photo.slug == name:
            return photo
    return None


def _matched_photo(clue: Clue) -> HintPhoto | None:
    """80% definition match, else a slug-mapped still. Never the leftover default.

    A slug map is not a green-field stand-in for SPHERE, and never TRANCE
    unless the definition itself is trance / dream.
    """
    matched = match_hint(clue.definition or "", clue=clue.clue, parse=clue.parse)
    if matched.close_enough:
        return matched.photo
    mapped = PHOTOS.get(clue.slug)
    if mapped is None:
        return None
    if mapped.slug == TRANCE.slug:
        rematch = match_hint(clue.definition or "", clue=clue.clue, parse=clue.parse)
        if rematch.close_enough and rematch.photo is not None and rematch.photo.slug == TRANCE.slug:
            return mapped
        return None
    if mapped.slug == FIELD.slug:
        field = match_hint(clue.definition or "")
        if field.close_enough and field.photo is not None and field.photo.slug == FIELD.slug:
            return mapped
        return None
    return mapped


def hint_for_clue(clue: Clue) -> HintPhoto | None:
    """Return a per-clue still, or None when nothing relevant matches."""
    attached = attach_hint(clue)
    if attached.hint_line == HINT_MISS or not attached.hint_image:
        return None
    if attached.hint_image:
        found = _photo_from_path(attached.hint_image)
        if found is None:
            return _matched_photo(attached)
        if found.slug == TRANCE.slug:
            rematch = match_hint(attached.definition or "", clue=attached.clue, parse=attached.parse)
            if rematch.close_enough and rematch.photo is not None and rematch.photo.slug == TRANCE.slug:
                return found
            return _matched_photo(attached)
        return found
    return _matched_photo(attached)


def spoken_hint(clue: Clue) -> str:
    """Speak the offer when a still is attached, otherwise the miss line."""
    return HINT_LINE if hint_for_clue(clue) is not None else HINT_MISS


def attach_hint(clue: Clue) -> Clue:
    """Attach a distinct still, or clear the photo and say no relevant image."""
    photo = _matched_photo(clue)
    if photo is None:
        wanted = {"hint_image": None, "hint_credit": None, "hint_line": HINT_MISS}
        if clue.hint_image is None and clue.hint_credit is None and clue.hint_line == HINT_MISS:
            return clue
        return clue.model_copy(update=wanted)
    wanted = {
        "hint_image": f"assets/hints/{photo.filename}",
        "hint_credit": photo.credit_line,
        "hint_line": HINT_LINE,
    }
    if (
        clue.hint_image == wanted["hint_image"]
        and clue.hint_credit == wanted["hint_credit"]
        and clue.hint_line == wanted["hint_line"]
    ):
        return clue
    return clue.model_copy(update=wanted)


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



def _generate_bring_still(dest: Path) -> Path:
    """Last-resort draw-forth still if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (28, 22, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle((80, 160, 620, 600), fill=(48, 36, 28))
    draw.polygon([(520, 240), (1120, 160), (1180, 400), (560, 520)], fill=(232, 168, 48))
    draw.polygon([(700, 280), (1040, 220), (1080, 360), (740, 420)], fill=(252, 220, 140))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_usa_still(dest: Path) -> Path:
    """Last-resort US-city still if the file is missing. No answer text."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (28, 56, 112))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1280, 280), fill=(184, 28, 41))
    draw.rectangle((0, 480, 1280, 720), fill=(236, 236, 240))
    for left, top, right, bottom in (
        (80, 300, 200, 520),
        (220, 240, 360, 520),
        (380, 180, 520, 520),
        (540, 220, 700, 520),
        (720, 160, 880, 520),
        (900, 260, 1040, 520),
        (1060, 200, 1200, 520),
    ):
        draw.rectangle((left, top, right, bottom), fill=(20, 28, 48))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_model_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (64, 40, 48))
    draw = ImageDraw.Draw(img)
    draw.ellipse((460, 40, 820, 500), fill=(232, 196, 176))
    draw.rectangle((520, 420, 760, 700), fill=(40, 24, 28))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_author_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (52, 40, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle((280, 80, 1000, 640), fill=(243, 234, 214))
    draw.rectangle((340, 140, 940, 180), fill=(26, 21, 16))
    draw.rectangle((340, 220, 860, 248), fill=(92, 78, 64))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_makeup_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (248, 228, 220))
    draw = ImageDraw.Draw(img)
    draw.ellipse((420, 80, 860, 640), fill=(232, 188, 168))
    draw.ellipse((500, 220, 600, 280), fill=(80, 40, 36))
    draw.ellipse((680, 220, 780, 280), fill=(80, 40, 36))
    draw.arc((520, 360, 760, 520), start=20, end=160, fill=(168, 32, 48), width=22)
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_crash_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (72, 76, 80))
    draw = ImageDraw.Draw(img)
    draw.polygon([(80, 420), (520, 260), (640, 420), (200, 560)], fill=(184, 28, 41))
    draw.polygon([(560, 480), (1100, 240), (1200, 400), (700, 620)], fill=(40, 44, 48))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_capsule_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (12, 16, 32))
    draw = ImageDraw.Draw(img)
    draw.ellipse((360, 80, 920, 640), fill=(188, 196, 208))
    draw.ellipse((520, 220, 760, 460), fill=(80, 140, 196))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_field_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (120, 168, 72))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1280, 260), fill=(140, 196, 232))
    draw.polygon([(0, 260), (1280, 260), (1280, 720), (0, 520)], fill=(72, 120, 40))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_weekly_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (36, 32, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle((300, 40, 980, 680), fill=(252, 247, 236))
    draw.rectangle((360, 80, 920, 200), fill=(184, 28, 41))
    draw.rectangle((360, 240, 820, 270), fill=(26, 21, 16))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_cross_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (88, 28, 28))
    draw = ImageDraw.Draw(img)
    draw.ellipse((400, 40, 880, 640), fill=(220, 96, 64))
    draw.line((500, 200, 600, 280), fill=(32, 16, 16), width=18)
    draw.line((780, 200, 680, 280), fill=(32, 16, 16), width=18)
    draw.arc((500, 380, 780, 560), start=200, end=340, fill=(32, 16, 16), width=18)
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_uproot_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (92, 64, 36))
    draw = ImageDraw.Draw(img)
    draw.ellipse((480, 80, 800, 360), fill=(48, 96, 40))
    draw.polygon([(560, 340), (720, 340), (820, 680), (460, 680)], fill=(96, 52, 24))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_tips_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (236, 220, 200))
    draw = ImageDraw.Draw(img)
    draw.ellipse((160, 160, 520, 560), fill=(216, 176, 140))
    draw.ellipse((760, 160, 1120, 560), fill=(216, 176, 140))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_porter_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (36, 40, 72))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1280, 160), fill=(184, 28, 41))
    draw.ellipse((500, 80, 780, 400), fill=(232, 196, 160))
    draw.rectangle((520, 380, 760, 680), fill=(20, 24, 48))
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def _generate_xyz_still(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), (243, 234, 214))
    draw = ImageDraw.Draw(img)
    draw.line((200, 560, 640, 200), fill=(184, 28, 41), width=18)
    draw.line((200, 560, 1080, 560), fill=(26, 21, 16), width=18)
    draw.line((200, 560, 360, 120), fill=(40, 88, 160), width=18)
    img.save(dest, "WEBP", quality=82, method=6)
    return dest


def ensure_hint_photo(photo: HintPhoto | None = None) -> Path:
    if photo is None:
        raise ValueError("no hint photo to ensure — DEFAULT is not a leftover still")
    dest = photo.path
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    if _fetch_commons(photo, dest):
        return dest
    generators = {
        TRANCE.slug: _generate_trance_still,
        RASTA.slug: _generate_rasta_still,
        LION.slug: _generate_rasta_still,
        FATS.slug: _generate_fats_still,
        WELLINGTON.slug: _generate_wellington_still,
        COLE.slug: _generate_cole_still,
        SMILES.slug: _generate_smiles_still,
        DAVIS.slug: _generate_davis_still,
        AIM.slug: _generate_aim_still,
        PAPERS.slug: _generate_papers_still,
        BRING.slug: _generate_bring_still,
        USA.slug: _generate_usa_still,
        MODEL.slug: _generate_model_still,
        AUTHOR.slug: _generate_author_still,
        MAKEUP.slug: _generate_makeup_still,
        CRASH.slug: _generate_crash_still,
        CAPSULE.slug: _generate_capsule_still,
        FIELD.slug: _generate_field_still,
        WEEKLY.slug: _generate_weekly_still,
        CROSS.slug: _generate_cross_still,
        UPROOT.slug: _generate_uproot_still,
        TIPS.slug: _generate_tips_still,
        PORTER.slug: _generate_porter_still,
        XYZ.slug: _generate_xyz_still,
    }
    generate = generators.get(photo.slug)
    if generate is not None:
        return generate(dest)
    raise FileNotFoundError(f"missing hint still {photo.slug}")
