from __future__ import annotations

from pathlib import Path

from twodown.captions import facebook_title, social_caption
from twodown.config import CLUES_PER_DAY, SITE_ROOT
from twodown.meta import facebook_ready, instagram_ready, upload_facebook, upload_instagram
from twodown.models import DailyPair
from twodown.tiktok import tiktok_ready, upload_short as upload_tiktok
from twodown.youtube import upload_pair as upload_youtube, youtube_ready

PLATFORMS = ("youtube", "tiktok", "instagram", "facebook")
CURSOR_ENVIRONMENT = "https://cursor.com/dashboard/cloud-agents/environments"


def platform_status() -> dict[str, bool]:
    return {
        "youtube": youtube_ready(),
        "tiktok": tiktok_ready(),
        "instagram": instagram_ready(),
        "facebook": facebook_ready(),
    }


def setup_hints() -> dict[str, str]:
    return {
        "youtube": "Set TWODOWN_YOUTUBE_TOKEN to an authorized YouTube OAuth token JSON for Cryptic Fun.",
        "tiktok": "Set TWODOWN_TIKTOK_TOKEN to a TikTok user access token JSON with video.publish.",
        "instagram": "Set TWODOWN_META_TOKEN (access_token + ig_user_id) for the Instagram professional account.",
        "facebook": "Set TWODOWN_META_TOKEN (access_token + page_id) for the Cryptic Fun Facebook Page.",
    }


def connect_instructions() -> str:
    return (
        "The upload agent cannot log into YouTube, TikTok, Instagram or Facebook as you.\n"
        "Connect each app once. Paste the JSON (not your password) as secrets on the\n"
        f"Cursor Cloud Agent environment: {CURSOR_ENVIRONMENT}\n"
        "\n"
        "  TWODOWN_YOUTUBE_TOKEN   YouTube OAuth user JSON with youtube.upload\n"
        "  TWODOWN_TIKTOK_TOKEN    {\"access_token\": \"...\"}\n"
        "  TWODOWN_META_TOKEN      {\"access_token\": \"...\", \"page_id\": \"...\", \"ig_user_id\": \"...\"}\n"
        "\n"
        "After that, a Cloud Agent can run `twodown today` and `twodown upload` for you.\n"
    )


def attach_site_videos(pair: DailyPair, site_root: Path | None = None) -> DailyPair:
    """Point clues at two-down/site/media/{slug}.mp4 when the render path is missing."""
    root = Path(site_root or SITE_ROOT)
    for item in pair.clues:
        if item.video_path and Path(item.video_path).exists():
            continue
        site_video = root / "media" / f"{item.clue.slug}.mp4"
        if site_video.exists():
            item.video_path = str(site_video)
    return pair


def _record(existing: str | None, uploader, notes: list[str]) -> None:
    if existing:
        notes.append(existing)
        return
    try:
        video_id = uploader()
        if video_id:
            notes.append(video_id)
    except Exception as exc:  # noqa: BLE001 — one platform must not block the others
        notes.append(f"error: {exc}")


def publish_pair(
    pair: DailyPair,
    *,
    youtube: bool = True,
    tiktok: bool = True,
    instagram: bool = True,
    facebook: bool = True,
    youtube_privacy: str = "public",
) -> dict[str, list[str]]:
    """Upload today's two Shorts to every connected platform. One failure does not stop the rest."""
    attach_site_videos(pair)
    notes: dict[str, list[str]] = {name: [] for name in PLATFORMS}
    status = platform_status()
    hints = setup_hints()

    if youtube:
        if not status["youtube"]:
            notes["youtube"] = [hints["youtube"]]
        else:
            notes["youtube"] = upload_youtube(pair, privacy=youtube_privacy)

    if tiktok and not status["tiktok"]:
        notes["tiktok"] = [hints["tiktok"]]
    if instagram and not status["instagram"]:
        notes["instagram"] = [hints["instagram"]]
    if facebook and not status["facebook"]:
        notes["facebook"] = [hints["facebook"]]

    for item in pair.clues[:CLUES_PER_DAY]:
        caption = social_caption(item)
        if tiktok and status["tiktok"]:
            _record(item.tiktok_id, lambda item=item, caption=caption: upload_tiktok(item, caption), notes["tiktok"])
        if instagram and status["instagram"]:
            _record(
                item.instagram_id,
                lambda item=item, caption=caption: upload_instagram(item, caption),
                notes["instagram"],
            )
        if facebook and status["facebook"]:
            _record(
                item.facebook_id,
                lambda item=item, caption=caption: upload_facebook(
                    item, caption, facebook_title(item.clue)
                ),
                notes["facebook"],
            )

    pair.tiktok_ids = [c.tiktok_id for c in pair.clues if c.tiktok_id]
    pair.instagram_ids = [c.instagram_id for c in pair.clues if c.instagram_id]
    pair.facebook_ids = [c.facebook_id for c in pair.clues if c.facebook_id]
    return notes
