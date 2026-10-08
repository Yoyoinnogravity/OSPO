from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import requests

from twodown.config import SITE_ORIGIN, TAGLINE, USER_AGENT

UPLOADS_NAME = "youtube-uploads.json"
LEGACY_NEEDS_UPLOAD_ZIP = "crypticfit-needs-upload.zip"
NEEDS_UPLOAD_ZIP_PREFIX = "crypticfit-needs-upload"
# GitHub rejects blobs over 100MB. Stay well under 90MB so Pages can
# serve real zip bytes instead of a Git LFS pointer.
MAX_NEEDS_UPLOAD_ZIP_BYTES = 80 * 1024 * 1024
ZIP_ENTRY_OVERHEAD = 128
NEEDS_UPLOAD_ZIP_HELP = (
    "Unzip each file, then drag the mp4s from your Downloads folder onto YouTube Studio. "
    "Do not drop the zip. You cannot drag from this page."
)
YOUTUBE_STUDIO_UPLOAD = "https://www.youtube.com/upload"
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
YOUTUBE_CONFIRMATIONS_ID = "youtube-confirmations"
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ATOM = "{http://www.w3.org/2005/Atom}"
_YT = "{http://www.youtube.com/xml/schemas/2015}"
_SLUG_IN_TEXT = re.compile(r"/c/([a-z0-9-]+)/?", re.I)
_SLUG_WORD = re.compile(r"[a-z0-9]+")
_BRAND_SLUG_PREFIXES = ("crypticfit-", "cryptic-fit-")


def studio_description() -> str:
    """Spoiler-free YouTube description paste. Never the answer."""
    return f"{TAGLINE}\n{SITE_ORIGIN}"


def studio_confirmations_html() -> str:
    """One card of honest Studio answers for every cryptic.fit Short."""
    desc = studio_description()
    return f"""    <article class="panel youtube-confirmations" id="{YOUTUBE_CONFIRMATIONS_ID}">
      <p class="kicker">YouTube confirmations</p>
      <h2>Same answers every Short.</h2>
      <p>These are AI-generated cryptic shorts for adults. Click Studio identically each time. We do not bot the dialogs.</p>
      <dl>
        <div><dt>Made for kids</dt><dd>No</dd></div>
        <div><dt>Age-restricted</dt><dd>No</dd></div>
        <div><dt>Paid promotion / sponsorship</dt><dd>No</dd></div>
        <div><dt>Altered / synthetic / AI-generated</dt><dd>Yes — disclose</dd></div>
        <div><dt>Language</dt><dd>English</dd></div>
        <div><dt>Category</dt><dd>Education</dd></div>
        <div><dt>Visibility</dt><dd>Public</dd></div>
        <div><dt>Movie / licensed music we do not own</dt><dd>No</dd></div>
        <div><dt>Title</dt><dd>Clue + #Shorts, never the answer</dd></div>
        <div><dt>Description</dt><dd><pre>{desc}</pre></dd></div>
      </dl>
      <p class="youtube-help">Studio still needs a click. Daily upload quota still applies.</p>
    </article>"""


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


def record_youtube_upload(
    root: Path,
    slug: str,
    youtube_id: str,
    uploaded_at: str | None = None,
) -> bool:
    """Store one Short's id. A different id already on the slug is left alone."""
    video_id = parse_youtube_id(youtube_id)
    slug = (slug or "").strip()
    if not video_id or not slug:
        return False
    data = ensure_uploads_json(root, extra=[slug])
    known = videos_by_slug(data)
    row = known.setdefault(slug, {"slug": slug})
    current = committed_youtube_id(row)
    if current:
        return False
    row["slug"] = slug
    row["youtube_id"] = video_id
    row["uploaded_at"] = (uploaded_at or datetime.now(timezone.utc).date().isoformat())[:10]
    data["videos"] = list(known.values())
    save_uploads(root, data)
    return True


def fetch_channel_feed(session: requests.Session | None = None) -> list[dict[str, str]]:
    """Public @crypticfit uploads. Used so a second run does not post the same Short."""
    sess = session or requests.Session()
    response = sess.get(
        CHANNEL_FEED_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"},
        timeout=30,
    )
    response.raise_for_status()
    return parse_channel_feed(response.text)


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


def needs_upload_zip_name(part: int) -> str:
    return f"{NEEDS_UPLOAD_ZIP_PREFIX}-{part}.zip"


def pending_video_files(root: Path, slugs: list[str] | None = None) -> list[Path]:
    """Published /c/ mp4s that still need a YouTube id. No study orphans."""
    uploads = load_uploads(root)
    wanted = slugs if slugs is not None else pending_slugs(root, uploads)
    media = Path(root) / "media"
    videos: list[Path] = []
    for slug in wanted:
        video = media / f"{slug}.mp4"
        if video.is_file():
            videos.append(video)
    return videos


def plan_needs_upload_parts(
    videos: list[Path],
    max_bytes: int = MAX_NEEDS_UPLOAD_ZIP_BYTES,
) -> list[list[Path]]:
    """Pack pending mp4s into zip parts, each well under the GitHub blob limit."""
    parts: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    limit = max(1, max_bytes)
    for video in videos:
        size = video.stat().st_size + ZIP_ENTRY_OVERHEAD
        if current and current_size + size > limit:
            parts.append(current)
            current = []
            current_size = 0
        current.append(video)
        current_size += size
    if current:
        parts.append(current)
    return parts


def needs_upload_zip_names(
    root: Path,
    slugs: list[str] | None = None,
    max_bytes: int = MAX_NEEDS_UPLOAD_ZIP_BYTES,
) -> list[str]:
    videos = pending_video_files(root, slugs)
    if not videos:
        return []
    return [needs_upload_zip_name(index) for index, _part in enumerate(plan_needs_upload_parts(videos, max_bytes), start=1)]


def needs_upload_zip_bar_html(names: list[str]) -> str:
    """Upload page buttons: one per zip part, plus Studio."""
    if not names:
        return ""
    buttons = [
        f'<a class="action download-all" href="media/{name}" download="{name}">Download zip {index}</a>'
        for index, name in enumerate(names, start=1)
    ]
    buttons.append(
        f'<a class="action ghost" href="{YOUTUBE_STUDIO_UPLOAD}" target="_blank" rel="noopener">Open YouTube Studio</a>'
    )
    joined = "\n      ".join(buttons)
    return (
        f'    <p class="youtube-help">{NEEDS_UPLOAD_ZIP_HELP}</p>\n'
        f'    <p class="youtube-zip">\n'
        f'      {joined}\n'
        f'    </p>'
    )


_ZIP_BAR = re.compile(
    r"[ \t]*<p class=\"youtube-help\">.*?</p>\s*<p class=\"youtube-zip\">.*?</p>",
    re.S,
)


_CONFIRMATIONS = re.compile(
    r"[ \t]*<article class=\"panel youtube-confirmations\"[^>]*>.*?</article>",
    re.S,
)


def refresh_upload_confirmations(root: Path) -> None:
    """Keep the Studio answers card on upload.html."""
    page = Path(root) / "upload.html"
    if not page.is_file():
        return
    card = studio_confirmations_html()
    text = page.read_text(encoding="utf-8")
    if _CONFIRMATIONS.search(text):
        updated = _CONFIRMATIONS.sub(card, text, count=1)
    else:
        marker = '<p class="youtube-help">'
        zip_at = text.find(marker)
        if zip_at != -1:
            updated = text[:zip_at] + card + "\n    " + text[zip_at:]
        else:
            updated = text.replace(
                '<section class="staging-list" id="needs-upload">',
                f"{card}\n    \n    <section class=\"staging-list\" id=\"needs-upload\">",
                1,
            )
            if updated == text:
                return
    if updated != text:
        page.write_text(updated, encoding="utf-8")


def refresh_upload_zip_bar(root: Path) -> None:
    """Keep upload.html zip buttons in sync with the planned parts."""
    page = Path(root) / "upload.html"
    if not page.is_file():
        return
    bar = needs_upload_zip_bar_html(needs_upload_zip_names(root))
    text = page.read_text(encoding="utf-8")
    if _ZIP_BAR.search(text):
        updated = _ZIP_BAR.sub(bar, text, count=1) if bar else _ZIP_BAR.sub("", text, count=1)
    elif bar:
        updated = text.replace(
            '<section class="staging-list" id="needs-upload">',
            f"{bar}\n    \n    <section class=\"staging-list\" id=\"needs-upload\">",
            1,
        )
    else:
        updated = text
    if updated != text:
        page.write_text(updated, encoding="utf-8")
    refresh_upload_confirmations(root)


def _clear_needs_upload_zips(media: Path) -> None:
    for path in media.glob(f"{NEEDS_UPLOAD_ZIP_PREFIX}*.zip"):
        path.unlink()
    leftover = media / LEGACY_NEEDS_UPLOAD_ZIP
    if leftover.exists():
        leftover.unlink()


def write_needs_upload_zips(
    root: Path,
    slugs: list[str] | None = None,
    max_bytes: int = MAX_NEEDS_UPLOAD_ZIP_BYTES,
) -> list[Path]:
    """Zip pending /c/ mp4s only, split so each part stays under max_bytes."""
    media = Path(root) / "media"
    videos = pending_video_files(root, slugs)
    _clear_needs_upload_zips(media)
    if not videos:
        return []
    dests: list[Path] = []
    media.mkdir(parents=True, exist_ok=True)
    for index, part in enumerate(plan_needs_upload_parts(videos, max_bytes), start=1):
        dest = media / needs_upload_zip_name(index)
        tmp = dest.with_name(dest.name + ".part")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
            for video in part:
                archive.write(video, arcname=short_download_name(video.stem))
        tmp.replace(dest)
        dests.append(dest)
    return dests


def write_needs_upload_zip(root: Path, slugs: list[str] | None = None) -> Path | None:
    """Back-compat wrapper. Prefer write_needs_upload_zips."""
    written = write_needs_upload_zips(root, slugs)
    return written[0] if written else None


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


def _expected_title(clue_line: str) -> str:
    """Clue line, or a full Short title when it already ends in #Shorts."""
    text = (clue_line or "").strip()
    if text.casefold().endswith("#shorts"):
        return _title_key(text)
    from twodown.youtube import video_title_from_line

    return _title_key(video_title_from_line(text))


def _slugish(text: str) -> str:
    return "-".join(_SLUG_WORD.findall((text or "").casefold()))


def slug_from_title(title: str, slugs: set[str] | list[str]) -> str | None:
    """Published /c/ slug when the title is that slug, maybe after a brand prefix.

    Aled sometimes titles a Short like ``crypticfit financial times 18478 1a``
    instead of the clue + #Shorts line. Only an exact published slug counts.
    """
    known = set(slugs)
    key = _slugish(title)
    if not key:
        return None
    for prefix in _BRAND_SLUG_PREFIXES:
        if key.startswith(prefix) and len(key) > len(prefix):
            key = key[len(prefix) :]
            break
    return key if key in known else None


def match_feed_to_films(
    entries: list[dict[str, str]],
    films: list[tuple[str, str]],
) -> dict[str, dict[str, str]]:
    """Map slug → {youtube_id, uploaded_at} only when the match is unique.

    `films` is (slug, clue line). Title must equal our Short title, name the
    published /c/ slug uniquely, or the description must contain that slug's
    /c/ URL. Ambiguous hits are dropped. The intro id is never assigned unless
    it uniquely matches a published film.
    """
    by_title: dict[str, list[str]] = {}
    for slug, clue_line in films:
        title = _expected_title(clue_line)
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
        slug_hit = slug_from_title(entry.get("title") or "", slugs)
        if slug_hit and slug_hit not in hits:
            hits.append(slug_hit)
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
