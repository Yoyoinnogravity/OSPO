from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

from twodown.config import SITE_ORIGIN, TAGLINE
from twodown.youtube import video_title_from_line

UPLOADS_NAME = "youtube-uploads.json"
NEEDS_UPLOAD_ZIP = "crypticfit-needs-upload.zip"
CHANNEL_HANDLE = "@crypticfit"
CHANNEL_ID = "UCjJDo1MB7pFjtJfeV2Yb7eA"
CHANNEL_FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
INTRO_YOUTUBE_ID = "8D8XTzkgNLE"
INTRO_NOTE = "Channel intro Short. Not a published daily /c/ film."
LOCAL_STORAGE_KEY = "cryptic-fit-youtube-uploads"
STUDIO_DROP_HELP = (
    "Download the file, then drag it from your Downloads folder onto YouTube Studio. "
    "You cannot drag from this page."
)
YOUTUBE_POSTER_NOTE = "The poster is the unsolved clue. Do not upload a frame that shows the answer."
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ATOM = "{http://www.w3.org/2005/Atom}"
_YT = "{http://www.youtube.com/xml/schemas/2015}"
_SLUG_IN_TEXT = re.compile(r"/c/([a-z0-9-]+)/?", re.I)


def studio_description() -> str:
    """Spoiler-free YouTube description paste. Never the answer."""
    return f"{TAGLINE}\n{SITE_ORIGIN}"


def short_download_name(slug: str) -> str:
    return f"crypticfit-{slug}.mp4"


def shorts_url(youtube_id: str) -> str:
    return f"https://www.youtube.com/shorts/{youtube_id}"


def parse_youtube_id(text: str | None) -> str | None:
    """Read a Shorts / watch URL or a bare 11-character id. None if unclear."""
    raw = (text or "").strip()
    if not raw:
        return None
    if _YOUTUBE_ID.fullmatch(raw):
        return raw
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in {"youtu.be", "youtube.com", "m.youtube.com", "music.youtube.com"}:
        parts = [part for part in parsed.path.split("/") if part]
        if host == "youtu.be" and parts:
            candidate = parts[0]
            return candidate if _YOUTUBE_ID.fullmatch(candidate) else None
        if parts and parts[0] in {"shorts", "embed", "live", "v"} and len(parts) > 1:
            candidate = parts[1]
            return candidate if _YOUTUBE_ID.fullmatch(candidate) else None
        query_id = (parse_qs(parsed.query).get("v") or [None])[0]
        if query_id and _YOUTUBE_ID.fullmatch(query_id):
            return query_id
    return None


def uploads_path(root: Path) -> Path:
    return Path(root) / UPLOADS_NAME


def empty_uploads() -> dict[str, Any]:
    return {
        "channel": CHANNEL_HANDLE,
        "channel_id": CHANNEL_ID,
        "intro": {"youtube_id": INTRO_YOUTUBE_ID, "note": INTRO_NOTE},
        "videos": [],
    }


def load_uploads(root: Path) -> dict[str, Any]:
    path = uploads_path(root)
    if not path.is_file():
        return empty_uploads()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_uploads()
    if not isinstance(data, dict):
        return empty_uploads()
    videos = data.get("videos")
    if not isinstance(videos, list):
        data["videos"] = []
    intro = data.setdefault("intro", {})
    if isinstance(intro, dict) and not intro.get("youtube_id"):
        intro["youtube_id"] = INTRO_YOUTUBE_ID
        intro.setdefault("note", INTRO_NOTE)
    data.setdefault("channel", CHANNEL_HANDLE)
    data.setdefault("channel_id", CHANNEL_ID)
    return data


def save_uploads(root: Path, data: dict[str, Any]) -> Path:
    dest = uploads_path(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return dest


def published_slugs(root: Path) -> list[str]:
    clue_root = Path(root) / "c"
    if not clue_root.is_dir():
        return []
    found = [
        page.name
        for page in sorted(clue_root.iterdir())
        if page.is_dir() and (page / "index.html").is_file()
    ]
    return found


def videos_by_slug(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in data.get("videos") or []:
        if not isinstance(raw, dict):
            continue
        slug = str(raw.get("slug") or "").strip()
        if slug:
            out[slug] = raw
    return out


def committed_youtube_id(record: dict[str, Any] | None) -> str | None:
    if not record:
        return None
    return parse_youtube_id(str(record.get("youtube_id") or ""))


def is_uploaded(record: dict[str, Any] | None) -> bool:
    return committed_youtube_id(record) is not None


def pending_slugs(root: Path, data: dict[str, Any] | None = None) -> list[str]:
    uploads = data if data is not None else load_uploads(root)
    known = videos_by_slug(uploads)
    return [slug for slug in published_slugs(root) if not is_uploaded(known.get(slug))]


def uploaded_slugs(root: Path, data: dict[str, Any] | None = None) -> list[str]:
    uploads = data if data is not None else load_uploads(root)
    known = videos_by_slug(uploads)
    return [slug for slug in published_slugs(root) if is_uploaded(known.get(slug))]


def ensure_uploads_json(root: Path, extra: list[str] | None = None) -> dict[str, Any]:
    """Keep a committed row per published /c/ slug. Never drop a known id."""
    data = load_uploads(root)
    known = videos_by_slug(data)
    slugs = list(dict.fromkeys([*published_slugs(root), *(extra or [])]))
    videos: list[dict[str, Any]] = []
    for slug in slugs:
        row = dict(known.get(slug) or {"slug": slug})
        row["slug"] = slug
        video_id = parse_youtube_id(str(row.get("youtube_id") or ""))
        if video_id:
            row["youtube_id"] = video_id
        else:
            row.pop("youtube_id", None)
            row.pop("uploaded_at", None)
        videos.append(row)
    for slug, row in known.items():
        if slug not in slugs and is_uploaded(row):
            videos.append(dict(row))
    data["videos"] = videos
    data["channel"] = CHANNEL_HANDLE
    data["channel_id"] = CHANNEL_ID
    data["intro"] = {"youtube_id": INTRO_YOUTUBE_ID, "note": INTRO_NOTE}
    save_uploads(root, data)
    return data


def write_needs_upload_zip(root: Path, slugs: list[str] | None = None) -> Path | None:
    """Zip pending /c/ mp4s only. Already-posted films stay out."""
    uploads = load_uploads(root)
    wanted = slugs if slugs is not None else pending_slugs(root, uploads)
    media = Path(root) / "media"
    dest = media / NEEDS_UPLOAD_ZIP
    videos: list[Path] = []
    for slug in wanted:
        video = media / f"{slug}.mp4"
        if video.is_file():
            videos.append(video)
    if not videos:
        if dest.exists():
            dest.unlink()
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
        for video in videos:
            archive.write(video, arcname=short_download_name(video.stem))
    tmp.replace(dest)
    return dest


def parse_channel_feed(xml_text: str) -> list[dict[str, str]]:
    """Public Atom entries: youtube_id, title, published, description, link."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    entries: list[dict[str, str]] = []
    for node in root.findall(f"{_ATOM}entry"):
        video_id = (node.findtext(f"{_YT}videoId") or "").strip()
        title = (node.findtext(f"{_ATOM}title") or "").strip()
        published = (node.findtext(f"{_ATOM}published") or "").strip()
        description = ""
        media_group = node.find("{http://search.yahoo.com/mrss/}group")
        if media_group is not None:
            desc_node = media_group.find("{http://search.yahoo.com/mrss/}description")
            if desc_node is not None and desc_node.text:
                description = desc_node.text
        link = ""
        for child in node.findall(f"{_ATOM}link"):
            href = child.attrib.get("href") or ""
            if href:
                link = href
                break
        if video_id:
            entries.append(
                {
                    "youtube_id": video_id,
                    "title": title,
                    "published": published,
                    "description": description,
                    "link": link,
                }
            )
    return entries


def _title_key(text: str) -> str:
    return " ".join((text or "").casefold().split())


def match_feed_to_films(
    entries: list[dict[str, str]],
    films: list[tuple[str, str]],
) -> dict[str, dict[str, str]]:
    """Map slug → {youtube_id, uploaded_at} only when the match is unique.

    `films` is (slug, clue line). Title must equal our Short title, or the
    description must contain that slug's /c/ URL. Ambiguous hits are dropped.
    The intro id is never assigned unless it uniquely matches a published film.
    """
    by_title: dict[str, list[str]] = {}
    for slug, clue_line in films:
        title = _title_key(video_title_from_line(clue_line))
        by_title.setdefault(title, []).append(slug)
    slugs = {slug for slug, _clue in films}

    claimed: dict[str, list[str]] = {}
    for entry in entries:
        video_id = parse_youtube_id(entry.get("youtube_id"))
        if not video_id:
            continue
        hits: list[str] = []
        for match in _SLUG_IN_TEXT.findall(entry.get("description") or ""):
            if match in slugs and match not in hits:
                hits.append(match)
        title_hits = by_title.get(_title_key(entry.get("title") or ""), [])
        if len(title_hits) == 1 and title_hits[0] not in hits:
            hits.append(title_hits[0])
        if video_id == INTRO_YOUTUBE_ID and not hits:
            continue
        if len(hits) != 1:
            continue
        claimed.setdefault(hits[0], []).append(video_id)

    matched: dict[str, dict[str, str]] = {}
    used_ids: set[str] = set()
    for slug, ids in claimed.items():
        unique = list(dict.fromkeys(ids))
        if len(unique) != 1:
            continue
        video_id = unique[0]
        if video_id in used_ids:
            continue
        used_ids.add(video_id)
        uploaded_at = ""
        for entry in entries:
            if entry.get("youtube_id") == video_id:
                uploaded_at = (entry.get("published") or "")[:10]
                break
        row = {"youtube_id": video_id}
        if uploaded_at:
            row["uploaded_at"] = uploaded_at
        matched[slug] = row
    return matched


def apply_feed_matches(root: Path, entries: list[dict[str, str]], films: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    """Persist unique feed matches onto youtube-uploads.json. Never guess."""
    data = ensure_uploads_json(root, extra=[slug for slug, _ in films])
    matches = match_feed_to_films(entries, films)
    if not matches:
        return {}
    known = videos_by_slug(data)
    applied: dict[str, dict[str, str]] = {}
    for slug, match in matches.items():
        row = known.setdefault(slug, {"slug": slug})
        if is_uploaded(row):
            continue
        row["slug"] = slug
        row["youtube_id"] = match["youtube_id"]
        if match.get("uploaded_at"):
            row["uploaded_at"] = match["uploaded_at"]
        applied[slug] = match
    if applied:
        data["videos"] = list(known.values())
        save_uploads(root, data)
    return applied


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()
