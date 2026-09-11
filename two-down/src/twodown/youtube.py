from __future__ import annotations

import os
from pathlib import Path

from twodown.config import SITE_ORIGIN
from twodown.models import SpokenClue

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_ENV = "TWODOWN_YOUTUBE_TOKEN"
CLIENT_ENV = "TWODOWN_YOUTUBE_CLIENT_SECRET"


def _token_path() -> Path | None:
    raw = os.environ.get(TOKEN_ENV)
    if raw:
        return Path(raw)
    default = Path.home() / ".config" / "twodown" / "youtube-token.json"
    if default.exists():
        return default
    return None


def youtube_ready() -> bool:
    return _credentials() is not None


def _credentials():
    token = _token_path()
    if not token or not token.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None
    return Credentials.from_authorized_user_file(str(token), scopes=SCOPES)


def upload_short(item: SpokenClue, privacy: str = "unlisted") -> str | None:
    """Upload one Short. Returns the video id, or None if credentials are missing."""
    if not item.video_path:
        return None
    creds = _credentials()
    if creds is None:
        return None
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    clue = item.clue
    title = f"cryptic.fun · {clue.setter} · {clue.clue[:48]} ({clue.enumeration}) #Shorts"
    title = title[:100]
    page = item.site_path or SITE_ORIGIN
    description = (
        f"{clue.clue} ({clue.enumeration})\n"
        f"Answer: {clue.answer}\n\n"
        f"{page}\n"
        f"Parse: {clue.source_url}\n"
        f"{clue.paper} {clue.puzzle_id} by {clue.setter}. "
        f"Blogged by {clue.blogger} on Fifteen Squared.\n"
    )
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["cryptic crossword", clue.device, clue.setter, "cryptic.fun"],
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
