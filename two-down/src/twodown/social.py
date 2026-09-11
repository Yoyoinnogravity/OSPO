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


GRAPH_EXPLORER = "https://developers.facebook.com/tools/explorer/"
META_APPS = "https://developers.facebook.com/apps/"
TIKTOK_APPS = "https://developers.tiktok.com/apps/"
GOOGLE_CONSOLE = "https://console.cloud.google.com/apis/credentials"
META_PERMISSIONS = (
    "pages_show_list, pages_manage_posts, pages_read_engagement, "
    "instagram_basic, instagram_content_publish"
)


def connect_instructions() -> str:
    """Exact steps to get each token. No account passwords are ever needed here."""
    return f"""The upload agent cannot log into YouTube, TikTok, Instagram or Facebook as you.
Each app gives you a token. Paste the JSON (never a password) as a secret on the
Cursor Cloud Agent environment: {CURSOR_ENVIRONMENT}

INSTAGRAM + FACEBOOK  ->  TWODOWN_META_TOKEN      (quickest; one token does both)
  1. Make a Cryptic Fun Facebook Page. Set Instagram to a professional
     account and link it to that Page.
  2. Create an app at {META_APPS} (type: Business).
  3. Open {GRAPH_EXPLORER}, pick the app, add permissions:
     {META_PERMISSIONS}
     then Generate Access Token.
  4. In the same tool run  GET /me/accounts            -> copy the Page "id"
     and                   GET /<page_id>?fields=instagram_business_account
                                                        -> copy that "id"
  5. Secret value:
     {{"access_token": "PAGE_TOKEN", "page_id": "PAGE_ID", "ig_user_id": "IG_ID"}}
     Use the Page token from step 4, not your personal user token, or posts fail.

TIKTOK  ->  TWODOWN_TIKTOK_TOKEN
  1. Register an app at {TIKTOK_APPS} and add the Content Posting API
     with the video.publish scope.
  2. Authorise the Cryptic Fun account and copy the user access token.
  3. Secret value: {{"access_token": "TIKTOK_USER_TOKEN"}}
  Note: until TikTok audits the app, posts are limited to private / self-only.
  Public TikTok posting waits on their review, not on this code.

YOUTUBE  ->  TWODOWN_YOUTUBE_TOKEN
  1. OAuth desktop client at {GOOGLE_CONSOLE}, YouTube Data API v3 enabled.
  2. Authorise the Cryptic Fun channel for scope youtube.upload.
  3. Secret value: the authorized-user JSON (token, refresh_token, token_uri,
     client_id, client_secret, scopes).

Then a Cloud Agent runs:  twodown upload            (all four)
                          twodown upload --no-youtube  (TikTok + IG + FB only)
"""


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
