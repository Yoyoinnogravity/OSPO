from __future__ import annotations

import json
from pathlib import Path

from twodown.captions import youtube_description
from twodown.config import BRAND, CLUES_PER_DAY, SITE_ORIGIN, SITE_ROOT
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
    lead = f"{YOUTUBE_CHANNEL} · "
    theme = (clue.theme or "").strip()
    if theme:
        lead = f"{YOUTUBE_CHANNEL} · {theme} · "
    title = f"{lead}{clue.clue}{enum} #Shorts"
    if len(title) <= 100:
        return title
    room = 100 - len(f"{lead}{enum} #Shorts")
    clipped = clue.clue[: max(10, room - 1)].rstrip() + "…"
    return f"{lead}{clipped}{enum} #Shorts"[:100]


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


def apply_ledger_ids(pair: DailyPair, root: Path | None = None) -> None:
    """Copy committed ids onto the pair so a later run does not upload again."""
    ids: list[str] = []
    for item in pair.clues:
        if not item.youtube_id:
            item.youtube_id = known_youtube_id(item.clue.slug, root)
        if item.youtube_id:
            ids.append(item.youtube_id)
    if ids:
        pair.youtube_ids = ids


def known_youtube_id(slug: str, root: Path | None = None) -> str | None:
    from twodown.staging import committed_youtube_id, load_uploads, videos_by_slug

    data = load_uploads(Path(root or SITE_ROOT))
    return committed_youtube_id(videos_by_slug(data).get(slug))


def remember_youtube_ids(pair: DailyPair, root: Path | None = None) -> bool:
    """Write new ids into youtube-uploads.json. Existing ids are not replaced."""
    from twodown.staging import record_youtube_upload

    site = Path(root or SITE_ROOT)
    changed = False
    for item in pair.clues:
        if not item.youtube_id:
            continue
        if record_youtube_upload(site, item.clue.slug, item.youtube_id):
            changed = True
    return changed


def sync_channel_ids(pair: DailyPair, root: Path | None = None) -> bool:
    """Fill ids from the ledger and the public channel feed. Never guesses."""
    from twodown.staging import apply_feed_matches, fetch_channel_feed

    site = Path(root or SITE_ROOT)
    changed = False
    for item in pair.clues:
        if item.youtube_id:
            continue
        found = known_youtube_id(item.clue.slug, site)
        if found:
            item.youtube_id = found
    missing = [item for item in pair.clues if not item.youtube_id]
    if not missing:
        return changed
    try:
        entries = fetch_channel_feed()
    except Exception:
        return changed
    films = [(item.clue.slug, video_title(item.clue)) for item in missing]
    applied = apply_feed_matches(site, entries, films)
    if applied:
        changed = True
    for item in missing:
        match = applied.get(item.clue.slug)
        if match:
            item.youtube_id = match["youtube_id"]
    return changed


def upload_pair(pair: DailyPair, privacy: str = "public") -> list[str]:
    ids: list[str] = []
    fresh: list[SpokenClue] = []
    for item in pair.clues:
        if not item.youtube_id:
            item.youtube_id = known_youtube_id(item.clue.slug)
        if item.youtube_id:
            ids.append(item.youtube_id)
        else:
            fresh.append(item)
    for item in fresh[:CLUES_PER_DAY]:
        video_id = upload_short(item, privacy=privacy)
        if video_id:
            ids.append(video_id)
    pair.youtube_ids = ids
    return ids
