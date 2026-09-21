from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from twodown.captions import youtube_description
from twodown.config import BRAND, YOUTUBE_DAILY_LIMIT, YOUTUBE_SKIP_SLUGS
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.tokens import CONFIG_DIR, secret_text

YOUTUBE_CHANNEL = BRAND
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
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
            "`twodown youtube-auth --finish URL` (or a laptop `twodown youtube-auth`). "
            "Do not use Command Prompt scripts."
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
            raise ValueError("Could not find ?code= in that redirect URL")
        return code
    return pasted


def _client_json_ok(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    block = data.get("installed") or data.get("web")
    if isinstance(block, dict) and block.get("client_id"):
        return True
    return bool(data.get("client_id"))


def discover_client_text() -> str | None:
    """Find the desktop OAuth client JSON. Downloads/ is the usual Windows location."""
    text = secret_text(CLIENT_ENV, CLIENT_FILENAME)
    if text and text.startswith("{"):
        return text
    downloads = Path.home() / "Downloads"
    if not downloads.is_dir():
        return None
    matches = sorted(downloads.glob("client_secret*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for match in matches:
        try:
            candidate = match.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not candidate.startswith("{"):
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if _client_json_ok(data):
            return candidate
    return None


def save_client_secret(raw: str) -> Path:
    """Store a pasted or downloaded Google desktop client JSON for youtube-auth."""
    raw = raw.strip()
    if not raw:
        raise ValueError("No OAuth client JSON provided")
    path = Path(raw).expanduser()
    if len(raw) < 512 and path.exists() and path.is_file():
        raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith("{"):
        raise ValueError("OAuth client must be a JSON object from Google Cloud credentials.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OAuth client JSON is invalid: {exc}") from exc
    if not _client_json_ok(data):
        raise ValueError("OAuth client JSON is missing client_id")
    dest = client_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dest


def _require_client_text() -> str:
    client_text = discover_client_text()
    if not client_text or not client_text.startswith("{"):
        raise FileNotFoundError(
            f"Need the Google OAuth desktop client JSON as {CLIENT_ENV}, "
            f"~/.config/twodown/{CLIENT_FILENAME}, or Downloads/client_secret*.json. "
            "Paste that file into `twodown youtube-auth --save-client`."
        )
    return client_text


def _installed_flow(client_text: str):
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError("google-auth-oauthlib is required for twodown youtube-auth") from exc
    flow = InstalledAppFlow.from_client_config(json.loads(client_text), scopes=SCOPES)
    return flow


def start_authorization() -> str:
    """Printable Google URL for Cloud Agents. Aled opens it and pastes the redirect back."""
    client_text = _require_client_text()
    save_client_secret(client_text)
    flow = _installed_flow(client_text)
    flow.redirect_uri = REDIRECT_URI
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    pending = {
        "client_config": json.loads(client_text),
        "state": state,
        "code_verifier": getattr(flow, "code_verifier", None),
        "redirect_uri": flow.redirect_uri,
        "scopes": SCOPES,
    }
    dest = pending_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(pending), encoding="utf-8")
    return auth_url


def finish_authorization(pasted: str) -> Path:
    """Exchange the pasted localhost redirect (or code) for a refresh token."""
    dest = pending_path()
    if not dest.exists():
        raise FileNotFoundError("No pending YouTube login. Run `twodown youtube-auth --start` first.")
    pending = json.loads(dest.read_text(encoding="utf-8"))
    flow = _installed_flow(json.dumps(pending["client_config"]))
    flow.redirect_uri = pending.get("redirect_uri") or REDIRECT_URI
    if pending.get("code_verifier"):
        flow.code_verifier = pending["code_verifier"]
    flow.fetch_token(code=authorization_code(pasted))
    token = token_path()
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(flow.credentials.to_json(), encoding="utf-8")
    dest.unlink(missing_ok=True)
    return token


def authorize(*, console: bool = False) -> Path:
    """One-time Google login for the cryptic.fit channel. Writes a refresh token."""
    client_text = _require_client_text()
    save_client_secret(client_text)
    if console:
        url = start_authorization()
        print("Open this URL, pick Cryptic Fit (not carbonyoyo).")
        print("The next page will fail to load. That is expected.")
        print("Copy the whole address bar and paste it here.")
        print(url)
        pasted = input("Redirect URL or code: ").strip()
        return finish_authorization(pasted)
    flow = _installed_flow(client_text)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    dest = token_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(creds.to_json(), encoding="utf-8")
    return dest


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
    if item.clue.slug in YOUTUBE_SKIP_SLUGS:
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


def delete_video(video_id: str) -> bool:
    """Remove a Short from the authorised channel. Returns True if YouTube accepted the delete."""
    if not video_id or video_id in {"skipped", "deleted"}:
        return False
    creds = _credentials()
    if creds is None:
        return False
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=creds)
    youtube.videos().delete(id=video_id).execute()
    return True


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
