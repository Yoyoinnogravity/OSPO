from __future__ import annotations

import json
from pathlib import Path

from twodown.bomb import (
    PACK_LIMIT,
    collect_bomb_clues,
    existing_video,
    public_record,
    render_bomb_videos,
)
from twodown.config import SITE_ROOT

collect_tiktok_clues = collect_bomb_clues
MANIFEST_NAME = "tiktok-100.json"
CAPTIONS_NAME = "tiktok-100.txt"


def render_tiktok_videos(
    clues,
    *,
    root: Path | None = None,
    dest: Path | None = None,
    rebuild: bool = False,
):
    """Cut a full newsprint Short for each clue. Reuse a film that is already cut."""
    del root
    return render_bomb_videos(clues, dest=dest, rebuild=rebuild, workers=1)


def write_tiktok_pack(records: list[dict[str, str | int | None]], root: Path | None = None) -> Path:
    site = Path(root or SITE_ROOT)
    site.mkdir(parents=True, exist_ok=True)
    path = site / MANIFEST_NAME
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    chunks = [str(row["caption"]) for row in records if row.get("caption")]
    (site / CAPTIONS_NAME).write_text("\n\n---\n\n".join(chunks) + "\n", encoding="utf-8")
    return path


def load_tiktok_pack(root: Path | None = None) -> list[dict[str, str | int | None]]:
    path = Path(root or SITE_ROOT) / MANIFEST_NAME
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "CAPTIONS_NAME",
    "MANIFEST_NAME",
    "PACK_LIMIT",
    "collect_tiktok_clues",
    "existing_video",
    "load_tiktok_pack",
    "public_record",
    "render_tiktok_videos",
    "write_tiktok_pack",
]
