from __future__ import annotations

import json
from pathlib import Path

from twodown.captions import youtube_description
from twodown.config import BRAND, CLUES_PER_DAY
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.render import draw_thumbnail
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
    if video_id:
        thumb = _ensure_thumbnail(item)
        if thumb:
            set_thumbnail(video_id, thumb)
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
