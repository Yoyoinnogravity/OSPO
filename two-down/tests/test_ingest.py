from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests

from twodown.config import SOURCE_HOST, SOURCE_SITE, WP_POSTS
from twodown.ingest import (
    LONDON,
    canonical_source_url,
    fetch_daily_posts,
    homepage_daily_urls,
    is_fifteensquared,
)
from twodown.models import PuzzlePost
from twodown.parse import parse_post

FIXTURES = Path(__file__).parent / "fixtures"


def test_source_is_fifteensquared_homepage():
    assert SOURCE_SITE == "https://fifteensquared.net/"
    assert SOURCE_HOST == "fifteensquared.net"
    assert WP_POSTS.startswith(SOURCE_SITE.rstrip("/"))


def test_is_fifteensquared_accepts_www_and_rejects_other_hosts():
    assert is_fifteensquared("https://fifteensquared.net/2026/09/11/independent-12458-phi/")
    assert is_fifteensquared("https://www.fifteensquared.net/foo")
    assert is_fifteensquared("http://fifteensquared.net/foo")
    assert not is_fifteensquared("https://timesforthetimes.co.uk/foo")
    assert not is_fifteensquared("https://puzzles.independent.co.uk/games/")
    assert not is_fifteensquared("https://www.ft.com/crossword")
    assert not is_fifteensquared("")
    assert not is_fifteensquared(None)


def test_canonical_source_url():
    assert (
        canonical_source_url("https://www.fifteensquared.net/2026/09/11/independent-12458-phi")
        == "https://fifteensquared.net/2026/09/11/independent-12458-phi/"
    )
    assert canonical_source_url("https://timesforthetimes.co.uk/x") is None


def test_homepage_daily_urls_from_fifteen_squared_html():
    html = (FIXTURES / "homepage.html").read_text(encoding="utf-8")
    urls = homepage_daily_urls(html)
    assert urls == [
        "https://fifteensquared.net/2026/09/11/independent-12458-phi/",
        "https://fifteensquared.net/2026/09/11/financial-times-18477-by-neo/",
        "https://fifteensquared.net/2026/09/10/guardian-cryptic-crossword-no-30108-by-paul/",
        "https://fifteensquared.net/2026/09/10/independent-12457-by-tack/",
    ]
    assert all(u.startswith(SOURCE_SITE) for u in urls)
    assert not any("independent.co.uk" in u for u in urls)
    assert not any("timesforthetimes" in u for u in urls)
    assert not any("/category/" in u for u in urls)


def test_parse_post_ignores_non_fifteen_squared_urls():
    html = (FIXTURES / "independent_detail.html").read_text(encoding="utf-8")
    post = PuzzlePost(
        post_id=1,
        url="https://timesforthetimes.co.uk/example/",
        title="Independent 12458 / Phi",
        date=datetime(2026, 9, 11, 7, 0, tzinfo=LONDON),
        paper="Independent",
        puzzle_id="12458",
        setter="Phi",
        blogger="someone",
        category_slugs=["independent"],
        html=html,
    )
    assert parse_post(post) == []


def _wp_item(post_id: int, link: str, title: str, cats: list[str]) -> dict:
    return {
        "id": post_id,
        "link": link,
        "date": "2026-09-11T07:00:00",
        "title": {"rendered": title},
        "content": {"rendered": "<p>x</p>"},
        "_embedded": {
            "author": [{"name": "blogger"}],
            "wp:term": [[{"taxonomy": "category", "slug": slug} for slug in cats]],
        },
    }


class _FakeResp:
    def __init__(self, *, json_data=None, text="", status=200):
        self._json = json_data
        self.text = text
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class _FakeSession:
    def __init__(self, home: str):
        self.home = home
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, params=None, headers=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params))
        if url == WP_POSTS and params.get("slug"):
            if params["slug"] == "guardian-cryptic-crossword-no-30108-by-paul":
                return _FakeResp(
                    json_data=[
                        _wp_item(
                            3,
                            "https://fifteensquared.net/2026/09/10/guardian-cryptic-crossword-no-30108-by-paul/",
                            "Guardian Cryptic crossword No 30,108 by Paul",
                            ["guardian"],
                        )
                    ]
                )
            return _FakeResp(json_data=[])
        if url == WP_POSTS:
            return _FakeResp(
                json_data=[
                    _wp_item(
                        1,
                        "https://fifteensquared.net/2026/09/11/independent-12458-phi/",
                        "Independent 12458 / Phi",
                        ["independent"],
                    ),
                    _wp_item(
                        99,
                        "https://timesforthetimes.co.uk/times-29000/",
                        "Times 29000 / A",
                        ["times"],
                    ),
                    _wp_item(
                        2,
                        "https://www.fifteensquared.net/2026/09/11/financial-times-18477-by-neo/",
                        "Financial Times 18477 by NEO",
                        ["ft"],
                    ),
                ]
            )
        if url == SOURCE_SITE:
            return _FakeResp(text=self.home)
        raise AssertionError(f"unexpected GET {url} {params}")


@patch("twodown.ingest.time.sleep")
def test_fetch_daily_posts_uses_homepage_and_drops_other_hosts(_sleep):
    home = (FIXTURES / "homepage.html").read_text(encoding="utf-8")
    session = _FakeSession(home)
    posts = fetch_daily_posts(session=session)
    urls = [p.url for p in posts]
    assert "https://fifteensquared.net/2026/09/11/independent-12458-phi/" in urls
    assert "https://fifteensquared.net/2026/09/11/financial-times-18477-by-neo/" in urls
    assert "https://fifteensquared.net/2026/09/10/guardian-cryptic-crossword-no-30108-by-paul/" in urls
    assert all(is_fifteensquared(url) for url in urls)
    assert not any("timesforthetimes" in url for url in urls)
    assert any(call[0] == WP_POSTS and call[1].get("slug") for call in session.calls)
    assert any(call[0] == SOURCE_SITE for call in session.calls)
