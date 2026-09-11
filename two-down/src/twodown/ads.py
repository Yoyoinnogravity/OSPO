from __future__ import annotations

import os
import re

ADSENSE_CLIENT_ENV = "TWODOWN_ADSENSE_CLIENT"
ADSENSE_SLOT_ENV = "TWODOWN_ADSENSE_SLOT"
# IAB ads.txt cert for Google AdSense / AdX.
GOOGLE_ADS_TXT_CERT = "f08c47fec0942fa0"
PUB_RE = re.compile(r"^ca-pub-\d{10,22}$")
SLOT_RE = re.compile(r"^\d{8,16}$")


def adsense_client() -> str | None:
    raw = (os.environ.get(ADSENSE_CLIENT_ENV) or "").strip()
    return raw if PUB_RE.fullmatch(raw) else None


def adsense_slot() -> str | None:
    raw = (os.environ.get(ADSENSE_SLOT_ENV) or "").strip()
    return raw if SLOT_RE.fullmatch(raw) else None


def ads_enabled() -> bool:
    """True only when a real display unit is configured. Off until then."""
    return bool(adsense_client() and adsense_slot())


def ads_txt() -> str | None:
    client = adsense_client()
    if not client:
        return None
    pub = client.removeprefix("ca-")
    return f"google.com, {pub}, DIRECT, {GOOGLE_ADS_TXT_CERT}\n"


def ads_status() -> tuple[str, str]:
    if ads_enabled():
        return "ready", adsense_client() or ""
    if adsense_client() and not adsense_slot():
        return "needs slot", f"Set {ADSENSE_SLOT_ENV} to the AdSense display unit id."
    return (
        "off",
        f"Set {ADSENSE_CLIENT_ENV}=ca-pub-… and {ADSENSE_SLOT_ENV} after AdSense approves cryptic.fun.",
    )
