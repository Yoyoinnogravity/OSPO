from __future__ import annotations

from twodown.config import BRAND, BRAND_PROMISE, CREDIT_LINE, SITE_ORIGIN, THINK_PROMPT
from twodown.models import Clue, SpokenClue
from twodown.scenes import get_scene

HASHTAGS = "#crypticcrossword #crypticaiforfun #crypticfit #crossword #shorts"
TIKTOK_HASHTAGS = "#crypticcrossword #crypticaiforfun #crypticfit #crossword"
SOCIAL_HANDLE = BRAND


def clue_line(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    return f"{clue.clue}{enum}"


def tiktok_caption(clue: Clue, *, index: int | None = None, total: int | None = None) -> str:
    """Clue first so TikTok's preview is the puzzle, not the brand. No answer."""
    series = ""
    if index and total:
        series = f"{index}/{total} · "
    elif index:
        series = f"{index} · "
    return "\n".join(
        [
            clue_line(clue),
            "",
            THINK_PROMPT,
            "",
            f"{series}{SOCIAL_HANDLE} · {clue.paper} {clue.puzzle_id} · {clue.setter}",
            SITE_ORIGIN,
            TIKTOK_HASHTAGS,
        ]
    )


def social_caption(item: SpokenClue, *, spoil: bool = False) -> str:
    """On-video social caption. The answer stays in the film unless spoil=True."""
    clue = item.clue
    page = item.site_path or SITE_ORIGIN
    lines = [
        clue_line(clue),
        "",
        "Have a think. The parse is in the video.",
        "",
        f"{SOCIAL_HANDLE} · {clue.paper} {clue.puzzle_id} · {clue.setter}",
    ]
    if spoil:
        lines.append(f"Answer: {clue.answer}")
    lines.extend(
        [
            page,
            HASHTAGS,
        ]
    )
    return "\n".join(lines)


def youtube_drop_description(clue: Clue) -> str:
    """Public YouTube paste text. The answer stays in the film."""
    return "\n".join(
        [
            f"{SOCIAL_HANDLE} · {clue_line(clue)}",
            "",
            "Have a think. The parse is in the video.",
            f"{clue.paper} {clue.puzzle_id} · {clue.setter}",
            SITE_ORIGIN + "/",
            HASHTAGS,
        ]
    )


def facebook_title(clue: Clue) -> str:
    title = f"{SOCIAL_HANDLE} · {clue_line(clue)}"
    return title if len(title) <= 255 else title[:254].rstrip() + "…"


def youtube_description(item: SpokenClue) -> str:
    clue = item.clue
    page = item.site_path or SITE_ORIGIN
    return (
        f"{SOCIAL_HANDLE} — {BRAND_PROMISE}.\n"
        f"{CREDIT_LINE}\n\n"
        f"{clue_line(clue)}\n"
        f"Answer: {clue.answer}\n\n"
        f"{page}\n"
        f"Support: {SITE_ORIGIN}/support.html\n"
        f"Parse: {clue.source_url}\n"
        f"{clue.paper} {clue.puzzle_id} by {clue.setter}. "
        f"Blogged by {clue.blogger} on Fifteen Squared.\n"
        f"{get_scene(item.scene).youtube_credit}\n"
    )
