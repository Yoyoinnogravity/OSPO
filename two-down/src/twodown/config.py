from pathlib import Path
import os

BRAND = "cryptic.fun"
SITE_ORIGIN = "https://cryptic.fun"
SUGGEST_EMAIL = "aledmorgan@gmail.com"
SPONSOR_EMAIL = SUGGEST_EMAIL
# Product line. We pick clues; we do not write the paper clues.
BRAND_PROMISE = "unique cryptic crossword clues and solutions"
BRAND_LINE = f"We provide {BRAND_PROMISE}."
CREDIT_LINE = "We credit all."
CREDIT_WHO = "the setter, the paper, Fifteen Squared, and the photograph"
# The only crossword source. Do not add other blogs.
SOURCE_SITE = "https://fifteensquared.net/"
SOURCE_HOST = "fifteensquared.net"
USER_AGENT = "cryptic.fun/0.1 (+https://cryptic.fun; source=https://fifteensquared.net/)"
WP_POSTS = f"{SOURCE_SITE.rstrip('/')}/wp-json/wp/v2/posts"
CRAWL_GAP_SECONDS = 1.0

DAILY_CATEGORY_SLUGS = frozenset({"independent", "ft", "guardian"})

# Sonia is the solver: warmer, more empathy. Libby stays as the clearer optional read.
DEFAULT_VOICE_ALIAS = "sonia"
VOICES = {
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    "ryan": "en-GB-RyanNeural",
    "thomas": "en-GB-ThomasNeural",
}
VOICE_LABELS = {
    "sonia": "Sonia",
    "libby": "Libby",
    "ryan": "Ryan",
    "thomas": "Thomas",
}
# Spoken like people, not a card reader. A bit slower than stock TTS.
VOICE_RATE = "-10%"
VOICE_PITCH = "+0Hz"
VOICE_VOLUME = "+5%"
CLUE_RATE = "-12%"
CLUE_PITCH = "-1Hz"
LETTERS_RATE = "-8%"
LETTERS_PITCH = "+0Hz"
THINK_RATE = "-8%"
THINK_PITCH = "+1Hz"
HINT_RATE = "-6%"
HINT_PITCH = "+0Hz"
ANSWER_RATE = "-2%"
ANSWER_PITCH = "+1Hz"
# Parse is the same woman, unhurried, with space around the asides.
PARSE_RATE = "-8%"
PARSE_PITCH = "+0Hz"
PARSE_ASIDE_PAUSE_SECONDS = 0.7
INTRO_LINE = "Right — here's your daily dose of cryptic fun."
INTRO_VOICE_ALIAS = "ryan"
INTRO_RATE = "+3%"
INTRO_PITCH = "+4Hz"
INTRO_VOLUME = "+8%"
INTRO_GAP_SECONDS = 0.45
OUTRO_LINE = "Thanks for thinking with cryptic.fun."
OUTRO_GAP_SECONDS = 0.4
# Source credit is not Sonia — Thomas reads the paper and Fifteen Squared.
SOURCE_VOICE_ALIAS = "thomas"
SOURCE_RATE = "-4%"
SOURCE_PITCH = "+0Hz"
SOURCE_VOLUME = "+4%"
SOURCE_GAP_SECONDS = 0.35
THINK_PAUSE_SECONDS = 7.0
CLUE_LETTERS_GAP_SECONDS = 0.35
LETTERS_PAUSE_SECONDS = 1.0
ANSWER_PAUSE_SECONDS = 1.2
THINK_PROMPT = "Just pause here, and have a think."
# Linear picture hint after the main think pause. Shorts cannot click mid-film.
HINT_LINE = "Have a look at this."
HINT_HOLD_SECONDS = 4.0
HINT_PAUSE_SECONDS = 2.5
CLUES_PER_DAY = 2
# Lock the spoken beat on this constructed study clue before touching the others.
# AIMLESSLY is Guardian 30115 9 across; twodown short rebuilds this clue only.
STUDY_SLUG = "guardian-30115-9a"
PINUP_SLUG = "independent-12462-6a"

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PACKAGE_ROOT / "output"
SITE_ROOT = PACKAGE_ROOT / "site"

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

# Public follow URLs. YouTube has a default handle; the others stay off until set.
YOUTUBE_FOLLOW = os.environ.get("TWODOWN_YOUTUBE_URL", "https://www.youtube.com/@crypticfun").strip()
TIKTOK_FOLLOW = os.environ.get("TWODOWN_TIKTOK_URL", "").strip()
INSTAGRAM_FOLLOW = os.environ.get("TWODOWN_INSTAGRAM_URL", "").strip()
FACEBOOK_FOLLOW = os.environ.get("TWODOWN_FACEBOOK_URL", "").strip()


def follow_profiles() -> list[tuple[str, str, str]]:
    """External cryptic.fun profiles: slug, label, url. Empty env values are omitted."""
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
