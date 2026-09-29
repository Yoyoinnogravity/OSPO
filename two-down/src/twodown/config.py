from pathlib import Path
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

# Cryptic Croc is a grown woman: Emma’s clear American read, Friends-plain,
# with a quicker South Park snap. Maisie stays off — she sounded like a child.
# Sonia, Libby, Ryan and Thomas stay available as alternate voices.
DEFAULT_VOICE_ALIAS = "croc"
VOICES = {
    "croc": "en-US-EmmaNeural",
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    "ryan": "en-GB-RyanNeural",
    "thomas": "en-GB-ThomasNeural",
}
VOICE_LABELS = {
    "croc": "Cryptic Croc",
    "sonia": "Sonia",
    "libby": "Libby",
    "ryan": "Ryan",
    "thomas": "Thomas",
}
# Punchier than a sitcom read, still slow enough to catch every word.
VOICE_RATE = "+8%"
VOICE_PITCH = "+4Hz"
VOICE_VOLUME = "+7%"
# She presents the clue with a bit more snap.
CLUE_RATE = "+12%"
CLUE_PITCH = "+6Hz"
CLUE_VOLUME = "+8%"
LETTERS_RATE = "+4%"
LETTERS_PITCH = "+4Hz"
THINK_RATE = "+2%"
THINK_PITCH = "+0Hz"
HINT_RATE = "+10%"
HINT_PITCH = "+6Hz"
HINT_VOLUME = "+8%"
ANSWER_RATE = "+8%"
ANSWER_PITCH = "+4Hz"
# Parse stays a touch slower so the wordplay lands.
PARSE_RATE = "+0%"
PARSE_PITCH = "+2Hz"
PARSE_ASIDE_PAUSE_SECONDS = 0.7
TAGLINE = "Solve it, I know you can."
# Ryan invites, upbeat. Cryptic Croc then presents the clue.
INTRO_LINE = f"{TAGLINE} Here's Cryptic Croc."
INTRO_VOICE_ALIAS = "ryan"
INTRO_RATE = "+10%"
INTRO_PITCH = "+8Hz"
INTRO_VOLUME = "+8%"
INTRO_GAP_SECONDS = 0.45
OUTRO_LINE = "That was cryptic.fit. Try to keep up."
OUTRO_VOICE_ALIAS = "croc"
OUTRO_RATE = "+0%"
OUTRO_PITCH = "+0Hz"
OUTRO_VOLUME = "+4%"
OUTRO_GAP_SECONDS = 0.4
# She names the setter too, a little steadier than the solve.
SOURCE_VOICE_ALIAS = "croc"
SOURCE_RATE = "-2%"
SOURCE_PITCH = "+2Hz"
SOURCE_VOLUME = "+4%"
SOURCE_GAP_SECONDS = 0.35
THINK_PAUSE_SECONDS = 7.0
CLUE_LETTERS_GAP_SECONDS = 0.35
LETTERS_PAUSE_SECONDS = 1.0
ANSWER_PAUSE_SECONDS = 1.2
THINK_PROMPT = "Go on. Think. I can wait."
# Cryptic Croc offers a clue, then points at the picture.
HINT_OFFER = "Stuck already?"
HINT_LOOK = "Look at this."
HINT_LINE = f"{HINT_OFFER} {HINT_LOOK}"
HINT_VOICE_ALIAS = "croc"
HINT_HOLD_SECONDS = 4.0
HINT_PAUSE_SECONDS = 2.5
CLUES_PER_DAY = 2
# Lock the spoken beat on this constructed study clue before touching the others.
# MASS MEDIA is FT 18483 1 across; twodown short rebuilds this clue only.
STUDY_SLUG = "financial-times-18483-1a"
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

# Public follow URLs. YouTube is @crypticfit. Do not use @crypticfun.
YOUTUBE_FOLLOW = os.environ.get("TWODOWN_YOUTUBE_URL", "https://www.youtube.com/@crypticfit").strip()
TIKTOK_FOLLOW = os.environ.get("TWODOWN_TIKTOK_URL", "").strip()
INSTAGRAM_FOLLOW = os.environ.get("TWODOWN_INSTAGRAM_URL", "").strip()
FACEBOOK_FOLLOW = os.environ.get("TWODOWN_FACEBOOK_URL", "").strip()


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
