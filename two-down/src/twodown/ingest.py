from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from twodown.config import CRAWL_GAP_SECONDS, DAILY_CATEGORY_SLUGS, SOURCE_HOST, SOURCE_SITE, USER_AGENT, WP_POSTS
from twodown.models import PuzzlePost

LONDON = ZoneInfo("Europe/London")

TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"Independent\s+on\s+Sunday\s+([\d,]+)\s*(?:/|by)\s*(.+)$", re.I),
        "Independent on Sunday",
    ),
    (re.compile(r"Independent\s+([\d,]+)\s*(?:/|by)\s*(.+)$", re.I), "Independent"),
    (re.compile(r"Financial Times\s+([\d,]+)\s+by\s+(.+)$", re.I), "Financial Times"),
    (re.compile(r"Guardian(?: Cryptic(?: crossword)?)?(?: No\.?)?\s*([\d,]+)\s*(?:/|:|by)\s*(.+)$", re.I), "Guardian"),
]

DAILY_PATH = re.compile(
    r"^/\d{4}/\d{2}/\d{2}/(independent|financial-times|guardian)[-a-z0-9]*/?$",
    re.I,
)
HOMEPAGE_POST = re.compile(
    r"https?://(?:www\.)?fifteensquared\.net/\d{4}/\d{2}/\d{2}/"
    r"(?:independent|financial-times|guardian)[-a-z0-9]*/?",
    re.I,
)


def is_fifteensquared(url: str | None) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host == SOURCE_HOST


def canonical_source_url(url: str | None) -> str | None:
    """Normalize a 15² permalink, or None if it is not on fifteensquared.net."""
    if not url or not is_fifteensquared(url):
        return None
    parsed = urlparse(url.strip())
    path = (parsed.path or "/").rstrip("/") + "/"
    return f"https://{SOURCE_HOST}{path}"


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


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "text/html, application/json"}


def _post_from_wp_item(item: dict) -> PuzzlePost | None:
    url = canonical_source_url(item.get("link") or "")
    if not url:
        return None
    slugs = _category_slugs(item)
    if not DAILY_CATEGORY_SLUGS.intersection(slugs):
        return None
    paper, puzzle_id, setter = parse_title(item["title"]["rendered"])
    date = datetime.fromisoformat(item["date"]).replace(tzinfo=LONDON)
    return PuzzlePost(
        post_id=item["id"],
        url=url,
        title=html.unescape(item["title"]["rendered"]),
        date=date,
        paper=paper,
        puzzle_id=puzzle_id,
        setter=setter,
        blogger=_blogger(item),
        category_slugs=slugs,
        html=item["content"]["rendered"],
    )


def homepage_daily_urls(html_text: str) -> list[str]:
    """Independent / FT / Guardian post URLs linked from the 15² homepage."""
    hrefs: list[str] = []
    soup = BeautifulSoup(html_text, "lxml")
    for anchor in soup.find_all("a", href=True):
        hrefs.append(anchor["href"])
    for match in HOMEPAGE_POST.finditer(html_text):
        hrefs.append(match.group(0))
    found: list[str] = []
    for href in hrefs:
        raw = href.split("#", 1)[0].split("?", 1)[0].strip()
        if not raw:
            continue
        url = canonical_source_url(urljoin(SOURCE_SITE, raw))
        if not url:
            continue
        if not DAILY_PATH.match(urlparse(url).path):
            continue
        if url not in found:
            found.append(url)
    return found


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def fetch_daily_posts(session: requests.Session | None = None, per_page: int = 20) -> list[PuzzlePost]:
    """Read Independent, FT and Guardian blogs from https://fifteensquared.net/ only."""
    sess = session or requests.Session()
    posts: list[PuzzlePost] = []
    seen: set[str] = set()

    api = sess.get(
        WP_POSTS,
        params={"per_page": per_page, "_embed": "1"},
        headers=_headers(),
        timeout=30,
    )
    api.raise_for_status()
    time.sleep(CRAWL_GAP_SECONDS)
    for item in api.json():
        post = _post_from_wp_item(item)
        if post and post.url not in seen:
            seen.add(post.url)
            posts.append(post)

    extra_urls: list[str] = []
    try:
        home = sess.get(SOURCE_SITE, headers=_headers(), timeout=30)
        home.raise_for_status()
        extra_urls = homepage_daily_urls(home.text)
        time.sleep(CRAWL_GAP_SECONDS)
    except requests.RequestException:
        extra_urls = []

    for url in extra_urls:
        if url in seen:
            continue
        slug = _slug_from_url(url)
        try:
            extra = sess.get(
                WP_POSTS,
                params={"slug": slug, "_embed": "1"},
                headers=_headers(),
                timeout=30,
            )
            extra.raise_for_status()
            time.sleep(CRAWL_GAP_SECONDS)
        except requests.RequestException:
            continue
        for item in extra.json():
            post = _post_from_wp_item(item)
            if post and post.url not in seen:
                seen.add(post.url)
                posts.append(post)
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
