from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from twodown.captions import clue_line, tiktok_caption, youtube_drop_description
from twodown.config import DEFAULT_OUTPUT, LOCKED_SLUGS, SITE_ROOT
from twodown.drop import YOUTUBE_UPLOAD
from twodown.ingest import fetch_daily_posts
from twodown.models import Clue
from twodown.parse import parse_post, usable
from twodown.pipeline import render_one_short, study_clues
from twodown.youtube import video_title

PACK_LIMIT = 100
WORKERS = 1
MANIFEST_NAME = "youtube-100.json"
TITLES_NAME = "YOUTUBE-TITLES.txt"
HOW_NAME = "HOW.txt"


def collect_bomb_clues(limit: int = PACK_LIMIT, session=None) -> list[Clue]:
    """Usable Independent / FT / Guardian clues from Fifteen Squared only."""
    posts = fetch_daily_posts(session=session, per_page=20, pages=12)
    clues: list[Clue] = []
    seen: set[str] = set()
    for post in posts:
        for clue in usable(parse_post(post)):
            if clue.slug in seen:
                continue
            seen.add(clue.slug)
            clues.append(clue)
            if len(clues) >= limit:
                return clues
    for clue in study_clues().values():
        if clue.slug in seen:
            continue
        seen.add(clue.slug)
        clues.append(clue)
        if len(clues) >= limit:
            break
    return clues[:limit]


def public_record(clue: Clue, *, index: int, total: int, video: str | None) -> dict[str, str | int | None]:
    return {
        "n": index,
        "slug": clue.slug,
        "clue": clue_line(clue),
        "paper": clue.paper,
        "puzzle_id": clue.puzzle_id,
        "setter": clue.setter,
        "source_url": clue.source_url,
        "title": video_title(clue),
        "description": youtube_drop_description(clue),
        "caption": tiktok_caption(clue, index=index, total=total),
        "video": video,
    }


def existing_video(clue: Clue, *roots: Path) -> Path | None:
    names = (
        f"{clue.slug}.mp4",
        f"{clue.slug}/short.mp4",
        f"study/{clue.slug}/short.mp4",
        f"media/{clue.slug}.mp4",
    )
    search = [Path(root) for root in roots if root]
    search.extend([SITE_ROOT, SITE_ROOT / "media", DEFAULT_OUTPUT, DEFAULT_OUTPUT / "bomb"])
    seen: set[Path] = set()
    for root in search:
        for name in names:
            path = (root / name).resolve() if (root / name).exists() else root / name
            if path in seen:
                continue
            seen.add(path)
            if path.exists() and path.is_file() and path.stat().st_size > 1000:
                return path
    return None


def _locked(clue: Clue) -> bool:
    return clue.slug in LOCKED_SLUGS


def _cut_one(clue: Clue, dest: Path, rebuild: bool) -> Path | None:
    video = existing_video(clue, dest, dest / clue.slug)
    if _locked(clue):
        return video
    if video is not None and not rebuild:
        return video
    item = render_one_short(clue.slug, dest=dest, publish=False, clue=clue)
    if item.video_path:
        path = Path(item.video_path)
        if path.exists():
            return path
    return existing_video(clue, dest)


def render_bomb_videos(
    clues: list[Clue],
    *,
    dest: Path | None = None,
    rebuild: bool = False,
    workers: int = WORKERS,
) -> list[dict[str, str | int | None]]:
    """Cut a full newsprint Short for each clue. Reuse a film that is already cut."""
    slot = Path(dest or (DEFAULT_OUTPUT / "bomb"))
    slot.mkdir(parents=True, exist_ok=True)
    total = len(clues)
    records: list[dict[str, str | int | None] | None] = [None] * total

    def work(index: int, clue: Clue) -> tuple[int, dict[str, str | int | None]]:
        try:
            video = _cut_one(clue, slot, rebuild)
        except Exception as exc:
            print(f"bomb {index}/{total} fail {clue.slug}: {exc}", flush=True)
            video = existing_video(clue, slot)
        rel = str(video) if video else None
        print(f"bomb {index}/{total} {'ok' if video else 'miss'} {clue.slug}", flush=True)
        return index, public_record(clue, index=index, total=total, video=rel)

    if workers <= 1 or total <= 1:
        for index, clue in enumerate(clues, start=1):
            _, row = work(index, clue)
            records[index - 1] = row
        return [row for row in records if row is not None]

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(work, index, clue) for index, clue in enumerate(clues, start=1)]
        for future in as_completed(futures):
            index, row = future.result()
            records[index - 1] = row
    return [row for row in records if row is not None]


def how_to_bomb() -> str:
    return f"{YOUTUBE_UPLOAD}\n\nDrag every mp4.\n"


def write_bomb_manifest(records: list[dict[str, str | int | None]], root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / MANIFEST_NAME
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"{row['n']:03d}\t{row['title']}" for row in records]
    (root / TITLES_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / HOW_NAME).write_text(how_to_bomb(), encoding="utf-8")
    return path


def write_bomb_zip(records: list[dict[str, str | int | None]], dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(dest, "w", ZIP_DEFLATED) as zf:
        zf.writestr(HOW_NAME, how_to_bomb())
        titles = [f"{row['n']:03d}\t{row['title']}" for row in records]
        zf.writestr(TITLES_NAME, "\n".join(titles) + "\n")
        zf.writestr(MANIFEST_NAME, json.dumps(records, indent=2, ensure_ascii=False) + "\n")
        for row in records:
            video = row.get("video")
            if not video:
                continue
            path = Path(str(video))
            if not path.exists():
                continue
            stem = f"{int(row['n']):03d}-{row['slug']}"
            zf.write(path, f"{stem}.mp4")
            text = f"{row['title']}\n\n{row['description']}\n"
            zf.writestr(f"{stem}.txt", text)
    return dest


def run_bomb(
    *,
    limit: int = PACK_LIMIT,
    dest: Path | None = None,
    zip_path: Path | None = None,
    rebuild: bool = False,
    workers: int = WORKERS,
    session=None,
) -> tuple[Path, list[dict[str, str | int | None]]]:
    clues = collect_bomb_clues(limit=limit, session=session)
    slot = Path(dest or (DEFAULT_OUTPUT / "bomb"))
    records = render_bomb_videos(clues, dest=slot, rebuild=rebuild, workers=workers)
    write_bomb_manifest(records, slot)
    packed = write_bomb_zip(records, Path(zip_path or (slot / "youtube-100.zip")))
    return packed, records
