from __future__ import annotations

import os
from pathlib import Path

from twodown.config import BRAND, CLUES_PER_DAY, SITE_ORIGIN
from twodown.models import Clue, DailyPair, SpokenClue

YOUTUBE_CHANNEL = "Cryptic Fun"
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


def video_title(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    title = f"{YOUTUBE_CHANNEL} · {clue.clue}{enum} #Shorts"
    if len(title) <= 100:
        return title
    room = 100 - len(f"{YOUTUBE_CHANNEL} · {enum} #Shorts")
    clipped = clue.clue[: max(10, room - 1)].rstrip() + "…"
    return f"{YOUTUBE_CHANNEL} · {clipped}{enum} #Shorts"[:100]


def video_description(item: SpokenClue) -> str:
    clue = item.clue
    page = item.site_path or SITE_ORIGIN
    return (
        f"{YOUTUBE_CHANNEL} — two cryptic clues a day.\n"
        f"{BRAND}\n\n"
        f"{clue.clue} ({clue.enumeration})\n"
        f"Answer: {clue.answer}\n\n"
        f"{page}\n"
        f"Parse: {clue.source_url}\n"
        f"{clue.paper} {clue.puzzle_id} by {clue.setter}. "
        f"Blogged by {clue.blogger} on Fifteen Squared.\n"
    )


def upload_short(item: SpokenClue, privacy: str = "public") -> str | None:
    """Upload one Short as Cryptic Fun. Returns the video id, or None if credentials are missing."""
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
            "tags": ["Cryptic Fun", "cryptic.fun", "cryptic crossword", item.clue.device, item.clue.setter],
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
