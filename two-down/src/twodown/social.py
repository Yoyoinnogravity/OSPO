from __future__ import annotations

from pathlib import Path

from twodown.captions import facebook_title, social_caption
from twodown.config import CLUES_PER_DAY, SITE_ROOT, YOUTUBE_DAILY_LIMIT
from twodown.meta import facebook_ready, instagram_ready, upload_facebook, upload_instagram
from twodown.models import DailyPair
from twodown.tiktok import tiktok_ready, upload_short as upload_tiktok
from twodown.uploads import apply_ledger, record_youtube
from twodown.youtube import upload_pair as upload_youtube, youtube_hint, youtube_ready

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
        "youtube": youtube_hint(),
        "tiktok": "Set TWODOWN_TIKTOK_TOKEN to a TikTok user access token JSON with video.publish.",
        "instagram": "Set TWODOWN_META_TOKEN (access_token + ig_user_id) for the Instagram professional account.",
        "facebook": "Set TWODOWN_META_TOKEN (access_token + page_id) for the cryptic.fit Facebook Page.",
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
Each app gives you a token. Paste the JSON (never a password) as a GitHub Actions
secret so the daily workflow can upload, and optionally on the Cursor Cloud Agent
environment: {CURSOR_ENVIRONMENT}

INSTAGRAM + FACEBOOK  ->  TWODOWN_META_TOKEN      (quickest; one token does both)
  1. Make a cryptic.fit Facebook Page. Set Instagram to a professional
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
  2. Authorise the cryptic.fit account and copy the user access token.
  3. Secret value: {{"access_token": "TIKTOK_USER_TOKEN"}}
  Note: until TikTok audits the app, posts are limited to private / self-only.
  Public TikTok posting waits on their review, not on this code.

YOUTUBE  ->  TWODOWN_YOUTUBE_TOKEN   (this is the one that makes auto-upload work)
  Deploy only to the cryptic.fit channel (youtube.com/@crypticfit).
  Do not use youtube.com/@crypticfun — that handle is someone else's
  channel, and we do not own the .fun name.
  Same Google login can own Aled Morgan / carbonyoyo as a personal
  channel. When Google asks which channel, pick Cryptic Fit.
  Channel already exists: youtube.com/@crypticfit. Do not recreate it.
  Do not run Command Prompt scripts. The Cloud Agent can finish login:

  1. OAuth desktop client at {GOOGLE_CONSOLE} is already made (project
     cryptic-fit, YouTube Data API v3). The JSON is in Downloads as
     client_secret*.json.
  2. twodown youtube-auth --save-client ~/Downloads/client_secret*.json
     or paste that JSON as TWODOWN_YOUTUBE_CLIENT_SECRET.
  3. twodown youtube-auth --start
     Open the printed URL. Pick Cryptic Fit, not carbonyoyo. The next
     page fails to load — copy the whole address bar.
  4. twodown youtube-auth --finish 'PASTE_THE_URL' --upload
     That writes ~/.config/twodown/youtube-token.json (must include
     refresh_token) and posts the next Short unlisted.
  5. Paste that token JSON as repo secret TWODOWN_YOUTUBE_TOKEN
     (GitHub → Settings → Secrets and variables → Actions) so the
     daily workflow can upload without a human.
     The same JSON can also sit on the Cursor Cloud Agent environment.

Then GitHub Actions runs: twodown today / twodown upload
or a Cloud Agent runs:    twodown upload            (all four)
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
    youtube_limit: int | None = YOUTUBE_DAILY_LIMIT,
    site_root: Path | None = None,
) -> dict[str, list[str]]:
    """Upload Shorts to every connected platform. YouTube posts at most youtube_limit new films."""
    attach_site_videos(pair, site_root)
    apply_ledger(pair, site_root)
    notes: dict[str, list[str]] = {name: [] for name in PLATFORMS}
    status = platform_status()
    hints = setup_hints()

    if youtube:
        if not status["youtube"]:
            notes["youtube"] = [hints["youtube"]]
        else:
            try:
                notes["youtube"] = upload_youtube(pair, privacy=youtube_privacy, limit=youtube_limit)
            except Exception as exc:  # noqa: BLE001 — one platform must not block the others
                notes["youtube"] = [f"error: {exc}"]

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
    record_youtube(pair, site_root)
    return notes
