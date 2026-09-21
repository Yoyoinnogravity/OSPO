from __future__ import annotations

import json
from pathlib import Path

from twodown.config import SITE_ROOT
from twodown.models import DailyPair

LEDGER_NAME = "uploads.json"


def ledger_path(site_root: Path | None = None) -> Path:
    return Path(site_root or SITE_ROOT) / LEDGER_NAME


def load_ledger(site_root: Path | None = None) -> dict[str, dict[str, str]]:
    path = ledger_path(site_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    platforms: dict[str, dict[str, str]] = {}
    for name, mapping in data.items():
        if isinstance(mapping, dict):
            platforms[str(name)] = {str(slug): str(video_id) for slug, video_id in mapping.items() if video_id}
    return platforms


def save_ledger(ledger: dict[str, dict[str, str]], site_root: Path | None = None) -> Path:
    path = ledger_path(site_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def apply_ledger(pair: DailyPair, site_root: Path | None = None) -> DailyPair:
    """Fill in already-uploaded YouTube ids so a later run does not post twice."""
    youtube = load_ledger(site_root).get("youtube") or {}
    for item in pair.clues:
        if not item.youtube_id:
            item.youtube_id = youtube.get(item.clue.slug)
    pair.youtube_ids = [item.youtube_id for item in pair.clues if item.youtube_id]
    return pair


def record_youtube(pair: DailyPair, site_root: Path | None = None) -> bool:
    """Remember YouTube ids on the static site so GitHub Actions stays idempotent."""
    ledger = load_ledger(site_root)
    youtube = dict(ledger.get("youtube") or {})
    changed = False
    for item in pair.clues:
        if item.youtube_id and youtube.get(item.clue.slug) != item.youtube_id:
            youtube[item.clue.slug] = item.youtube_id
            changed = True
    if not changed:
        return False
    ledger["youtube"] = youtube
    save_ledger(ledger, site_root)
    return True
