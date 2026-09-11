from pathlib import Path

USER_AGENT = "TwoDown/0.1 (+https://cryptic.fit)"
WP_POSTS = "https://fifteensquared.net/wp-json/wp/v2/posts"
CRAWL_GAP_SECONDS = 1.0

# Fifteen Squared category slugs for weekday 15x15 cryptics.
DAILY_CATEGORY_SLUGS = frozenset({"independent", "ft", "guardian"})

# Default spoken voice: Sonia is a clear southern-British neural voice.
# Slowed slightly so letter-play does not blur.
DEFAULT_VOICE_ALIAS = "sonia"
VOICES = {
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    "ryan": "en-GB-RyanNeural",
    "thomas": "en-GB-ThomasNeural",
}
VOICE_RATE = "-8%"

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PACKAGE_ROOT / "output"

CARD_BG = (14, 26, 36)
CARD_CREAM = (244, 239, 230)
CARD_GOLD = (212, 160, 23)
CARD_MUTED = (156, 170, 180)

FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
