from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "twodown"


def secret_text(env_name: str, default_filename: str) -> str | None:
    """Load a Cloud Agent secret as inline JSON/token, or as a path to a file."""
    raw = (os.environ.get(env_name) or "").strip()
    if raw:
        path = Path(raw).expanduser()
        looks_like_path = raw.startswith(("/", "~", "./")) or raw.endswith(".json")
        if looks_like_path and path.exists():
            text = path.read_text(encoding="utf-8").strip()
            return text or None
        if raw.startswith("{") or raw.startswith("["):
            return raw
        if looks_like_path:
            return None
        return raw
    default = CONFIG_DIR / default_filename
    if default.exists():
        text = default.read_text(encoding="utf-8").strip()
        return text or None
    return None
