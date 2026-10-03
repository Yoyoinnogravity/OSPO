from __future__ import annotations

import json
from pathlib import Path

from twodown.captions import youtube_description
from twodown.config import BRAND, CLUES_PER_DAY, SITE_ORIGIN
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.render import write_thumbnail
from twodown.tokens import secret_text

YOUTUBE_CHANNEL = BRAND
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@crypticfit"
YOUTUBE_STUDIO = "https://www.youtube.com/upload"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_ENV = "TWODOWN_YOUTUBE_TOKEN"
CLIENT_ENV = "TWODOWN_YOUTUBE_CLIENT_SECRET"
# YouTube videoCategories.list: 27 = Education.
YOUTUBE_CATEGORY_EDUCATION = "27"


def short_mp4_url(slug: str) -> str:
    """Public file Aled downloads, then drops on YouTube Studio."""
    return f"{SITE_ORIGIN}/media/{slug}.mp4"


def video_title_from_line(clue_line: str) -> str:
    """Same 100-character Short title as video_title, from an already-joined clue line."""
    line = (clue_line or "").strip()
    title = f"{YOUTUBE_CHANNEL} · {line} #Shorts"
    if len(title) <= 100:
        return title
    room = 100 - len(f"{YOUTUBE_CHANNEL} ·  #Shorts")
    clipped = line[: max(10, room - 1)].rstrip() + "…"
    return f"{YOUTUBE_CHANNEL} · {clipped} #Shorts"[:100]


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


def thumbnail_file(item: SpokenClue) -> Path | None:
    """Unsolved JPEG for this Short, never a frame that shows the answer."""
    if item.thumbnail_path and Path(item.thumbnail_path).exists():
        return Path(item.thumbnail_path)
    if item.clue is None:
        return None
    dest = Path(item.video_path).with_name("thumb.jpg") if item.video_path else Path("/tmp") / f"{item.clue.slug}-thumb.jpg"
    path = write_thumbnail(item.clue, dest)
    item.thumbnail_path = str(path)
    return path


def _set_thumbnail(youtube, video_id: str, item: SpokenClue) -> None:
    path = thumbnail_file(item)
    if path is None or not video_id:
        return
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(path), mimetype="image/jpeg", resumable=False)
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def video_insert_body(item: SpokenClue, privacy: str = "public") -> dict:
    """videos.insert snippet+status. Only fields the Data API v3 actually accepts.

    Studio-only prompts (paid promotion, age restriction, not a movie) have
    no write field on videos.insert. This runs only when a token exists.
    """
    return {
        "snippet": {
            "title": video_title(item.clue),
            "description": video_description(item),
            "tags": ["cryptic.fit", "cryptic crossword", item.clue.device, item.clue.setter],
            "categoryId": YOUTUBE_CATEGORY_EDUCATION,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }


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
    body = video_insert_body(item, privacy=privacy)
    media = MediaFileUpload(item.video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    result = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    video_id = result.get("id")
    item.youtube_id = video_id
    if video_id:
        try:
            _set_thumbnail(youtube, video_id, item)
        except Exception as exc:
            # The film is already on the channel. Losing the id here would
            # upload a second copy on the next run.
            print(f"YouTube thumbnail was not set for {video_id}: {exc}")
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
