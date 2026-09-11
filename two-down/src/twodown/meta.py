from __future__ import annotations

import json
import os
import time
from pathlib import Path

GRAPH_VERSION = "v22.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TOKEN_ENV = "TWODOWN_META_TOKEN"
PAGE_ENV = "TWODOWN_FB_PAGE_ID"
IG_ENV = "TWODOWN_IG_USER_ID"
ACCESS_ENV = "TWODOWN_META_ACCESS_TOKEN"


def _token_path() -> Path | None:
    raw = os.environ.get(TOKEN_ENV)
    if raw:
        return Path(raw)
    default = Path.home() / ".config" / "twodown" / "meta-token.json"
    if default.exists():
        return default
    return None


def _load_meta() -> dict[str, str]:
    data: dict[str, str] = {}
    path = _token_path()
    if path and path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text.startswith("{"):
            raw = json.loads(text)
            for key in ("access_token", "token", "page_id", "ig_user_id"):
                if raw.get(key):
                    data[key] = str(raw[key])
            if "access_token" not in data and raw.get("page_access_token"):
                data["access_token"] = str(raw["page_access_token"])
        elif text:
            data["access_token"] = text
    if os.environ.get(ACCESS_ENV):
        data["access_token"] = os.environ[ACCESS_ENV]
    if os.environ.get(PAGE_ENV):
        data["page_id"] = os.environ[PAGE_ENV]
    if os.environ.get(IG_ENV):
        data["ig_user_id"] = os.environ[IG_ENV]
    return data


def facebook_ready() -> bool:
    meta = _load_meta()
    return bool(meta.get("access_token") and meta.get("page_id"))


def instagram_ready() -> bool:
    meta = _load_meta()
    return bool(meta.get("access_token") and meta.get("ig_user_id"))


def _raise_graph(payload: dict, what: str) -> None:
    if "error" in payload:
        err = payload["error"]
        raise RuntimeError(f"{what}: {err.get('message') or err}")


def _wait_instagram_container(session, token: str, container_id: str, attempts: int = 24) -> None:
    url = f"{GRAPH}/{container_id}"
    for _ in range(attempts):
        response = session.get(
            url,
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        _raise_graph(payload, "Instagram status")
        code = (payload.get("status_code") or "").upper()
        if code == "FINISHED":
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container {code}: {payload}")
        time.sleep(2)
    raise RuntimeError("Instagram container did not finish processing")


def upload_instagram(item, caption: str, session=None) -> str | None:
    """Publish a Reel to the linked Instagram professional account."""
    if not item.video_path:
        return None
    meta = _load_meta()
    token = meta.get("access_token")
    ig_user = meta.get("ig_user_id")
    if not token or not ig_user:
        return None
    import requests

    path = Path(item.video_path)
    http = session or requests.Session()
    create = http.post(
        f"{GRAPH}/{ig_user}/media",
        data={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=30,
    )
    create.raise_for_status()
    created = create.json()
    _raise_graph(created, "Instagram container")
    container_id = created.get("id")
    uri = created.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{container_id}"
    blob = path.read_bytes()
    put = http.post(
        uri,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(len(blob)),
            "Content-Type": "application/octet-stream",
        },
        data=blob,
        timeout=120,
    )
    put.raise_for_status()
    _wait_instagram_container(http, token, str(container_id))
    publish = http.post(
        f"{GRAPH}/{ig_user}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    publish.raise_for_status()
    published = publish.json()
    _raise_graph(published, "Instagram publish")
    media_id = published.get("id")
    item.instagram_id = str(media_id) if media_id else None
    return item.instagram_id


def upload_facebook(item, caption: str, title: str, session=None) -> str | None:
    """Publish a Reel to the linked Facebook Page."""
    if not item.video_path:
        return None
    meta = _load_meta()
    token = meta.get("access_token")
    page_id = meta.get("page_id")
    if not token or not page_id:
        return None
    import requests

    path = Path(item.video_path)
    http = session or requests.Session()
    start = http.post(
        f"{GRAPH}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": token},
        timeout=30,
    )
    start.raise_for_status()
    started = start.json()
    _raise_graph(started, "Facebook reel start")
    video_id = started.get("video_id")
    upload_url = started.get("upload_url") or f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}/{video_id}"
    blob = path.read_bytes()
    put = http.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(len(blob)),
            "Content-Type": "application/octet-stream",
        },
        data=blob,
        timeout=120,
    )
    put.raise_for_status()
    finish = http.post(
        f"{GRAPH}/{page_id}/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "title": title,
            "access_token": token,
        },
        timeout=30,
    )
    finish.raise_for_status()
    finished = finish.json()
    _raise_graph(finished, "Facebook reel finish")
    item.facebook_id = str(video_id) if video_id else None
    return item.facebook_id
