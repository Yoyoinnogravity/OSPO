from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from twodown.config import CRAWL_GAP_SECONDS, DAILY_CATEGORY_SLUGS, USER_AGENT, WP_POSTS
from twodown.models import PuzzlePost

LONDON = ZoneInfo("Europe/London")

TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Independent\s+([\d,]+)\s*(?:/|by)\s*(.+)$", re.I), "Independent"),
    (re.compile(r"Financial Times\s+([\d,]+)\s+by\s+(.+)$", re.I), "Financial Times"),
    (re.compile(r"Guardian(?: Cryptic(?: crossword)?)?(?: No\.?)?\s*([\d,]+)\s*(?:/|:|by)\s*(.+)$", re.I), "Guardian"),
]


def parse_title(title: str) -> tuple[str, str, str]:
    raw = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
    raw = re.sub(r"\s+", " ", raw)
    for pattern, paper in TITLE_PATTERNS:
        match = pattern.search(raw)
        if match:
            puzzle_id = match.group(1).replace(",", "")
            setter = match.group(2).strip(" /")
            setter = re.sub(r"\s+", " ", setter)
            return paper, puzzle_id, setter
    return "Unknown", "", raw


def _category_slugs(post: dict) -> list[str]:
    slugs: list[str] = []
    embedded = post.get("_embedded") or {}
    for group in embedded.get("wp:term") or []:
        for term in group:
            if term.get("taxonomy") == "category" and term.get("slug"):
                slugs.append(term["slug"])
    return slugs


def _blogger(post: dict) -> str:
    embedded = post.get("_embedded") or {}
    authors = embedded.get("author") or []
    if authors:
        return str(authors[0].get("name") or "Fifteen Squared")
    return "Fifteen Squared"


def fetch_daily_posts(session: requests.Session | None = None, per_page: int = 20) -> list[PuzzlePost]:
    sess = session or requests.Session()
    response = sess.get(
        WP_POSTS,
        params={"per_page": per_page, "_embed": "1"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    time.sleep(CRAWL_GAP_SECONDS)
    posts: list[PuzzlePost] = []
    for item in response.json():
        slugs = _category_slugs(item)
        if not DAILY_CATEGORY_SLUGS.intersection(slugs):
            continue
        paper, puzzle_id, setter = parse_title(item["title"]["rendered"])
        date = datetime.fromisoformat(item["date"]).replace(tzinfo=LONDON)
        posts.append(
            PuzzlePost(
                post_id=item["id"],
                url=item["link"],
                title=html.unescape(item["title"]["rendered"]),
                date=date,
                paper=paper,
                puzzle_id=puzzle_id,
                setter=setter,
                blogger=_blogger(item),
                category_slugs=slugs,
                html=item["content"]["rendered"],
            )
        )
    return posts


def posts_for_london_date(posts: list[PuzzlePost], day: datetime | None = None) -> list[PuzzlePost]:
    target = (day or datetime.now(tz=LONDON)).astimezone(LONDON).date()
    matched = [p for p in posts if p.date.astimezone(LONDON).date() == target]
    if matched:
        return matched
    # Blogs often land the morning of publication; if today is empty, use the newest daily post date.
    if not posts:
        return []
    newest = max(p.date.astimezone(LONDON).date() for p in posts)
    return [p for p in posts if p.date.astimezone(LONDON).date() == newest]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
