from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from twodown.config import BRAND, BRAND_LINE, CREDIT_LINE, SITE_HOST, SITE_ORIGIN, SOURCE_SITE, follow_profiles
from twodown.models import Clue, DailyPair

GSC_ENV = "TWODOWN_GSC_VERIFY"
SHARE_IMAGE = "/media/og.webp"
DEFAULT_DESCRIPTION = (
    f"{BRAND_LINE} {CREDIT_LINE} From Fifteen Squared. "
    "Have a go before you tap solve. Spoken parses on cryptic.fit."
)


def canonical_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path or path == "/":
        return f"{SITE_ORIGIN}/"
    return f"{SITE_ORIGIN.rstrip('/')}/{path.lstrip('/')}"


def gsc_verification() -> str | None:
    raw = (os.environ.get(GSC_ENV) or "").strip()
    return raw or None


def homepage_description(pretty_date: str) -> str:
    return (
        f"Two cryptic crossword clues for {pretty_date}, taken from Fifteen Squared. "
        "Have a go before you tap solve."
    )


def clue_share_title(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    title = f"{clue.clue}{enum} — {BRAND}"
    return title if len(title) <= 70 else f"{clue.clue[:48].rstrip()}… — {BRAND}"


def clue_description(clue: Clue) -> str:
    enum = f" ({clue.enumeration})" if clue.enumeration else ""
    return (
        f"{clue.clue}{enum} — {clue.paper} {clue.puzzle_id} by {clue.setter}. "
        "Have a go, then tap solve. Parse via Fifteen Squared."
    )


def dumps_ld(data: dict | list) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def website_ld() -> dict:
    same = [f"{SITE_ORIGIN}/", SOURCE_SITE, f"{SITE_ORIGIN}/feed.xml"]
    same.extend(url for _slug, _label, url in follow_profiles())
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": BRAND,
        "alternateName": SITE_HOST,
        "url": f"{SITE_ORIGIN}/",
        "description": DEFAULT_DESCRIPTION,
        "inLanguage": "en-GB",
        "publisher": {"@type": "Organization", "name": BRAND, "url": f"{SITE_ORIGIN}/", "sameAs": same},
        "sourceOrganization": {"@type": "Organization", "name": "Fifteen Squared", "url": SOURCE_SITE},
    }


def item_list_ld(pair: DailyPair) -> dict:
    elements = []
    for i, item in enumerate(pair.clues, start=1):
        clue = item.clue
        elements.append(
            {
                "@type": "ListItem",
                "position": i,
                "url": canonical_url(f"/c/{clue.slug}/"),
                "name": clue_share_title(clue).replace(f" — {BRAND}", ""),
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{BRAND} pair {pair.date}",
        "itemListElement": elements,
    }


def article_ld(clue: Clue, *, canonical: str, published: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": clue.clue,
        "description": clue_description(clue),
        "url": canonical,
        "datePublished": published,
        "inLanguage": "en-GB",
        "isBasedOn": clue.source_url,
        "author": {"@type": "Person", "name": clue.setter},
        "contributor": {"@type": "Person", "name": clue.blogger},
        "publisher": {"@type": "Organization", "name": BRAND, "url": f"{SITE_ORIGIN}/"},
        "about": ["Cryptic crossword", clue.paper],
    }


@dataclass
class PageSeo:
    title: str
    description: str
    path: str
    og_type: str = "website"
    json_ld: dict | list | None = None
    published: str | None = None
    extra: list[str] = field(default_factory=list)

    @property
    def canonical(self) -> str:
        return canonical_url(self.path)


def robots_txt() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {canonical_url('/sitemap.xml')}\n"


def sitemap_xml(urls: list[tuple[str, str]]) -> str:
    """urls: (loc, lastmod YYYY-MM-DD)."""
    seen: set[str] = set()
    chunks = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in urls:
        loc = canonical_url(loc)
        if loc in seen:
            continue
        seen.add(loc)
        chunks.append("  <url>")
        chunks.append(f"    <loc>{xml_escape(loc)}</loc>")
        if lastmod:
            chunks.append(f"    <lastmod>{xml_escape(lastmod)}</lastmod>")
        chunks.append("  </url>")
    chunks.append("</urlset>\n")
    return "\n".join(chunks)


def rss_xml(pair: DailyPair, pretty_date: str) -> str:
    items: list[str] = []
    day_link = canonical_url(f"/d/{pair.date}/")
    clues = " ".join(
        (f"{item.clue.clue} ({item.clue.enumeration})." if item.clue.enumeration else f"{item.clue.clue}.")
        for item in pair.clues
    )
    items.append(_rss_item(f"Today’s pair · {pretty_date}", day_link, homepage_description(pretty_date) + " " + clues, pair.date))
    for item in pair.clues:
        clue = item.clue
        link = canonical_url(f"/c/{clue.slug}/")
        items.append(_rss_item(clue_share_title(clue), link, clue_description(clue), pair.date))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        f"<title>{xml_escape(BRAND)}</title>\n"
        f"<link>{xml_escape(canonical_url('/'))}</link>\n"
        f"<description>{xml_escape(DEFAULT_DESCRIPTION)}</description>\n"
        "<language>en-GB</language>\n"
        + "".join(items)
        + "</channel>\n</rss>\n"
    )


def _rss_item(title: str, link: str, description: str, day: str) -> str:
    return (
        "<item>\n"
        f"<title>{xml_escape(title)}</title>\n"
        f"<link>{xml_escape(link)}</link>\n"
        f"<guid>{xml_escape(link)}</guid>\n"
        f"<pubDate>{_rss_date(day)}</pubDate>\n"
        f"<description>{xml_escape(description)}</description>\n"
        "</item>\n"
    )


def _rss_date(day: str) -> str:
    dt = datetime.strptime(day, "%Y-%m-%d")
    return dt.strftime("%a, %d %b %Y 09:00:00 +0000")


def collect_sitemap_urls(root: Path, pair: DailyPair) -> list[tuple[str, str]]:
    today = pair.date
    urls: list[tuple[str, str]] = [
        ("/", today),
        ("/about.html", today),
        ("/support.html", today),
        ("/post.html", today),
        ("/tiktok.html", today),
        ("/follow.html", today),
        ("/suggest.html", today),
        ("/privacy.html", today),
        (f"/d/{pair.date}/", today),
    ]
    for item in pair.clues:
        urls.append((f"/c/{item.clue.slug}/", today))
    day_root = root / "d"
    if day_root.is_dir():
        for folder in sorted(day_root.iterdir()):
            if folder.is_dir() and (folder / "index.html").exists():
                urls.append((f"/d/{folder.name}/", folder.name))
    clue_root = root / "c"
    if clue_root.is_dir():
        for folder in sorted(clue_root.iterdir()):
            if folder.is_dir() and (folder / "index.html").exists():
                urls.append((f"/c/{folder.name}/", today))
    return urls


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" fill="#b81c29"/>
  <text x="16" y="23" text-anchor="middle" font-family="Georgia, serif" font-size="18" fill="#fcf7ec">c</text>
</svg>
"""
