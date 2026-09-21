from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from twodown.captions import youtube_description
from twodown.config import BRAND, YOUTUBE_DAILY_LIMIT
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.tokens import CONFIG_DIR, secret_text

YOUTUBE_CHANNEL = BRAND
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_ENV = "TWODOWN_YOUTUBE_TOKEN"
CLIENT_ENV = "TWODOWN_YOUTUBE_CLIENT_SECRET"
TOKEN_FILENAME = "youtube-token.json"
CLIENT_FILENAME = "youtube-client-secret.json"


def youtube_ready() -> bool:
    info = _token_info()
    return bool(
        info
        and info.get("refresh_token")
        and info.get("client_id")
        and info.get("client_secret")
    )


def youtube_hint() -> str:
    text = secret_text(TOKEN_ENV, TOKEN_FILENAME)
    if not text:
        return (
            "Set TWODOWN_YOUTUBE_TOKEN to the authorized-user JSON from "
            "`twodown youtube-auth` (GitHub Actions secret or ~/.config/twodown/youtube-token.json)."
        )
    info = _token_info()
    if info is None:
        return "TWODOWN_YOUTUBE_TOKEN is not valid OAuth JSON. Re-run `twodown youtube-auth`."
    if not info.get("refresh_token"):
        return "YouTube token has no refresh_token. Re-run `twodown youtube-auth` so daily upload stays signed in."
    if not info.get("client_id") or not info.get("client_secret"):
        return (
            f"Set {CLIENT_ENV} to the Google OAuth desktop client JSON "
            f"(or put client_id and client_secret inside TWODOWN_YOUTUBE_TOKEN)."
        )
    return "YouTube is ready for unattended Shorts upload."


def _client_info() -> dict | None:
    text = secret_text(CLIENT_ENV, CLIENT_FILENAME)
    if not text or not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    block = data.get("installed") or data.get("web")
    if isinstance(block, dict):
        return block
    if data.get("client_id"):
        return data
    return None


def _token_info() -> dict | None:
    text = secret_text(TOKEN_ENV, TOKEN_FILENAME)
    if not text or not text.startswith("{"):
        return None
    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(info, dict):
        return None
    client = _client_info() or {}
    merged = dict(info)
    for key in ("client_id", "client_secret", "token_uri"):
        if not merged.get(key) and client.get(key):
            merged[key] = client[key]
    merged.setdefault("token_uri", "https://oauth2.googleapis.com/token")
    if not merged.get("refresh_token") and not merged.get("token"):
        return None
    return merged


def _credentials():
    info = _token_info()
    if not info:
        return None
    try:
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None
    try:
        return Credentials.from_authorized_user_info(info, scopes=SCOPES)
    except (ValueError, TypeError):
        return None


def token_path() -> Path:
    return CONFIG_DIR / TOKEN_FILENAME


def authorize(*, console: bool = False) -> Path:
    """One-time Google login for the cryptic.fit channel. Writes a refresh token."""
    client_text = secret_text(CLIENT_ENV, CLIENT_FILENAME)
    if not client_text or not client_text.startswith("{"):
        raise FileNotFoundError(
            f"Need the Google OAuth desktop client JSON as {CLIENT_ENV} "
            f"or ~/.config/twodown/{CLIENT_FILENAME}"
        )
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError("google-auth-oauthlib is required for twodown youtube-auth") from exc

    flow = InstalledAppFlow.from_client_config(json.loads(client_text), scopes=SCOPES)
    if console:
        creds = _run_console_flow(flow)
    else:
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    dest = token_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(creds.to_json(), encoding="utf-8")
    return dest


def _run_console_flow(flow):
    """Headless helper: print the Google URL, then accept a pasted redirect or code."""
    flow.redirect_uri = flow.redirect_uri or "http://localhost"
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    print("Open this URL, pick the cryptic.fit channel, then paste the redirect URL or the code:")
    print(auth_url)
    pasted = input("Redirect URL or code: ").strip()
    if not pasted:
        raise ValueError("No authorization code pasted")
    if pasted.startswith("http"):
        query = parse_qs(urlparse(pasted).query)
        code = (query.get("code") or [""])[0]
    else:
        code = pasted
    if not code:
        raise ValueError("Could not find ?code= in that redirect URL")
    flow.fetch_token(code=code)
    return flow.credentials


def video_title(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    title = f"{YOUTUBE_CHANNEL} · {clue.clue}{enum} #Shorts"
    if len(title) <= 100:
        return title
    room = 100 - len(f"{YOUTUBE_CHANNEL} · {enum} #Shorts")
    clipped = clue.clue[: max(10, room - 1)].rstrip() + "…"
    return f"{YOUTUBE_CHANNEL} · {clipped}{enum} #Shorts"[:100]


def video_description(item: SpokenClue) -> str:
    return youtube_description(item)


def upload_short(item: SpokenClue, privacy: str = "public") -> str | None:
    """Upload one Short to the authorised channel.

    Upload to the authorised cryptic.fit channel. Returns the video id,
    or None if credentials are missing.
    """
    if not item.video_path:
        return None
    creds = _credentials()
    if creds is None:
        return None
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": video_title(item.clue),
            "description": video_description(item),
            "tags": ["cryptic.fit", "cryptic crossword", item.clue.device, item.clue.setter],
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(item.video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    result = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    video_id = result.get("id")
    item.youtube_id = video_id
    return video_id


def upload_pair(pair: DailyPair, privacy: str = "public", limit: int | None = YOUTUBE_DAILY_LIMIT) -> list[str]:
    """Upload unpublished Shorts on this pair. limit=None means the whole pair."""
    ids: list[str] = []
    uploaded = 0
    for item in pair.clues:
        if item.youtube_id:
            ids.append(item.youtube_id)
            continue
        if limit is not None and uploaded >= limit:
            continue
        video_id = upload_short(item, privacy=privacy)
        if video_id:
            ids.append(video_id)
            uploaded += 1
    pair.youtube_ids = [item.youtube_id for item in pair.clues if item.youtube_id]
    return ids
