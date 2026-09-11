from __future__ import annotations

import re

import requests

from twodown.config import SITE_ORIGIN, SITE_ROOT, SOURCE_SITE

GITHUB_PAGES = "https://yoyoinnogravity.github.io/OSPO/"
PR_URL = "https://github.com/Yoyoinnogravity/OSPO/pull/42"


def _fifteen_squared_from_site() -> list[tuple[str, str]]:
    found: list[str] = []
    index = SITE_ROOT / "index.html"
    if index.exists():
        for url in re.findall(r"https://fifteensquared\.net/[^\"\s<]+", index.read_text(encoding="utf-8")):
            if url.rstrip("/") not in [u.rstrip("/") for u in found]:
                found.append(url)
    if not found:
        return [("Fifteen Squared", SOURCE_SITE)]
    return [(f"15² {i}", url) for i, url in enumerate(found, start=1)]


def public_checks() -> list[tuple[str, str]]:
    checks = [
        ("cryptic.fun", f"{SITE_ORIGIN}/"),
        ("sitemap", f"{SITE_ORIGIN}/sitemap.xml"),
        ("support", f"{SITE_ORIGIN}/support.html"),
        ("GitHub Pages", GITHUB_PAGES),
        * _fifteen_squared_from_site(),
        ("Pull request", PR_URL),
    ]
    return checks


def probe(url: str, timeout: float = 8.0) -> tuple[str, str]:
    """Return (state, detail) e.g. ('live', '200') or ('down', 'no DNS')."""
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return "live", str(response.status_code)
        return "down", str(response.status_code)
    except requests.exceptions.SSLError:
        return "down", "tls error"
    except requests.exceptions.ConnectionError:
        return "down", "no DNS or connection"
    except requests.RequestException as exc:
        return "down", exc.__class__.__name__
