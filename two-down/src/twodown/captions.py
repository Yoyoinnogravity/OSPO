from __future__ import annotations

from twodown.config import BRAND, BRAND_PROMISE, SITE_ORIGIN
from twodown.models import Clue, SpokenClue
from twodown.scenes import get_scene

HASHTAGS = "#crypticcrossword #crypticfun #crossword #shorts"
SOCIAL_HANDLE = "Cryptic Fun"


def clue_line(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    return f"{clue.clue}{enum}"


def social_caption(item: SpokenClue, *, spoil: bool = False) -> str:
    """On-video social caption. The answer stays in the film unless spoil=True."""
    clue = item.clue
    page = item.site_path or SITE_ORIGIN
    lines = [
        f"{SOCIAL_HANDLE} · {clue_line(clue)}",
        "",
        "Have a think. The parse is in the video.",
    ]
    if spoil:
        lines.append(f"Answer: {clue.answer}")
    lines.extend(
        [
            f"{clue.paper} {clue.puzzle_id} by {clue.setter}.",
            f"{page}",
            HASHTAGS,
        ]
    )
    return "\n".join(lines)


def facebook_title(clue: Clue) -> str:
    title = f"{SOCIAL_HANDLE} · {clue_line(clue)}"
    return title if len(title) <= 255 else title[:254].rstrip() + "…"


def youtube_description(item: SpokenClue) -> str:
    clue = item.clue
    page = item.site_path or SITE_ORIGIN
    return (
        f"{SOCIAL_HANDLE} — {BRAND_PROMISE}.\n"
        f"{BRAND}\n\n"
        f"{clue_line(clue)}\n"
        f"Answer: {clue.answer}\n\n"
        f"{page}\n"
        f"Support: {SITE_ORIGIN}/support.html\n"
        f"Parse: {clue.source_url}\n"
        f"{clue.paper} {clue.puzzle_id} by {clue.setter}. "
        f"Blogged by {clue.blogger} on Fifteen Squared.\n"
        f"{get_scene(item.scene).youtube_credit}\n"
    )
