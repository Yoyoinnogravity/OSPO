from __future__ import annotations

import re
import socket

import requests

from twodown.config import SITE_ORIGIN, SITE_ROOT, SOURCE_SITE

GITHUB_PAGES = "https://yoyoinnogravity.github.io/OSPO/"
PR_URL = "https://github.com/Yoyoinnogravity/OSPO/pull/42"
RDAP_URL = "https://rdap.identitydigital.services/rdap/domain/cryptic.fun"
NAMECHEAP_BUY = "https://www.namecheap.com/domains/registration/results/?domain=cryptic.fun"
GITHUB_PAGES_IPS = (
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
)
PRODUCT_CHECK_NAMES = frozenset({"cryptic.fun", "sitemap", "support", "GitHub Pages"})


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
        *_fifteen_squared_from_site(),
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


def registry_status(timeout: float = 8.0) -> tuple[str, str]:
    """Whether cryptic.fun exists in the .fun registry.

    RDAP 404 means the name is not registered. That is stronger than a missing
    A record: Chrome's DNS_PROBE_FINISHED_NXDOMAIN is the same fact.
    """
    try:
        response = requests.get(RDAP_URL, timeout=timeout)
    except requests.RequestException as exc:
        return "unknown", exc.__class__.__name__
    if response.status_code == 404:
        return "absent", "RDAP 404 — not in the .fun registry"
    if response.status_code == 200:
        return "present", "RDAP 200"
    return "unknown", f"RDAP {response.status_code}"


def dns_addresses(hostname: str = "cryptic.fun") -> tuple[str, str]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return "none", getattr(exc, "strerror", None) or str(exc)
    addrs = sorted({item[4][0] for item in infos if item[4]})
    if not addrs:
        return "none", "no address"
    return "ok", ", ".join(addrs)


def go_live_next_steps(
    *,
    registry: str,
    pages_live: bool,
    domain_live: bool,
) -> list[str]:
    """Operator steps, in order, for putting cryptic.fun on the public internet."""
    steps: list[str] = []
    if registry == "absent":
        steps.append(f"Buy cryptic.fun at Namecheap (domain only — skip hosting): {NAMECHEAP_BUY}")
        steps.append("Do not use cryptic.fit — that is a different GoDaddy name.")
    if not pages_live:
        steps.append(f"Merge {PR_URL}")
        steps.append("Repo Settings → Pages → Source: GitHub Actions")
    if registry != "absent" and not domain_live:
        steps.append("Point cryptic.fun A records at " + ", ".join(GITHUB_PAGES_IPS))
        steps.append("GitHub Pages custom domain: cryptic.fun")
    if not steps and not domain_live:
        steps.append("DNS or TLS is still catching up — wait and run twodown live again.")
    return steps
