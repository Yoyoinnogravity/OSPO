from __future__ import annotations

import json

from twodown.captions import youtube_description
from twodown.config import BRAND, CLUES_PER_DAY
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.tokens import secret_text

YOUTUBE_CHANNEL = BRAND
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_ENV = "TWODOWN_YOUTUBE_TOKEN"
CLIENT_ENV = "TWODOWN_YOUTUBE_CLIENT_SECRET"


def youtube_ready() -> bool:
    return _credentials() is not None


def _credentials():
    text = secret_text(TOKEN_ENV, "youtube-token.json")
    if not text or not text.startswith("{"):
        return None
    try:
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None
    try:
        info = json.loads(text)
        return Credentials.from_authorized_user_info(info, scopes=SCOPES)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


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

    Prefer cryptic.fun. If that Brand Account is not ready, the token may
    be Aled Morgan / carbonyoyo. Returns the video id, or None if credentials
    are missing.
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
            "tags": ["cryptic.fun", "cryptic crossword", item.clue.device, item.clue.setter],
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
