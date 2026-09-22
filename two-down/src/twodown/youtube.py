from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from twodown.captions import youtube_description, youtube_tags
from twodown.config import BRAND, CLUES_PER_DAY
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.render import draw_thumbnail
from twodown.tokens import CONFIG_DIR, secret_text

YOUTUBE_CHANNEL = BRAND
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_ENV = "TWODOWN_YOUTUBE_TOKEN"
CLIENT_ENV = "TWODOWN_YOUTUBE_CLIENT_SECRET"
TOKEN_FILENAME = "youtube-token.json"
CLIENT_FILENAME = "youtube-client-secret.json"
PENDING_FILENAME = "youtube-auth-pending.json"
REDIRECT_URI = "http://localhost"


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
            "Set TWODOWN_YOUTUBE_TOKEN from `twodown youtube-auth --start` then "
            "`twodown youtube-auth --finish URL` (or a laptop `twodown youtube-auth`)."
        )
    info = _token_info()
    if info is None:
        return "TWODOWN_YOUTUBE_TOKEN is not valid JSON."
    if not info.get("refresh_token"):
        return "TWODOWN_YOUTUBE_TOKEN is missing refresh_token — run youtube-auth again."
    return "ready"


def _token_info() -> dict | None:
    text = secret_text(TOKEN_ENV, TOKEN_FILENAME)
    if not text or not text.startswith("{"):
        return None
    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        return None
    return info if isinstance(info, dict) else None


def _credentials():
    info = _token_info()
    if info is None:
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


def pending_path() -> Path:
    return CONFIG_DIR / PENDING_FILENAME


def client_path() -> Path:
    return CONFIG_DIR / CLIENT_FILENAME


def authorization_code(pasted: str) -> str:
    """Accept either a localhost redirect URL or the bare ?code= value."""
    pasted = pasted.strip().strip("'\"")
    if not pasted:
        raise ValueError("No authorization code pasted")
    if pasted.startswith("http"):
        query = parse_qs(urlparse(pasted).query)
        code = (query.get("code") or [""])[0]
        if not code:
            raise ValueError("Redirect URL has no code= parameter")
        return code
    return pasted


def _load_client_config() -> dict:
    text = secret_text(CLIENT_ENV, CLIENT_FILENAME)
    if not text or not text.startswith("{"):
        raise FileNotFoundError(
            f"Need the Google OAuth desktop client JSON as {CLIENT_ENV} "
            f"or ~/.config/twodown/{CLIENT_FILENAME}"
        )
    client = json.loads(text)
    if "installed" not in client and "web" not in client:
        raise ValueError("Client JSON must be a Google installed-app OAuth client")
    return client


def _save_client_secret(client: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = client_path()
    path.write_text(json.dumps(client), encoding="utf-8")
    path.chmod(0o600)


def _save_token(creds) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = token_path()
    path.write_text(creds.to_json(), encoding="utf-8")
    path.chmod(0o600)
    pending = pending_path()
    if pending.exists():
        pending.unlink()
    return path


def start_authorization() -> str:
    """Print a Google consent URL for Cloud Agent / laptop handoff."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client = _load_client_config()
    flow = InstalledAppFlow.from_client_config(client, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    pending = {
        "state": state,
        "redirect_uri": flow.redirect_uri,
        "code_verifier": getattr(flow, "code_verifier", None),
        "client_config": client,
        "scopes": SCOPES,
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = pending_path()
    path.write_text(json.dumps(pending), encoding="utf-8")
    path.chmod(0o600)
    return auth_url


def finish_authorization(pasted: str) -> Path:
    """Exchange the localhost redirect (or bare code) for a refresh token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    pending_file = pending_path()
    if not pending_file.exists():
        raise FileNotFoundError(
            "No pending OAuth session. Run `twodown youtube-auth --start` first."
        )
    pending = json.loads(pending_file.read_text(encoding="utf-8"))
    redirect_uri = pending.get("redirect_uri") or REDIRECT_URI
    if redirect_uri.startswith("http://"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    flow = InstalledAppFlow.from_client_config(pending["client_config"], scopes=pending["scopes"])
    flow.redirect_uri = redirect_uri
    verifier = pending.get("code_verifier")
    if verifier:
        flow.code_verifier = verifier
        flow.autogenerate_code_verifier = False
    pasted = pasted.strip()
    if pasted.startswith("http"):
        flow.fetch_token(authorization_response=pasted)
    else:
        flow.fetch_token(code=authorization_code(pasted))
    return _save_token(flow.credentials)


def authorize(*, console: bool = False) -> Path:
    """One-time Google login on a laptop with a browser."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client = _load_client_config()
    flow = InstalledAppFlow.from_client_config(client, scopes=SCOPES)
    if console:
        creds = flow.run_console()
    else:
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    return _save_token(creds)


def video_title(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    suffix = f"{enum} #Shorts"
    mid = f"{clue.paper} cryptic by {clue.setter}"
    prefix = f"{YOUTUBE_CHANNEL} · {mid} · "
    full = f"{prefix}{clue.clue}{suffix}"
    if len(full) <= 100:
        return full
    room = 100 - len(prefix) - len(suffix)
    clipped = clue.clue[: max(10, room - 1)].rstrip() + "…"
    return f"{prefix}{clipped}{suffix}"[:100]


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
            "tags": youtube_tags(item.clue),
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
    if video_id:
        thumb = _ensure_thumbnail(item)
        if thumb:
            try:
                set_thumbnail(video_id, thumb)
            except Exception:
                pass  # verified channels only; the Short still uploads
    return video_id


def _ensure_thumbnail(item: SpokenClue) -> Path | None:
    if item.thumbnail_path and Path(item.thumbnail_path).exists():
        return Path(item.thumbnail_path)
    if not item.video_path:
        dest = Path("/tmp/twodown-thumbs") / f"{item.clue.slug}-thumb.jpg"
    else:
        dest = Path(item.video_path).with_name(f"{item.clue.slug}-thumb.jpg")
    path = draw_thumbnail(item.clue, dest)
    item.thumbnail_path = str(path)
    return path


def set_thumbnail(video_id: str, path: str | Path) -> bool:
    """Replace YouTube's auto frame (often the answer) with the clue-only still."""
    if not video_id:
        return False
    image = Path(path)
    if not image.exists():
        return False
    creds = _credentials()
    if creds is None:
        return False
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(image), mimetype="image/jpeg"),
    ).execute()
    return True


def upload_pair(pair: DailyPair, privacy: str = "public") -> list[str]:
    ids: list[str] = []
    for item in pair.clues[:CLUES_PER_DAY]:
        if item.youtube_id:
            ids.append(item.youtube_id)
            continue
        video_id = upload_short(item, privacy=privacy)
        if video_id:
            ids.append(video_id)
    pair.youtube_ids = ids
    return ids
