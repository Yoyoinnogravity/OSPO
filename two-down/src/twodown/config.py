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
CREDIT_WHO = "the setter, the paper, Fifteen Squared, and the photograph"
# The only crossword source. Do not add other blogs.
SOURCE_SITE = "https://fifteensquared.net/"
SOURCE_HOST = "fifteensquared.net"
USER_AGENT = f"{BRAND}/0.1 (+{SITE_ORIGIN}/; source=https://fifteensquared.net/)"
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
THINK_RATE = "+2%"
THINK_PITCH = "+1Hz"
HINT_RATE = "+2%"
HINT_PITCH = "+3Hz"
HINT_VOLUME = "+7%"
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
# After Ryan, stay on the dictionary so the glass can be read.
INTRO_GAP_SECONDS = 6.5
# After the sting, sit on the open book before he speaks.
INTRO_LOOK_BEFORE_SECONDS = 2.4
OUTRO_LINE = "Thanks for thinking with cryptic.fit."
OUTRO_GAP_SECONDS = 0.4
# Same two chords at both ends, on an up-beat: a short C pickup into F.
# They sit before Ryan and after the thank-you, so they name the brand
# without talking over the introduction.
BRAND_STING_SECONDS = 1.45
# Footer credit is not Sonia. Thomas (male) names the setter, paper, and Fifteen Squared.
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
# Ryan offers a clue, then points at the picture. Then we wait for the answer.
HINT_OFFER = "If you need a clue."
HINT_LOOK = "Have a look at this."
HINT_LINE = f"{HINT_OFFER} {HINT_LOOK}"
# When the still is not ~80% close, skip the picture rather than force a weak match.
NO_PICTURE_LINE = "No picture clue today."
HINT_VOICE_ALIAS = "ryan"
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
# YouTube lockup: yellow letters on a red highlighter.
YELLOW = (255, 214, 0)
HIGHLIGHT = (196, 16, 36)
# First Cryptic Fit Short on the channel is #287. Earlier pair films were early cuts.
THUMBNAIL_ISSUE_START = 287
THUMBNAIL_ISSUE_FIRST_SLUG = "guardian-30112-1a"

FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_DISPLAY = "/usr/share/fonts/opentype/cantarell/Cantarell-ExtraBold.otf"

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
