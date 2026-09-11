from pathlib import Path

BRAND = "cryptic.fun"
SITE_ORIGIN = "https://cryptic.fun"
USER_AGENT = "cryptic.fun/0.1 (+https://cryptic.fun)"
WP_POSTS = "https://fifteensquared.net/wp-json/wp/v2/posts"
CRAWL_GAP_SECONDS = 1.0

DAILY_CATEGORY_SLUGS = frozenset({"independent", "ft", "guardian"})

# Sonia: clear southern British, slightly slow for letter-play.
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
