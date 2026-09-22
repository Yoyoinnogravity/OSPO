from __future__ import annotations

from twodown.config import BRAND, BRAND_PROMISE, CREDIT_LINE, SITE_ORIGIN
from twodown.models import Clue, SpokenClue
from twodown.scenes import get_scene

HASHTAGS = "#crypticcrossword #crypticfit #crosswordshorts #FifteenSquared"
SOCIAL_HANDLE = BRAND


def youtube_hashtags(clue: Clue) -> str:
    tags = [HASHTAGS]
    paper = clue.paper or ""
    if "Guardian" in paper:
        tags.append("#GuardianCryptic")
    elif "Independent" in paper:
        tags.append("#IndependentCryptic")
    elif "Financial" in paper:
        tags.append("#FTCryptic")
    setter = "".join(ch for ch in (clue.setter or "") if ch.isalnum())
    if setter:
        tags.append(f"#{setter}")
    return " ".join(tags)


def youtube_tags(clue: Clue) -> list[str]:
    """Search tags for YouTube. Never include the answer."""
    paper = (clue.paper or "").strip()
    setter = (clue.setter or "").strip()
    device = (clue.device or "").replace("_", " ").strip()
    tags = [
        BRAND,
        "cryptic crossword",
        "daily cryptic",
        "crossword shorts",
        "Fifteen Squared",
        "AI cryptic crossword",
        paper,
        f"{paper} cryptic" if paper else "",
        setter,
        device,
    ]
    if "Guardian" in paper:
        tags.extend(["Guardian cryptic", "Guardian crossword"])
    elif "Independent" in paper:
        tags.extend(["Independent cryptic", "Independent crossword"])
    elif "Financial" in paper:
        tags.extend(["FT cryptic", "Financial Times crossword"])
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        key = tag.casefold()
        if not tag or key in seen or clue.answer.casefold() in key:
            continue
        seen.add(key)
        out.append(tag)
    return out


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
    page = item.site_path or f"{SITE_ORIGIN}/c/{clue.slug}/"
    return (
        f"{SOCIAL_HANDLE} — {BRAND_PROMISE}.\n"
        f"{CREDIT_LINE}\n\n"
        f"{clue.paper} cryptic crossword by {clue.setter}. "
        f"Pause the Short, then hear the parse.\n\n"
        f"{clue_line(clue)}\n\n"
        f"Watch on {BRAND}: {page}\n"
        f"Support: {SITE_ORIGIN}/support.html\n"
        f"Parse via Fifteen Squared: {clue.source_url}\n"
        f"{clue.paper} {clue.puzzle_id} · {clue.number} {clue.direction} · {clue.setter}. "
        f"Blogged by {clue.blogger} on Fifteen Squared.\n"
        f"{get_scene(item.scene).youtube_credit}\n\n"
        f"{youtube_hashtags(clue)}\n\n"
        "—\n"
        "Spoiler (skip if you have not solved)\n"
        f"Answer: {clue.answer}\n"
    )
