from __future__ import annotations

import json
import os
from pathlib import Path

from twodown.tokens import secret_text

TOKEN_ENV = "TWODOWN_TIKTOK_TOKEN"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
CREATOR_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
PREFERRED_PRIVACY = "PUBLIC_TO_EVERYONE"
WHOLE_FILE_LIMIT = 10 * 1024 * 1024


def _load_token() -> str | None:
    text = secret_text(TOKEN_ENV, "tiktok-token.json")
    if not text:
        return None
    if text.startswith("{"):
        data = json.loads(text)
        token = data.get("access_token") or data.get("token")
        return str(token) if token else None
    return text


def tiktok_ready() -> bool:
    return bool(_load_token())


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _api_error(payload: dict) -> str | None:
    error = payload.get("error") or {}
    if not error:
        return None
    code = error.get("code") or error.get("error_code")
    if code in (None, 0, "ok"):
        return None
    return str(error.get("message") or error.get("code") or payload)


def _privacy_level(session, token: str) -> str:
    response = session.post(CREATOR_URL, headers=_headers(token), json={}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    err = _api_error(payload)
    if err:
        return "SELF_ONLY"
    options = payload.get("data", {}).get("privacy_level_options") or []
    if PREFERRED_PRIVACY in options:
        return PREFERRED_PRIVACY
    return str(options[0]) if options else "SELF_ONLY"


def _chunk_plan(size: int) -> tuple[int, int]:
    if size <= WHOLE_FILE_LIMIT:
        return size, 1
    chunk = WHOLE_FILE_LIMIT
    count = (size + chunk - 1) // chunk
    return chunk, count


def upload_short(item, caption: str, session=None) -> str | None:
    """Direct-post one Short via TikTok Content Posting API. Returns publish or post id."""
    if not item.video_path:
        return None
    token = _load_token()
    if not token:
        return None
    import requests

    path = Path(item.video_path)
    size = path.stat().st_size
    chunk_size, chunk_count = _chunk_plan(size)
    http = session or requests.Session()
    privacy = _privacy_level(http, token)
    init = http.post(
        INIT_URL,
        headers=_headers(token),
        json={
            "post_info": {
                "title": caption[:2200],
                "privacy_level": privacy,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunk_count,
            },
        },
        timeout=30,
    )
    init.raise_for_status()
    payload = init.json()
    err = _api_error(payload)
    if err:
        raise RuntimeError(f"TikTok init failed: {err}")
    data = payload.get("data") or {}
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
    if not upload_url:
        raise RuntimeError(f"TikTok init returned no upload_url: {payload}")
    with path.open("rb") as fh:
        sent = 0
        for _ in range(chunk_count):
            blob = fh.read(chunk_size)
            if not blob:
                break
            end = sent + len(blob) - 1
            put = http.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(blob)),
                    "Content-Range": f"bytes {sent}-{end}/{size}",
                },
                data=blob,
                timeout=120,
            )
            put.raise_for_status()
            sent += len(blob)
    status = http.post(
        STATUS_URL,
        headers=_headers(token),
        json={"publish_id": publish_id},
        timeout=30,
    )
    status.raise_for_status()
    status_payload = status.json()
    public_ids = (status_payload.get("data") or {}).get("publicaly_available_post_id") or []
    video_id = str(public_ids[0]) if public_ids else str(publish_id or "")
    item.tiktok_id = video_id or None
    return item.tiktok_id
