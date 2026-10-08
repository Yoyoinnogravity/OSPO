from pathlib import Path
import hashlib
import os

BRAND = "cryptic.fit"
# One name: the site Aled owns. Do not use cryptic.fun — we do not own it.
SITE_HOST = "cryptic.fit"
SITE_ORIGIN = f"https://{SITE_HOST}"
SUGGEST_EMAIL = "aledmorgan@gmail.com"
SPONSOR_EMAIL = SUGGEST_EMAIL
# Product line. We pick clues; we do not write the paper clues.
BRAND_PROMISE = "unique cryptic crossword clues and solutions"
BRAND_LINE = f"We provide {BRAND_PROMISE}."
CREDIT_LINE = "We credit all."
CREDIT_WHO = "the setter, the paper, and the photograph"
# The only crossword source. Do not add other blogs.
SOURCE_SITE = "https://fifteensquared.net/"
SOURCE_HOST = "fifteensquared.net"
USER_AGENT = f"{BRAND}/0.1 (+{SITE_ORIGIN}/; source=https://fifteensquared.net/)"
WP_POSTS = f"{SOURCE_SITE.rstrip('/')}/wp-json/wp/v2/posts"
CRAWL_GAP_SECONDS = 1.0

DAILY_CATEGORY_SLUGS = frozenset({"independent", "ft", "guardian"})

# Cryptic Croc is Ava. Andrew invites. Production pair is locked.
# Sonia, Libby, Ryan and Thomas stay available as alternate voices.
DEFAULT_VOICE_ALIAS = "croc"
VOICES = {
    "croc": "en-US-AvaNeural",
    "andrew": "en-US-AndrewNeural",
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    "ryan": "en-GB-RyanNeural",
    "thomas": "en-GB-ThomasNeural",
}
VOICE_LABELS = {
    "croc": "Cryptic Croc",
    "andrew": "Andrew",
    "sonia": "Sonia",
    "libby": "Libby",
    "ryan": "Ryan",
    "thomas": "Thomas",
}
# Conversational. No snap, no raised pitch.
VOICE_RATE = "+0%"
VOICE_PITCH = "+0Hz"
VOICE_VOLUME = "+2%"
# The clue is a little slower so it can be written down.
CLUE_RATE = "-5%"
CLUE_PITCH = "+0Hz"
CLUE_VOLUME = "+2%"
LETTERS_RATE = "-2%"
LETTERS_PITCH = "+0Hz"
THINK_RATE = "-4%"
THINK_PITCH = "+0Hz"
HINT_RATE = "+0%"
HINT_PITCH = "+0Hz"
HINT_VOLUME = "+2%"
ANSWER_RATE = "+0%"
ANSWER_PITCH = "+0Hz"
# Parse stays slower so the wordplay lands.
PARSE_RATE = "-6%"
PARSE_PITCH = "+0Hz"
PARSE_ASIDE_PAUSE_SECONDS = 0.35
TAGLINE = "Solve it, I know you can."
# Recorded open from Aled's YouTube Short 8D8XTzkgNLE (dictionary ident +
# Ryan). The bumper already invites. Do not stack Andrew's daily-dose line.
INTRO_LINE = "Hello, here is your daily dose of AI cryptic crossword."
INTRO_VOICE_ALIAS = "andrew"
INTRO_RATE = "+0%"
INTRO_PITCH = "+0Hz"
INTRO_VOLUME = "+2%"
# The bumper already holds a breath after the invite. Keep the splice tiny.
INTRO_GAP_SECONDS = 0.08
OUTRO_LINE = "That was cryptic.fit."
# Ava signs off with one of these, then the site name. Same slug, same closer.
WISDOM_LINES = (
    "A good clue hides in daylight.",
    "If it looks too obvious, read it again.",
    "The grid forgives anyone who stays with it.",
    "The setter left you a way in.",
    "Every light starts as a blank.",
    "Trust the surface, then look twice.",
    "One letter in, the rest will follow.",
)
OUTRO_VOICE_ALIAS = "croc"
OUTRO_RATE = "+0%"
OUTRO_PITCH = "+0Hz"
OUTRO_VOLUME = "+2%"
OUTRO_GAP_SECONDS = 0.3
SOURCE_VOICE_ALIAS = "croc"
SOURCE_RATE = "-4%"
SOURCE_PITCH = "+0Hz"
SOURCE_VOLUME = "+2%"
SOURCE_GAP_SECONDS = 0.25
THINK_PAUSE_SECONDS = 3.0
CLUE_LETTERS_GAP_SECONDS = 0.25
LETTERS_PAUSE_SECONDS = 0.8
ANSWER_PAUSE_SECONDS = 0.8
THINK_PROMPT = "Pause here to think about it."
HINT_OFFER = "Here's a hint."
HINT_LOOK = "Here's a hint."
HINT_LINE = "Here's a hint."
# Spoken and shown when attach_hint has no ~80% match. Do not paste a generic still.
HINT_MISS = "No relevant image found."
HINT_VOICE_ALIAS = "croc"
HINT_HOLD_SECONDS = 2.0
HINT_PAUSE_SECONDS = 0.8
# One Short a day. twodown.train rotates which source supplies it.
CLUES_PER_DAY = 1
# Lock the spoken beat on this constructed study clue before touching the others.
# MASS MEDIA is FT 18483 1 across; twodown short rebuilds this clue only.
STUDY_SLUG = "financial-times-18483-1a"
PINUP_SLUG = "independent-12462-6a"

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PACKAGE_ROOT / "output"
SITE_ROOT = PACKAGE_ROOT / "site"
# Clues Aled has already solved. Times, Telegraph, and homemade days read this.
# Empty means those slots fall through. Never invent a row here.
OWN_CLUES = PACKAGE_ROOT / "own-clues.json"
INTRO_BUMPER = PACKAGE_ROOT / "assets" / "intro" / "aled-daily-dose.mp4"

# Newsprint + crimson. Definition-red is the 15² convention made into a brand.
NEWS_BG = (243, 234, 214)
NEWS_GRID = (228, 216, 188)
INK = (26, 21, 16)
CRIMSON = (184, 28, 41)
CREAM = (252, 247, 236)
MUTED = (92, 78, 64)

FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# Public follow URLs. YouTube is @crypticfit. Do not use @crypticfun.
YOUTUBE_FOLLOW = os.environ.get("TWODOWN_YOUTUBE_URL", "https://www.youtube.com/@crypticfit").strip()
TIKTOK_FOLLOW = os.environ.get("TWODOWN_TIKTOK_URL", "").strip()
INSTAGRAM_FOLLOW = os.environ.get("TWODOWN_INSTAGRAM_URL", "").strip()
FACEBOOK_FOLLOW = os.environ.get("TWODOWN_FACEBOOK_URL", "").strip()


def pick_wisdom(slug: str, lines: tuple[str, ...] | None = None) -> str:
    """Pick one closer from the pool. Stable for a clue slug so a recut says the same line."""
    pool = lines if lines is not None else WISDOM_LINES
    if not pool:
        return ""
    digest = hashlib.sha256((slug or "").encode("utf-8")).hexdigest()
    return pool[int(digest, 16) % len(pool)]


def follow_profiles() -> list[tuple[str, str, str]]:
    """External cryptic.fit profiles: slug, label, url. Empty env values are omitted."""
    rows: list[tuple[str, str, str]] = []
    for slug, label, url in (
        ("youtube", "YouTube", YOUTUBE_FOLLOW),
        ("tiktok", "TikTok", TIKTOK_FOLLOW),
        ("instagram", "Instagram", INSTAGRAM_FOLLOW),
        ("facebook", "Facebook", FACEBOOK_FOLLOW),
    ):
        if url:
            rows.append((slug, label, url))
    return rows
