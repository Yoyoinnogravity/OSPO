"""YouTube channel banner for cryptic.fit.

Upload size is 2560×1440, YouTube's recommended canvas. The minimum they
accept is 2048×1152. Phones only keep the centre 1546×423, so the name
and Cryptic Croc sit inside that band. The newsprint runs to the edges
for desktop and TV.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from twodown.config import (
    BRAND,
    CRIMSON,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    INK,
    MUTED,
    NEWS_BG,
    NEWS_GRID,
)
from twodown.croc import croc_sprite

BANNER_SIZE = (2560, 1440)
# Centre region YouTube keeps on every device, scaled to this canvas.
SAFE_SIZE = (1546, 423)
MAX_BYTES = 6_000_000


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _safe_box(width: int, height: int) -> tuple[int, int, int, int]:
    safe_w, safe_h = SAFE_SIZE
    left = (width - safe_w) // 2
    top = (height - safe_h) // 2
    return left, top, left + safe_w, top + safe_h


def write_youtube_banner(dest: Path) -> Path:
    """Draw the channel banner and save a PNG under YouTube's 6 MB limit."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    width, height = BANNER_SIZE
    img = Image.new("RGB", (width, height), NEWS_BG)
    draw = ImageDraw.Draw(img)
    for x in range(0, width, 64):
        draw.line([(x, 0), (x, height)], fill=NEWS_GRID, width=1)
    for y in range(0, height, 64):
        draw.line([(0, y), (width, y)], fill=NEWS_GRID, width=1)
    draw.rectangle([0, 0, width, 16], fill=CRIMSON)
    draw.rectangle([0, height - 16, width, height], fill=CRIMSON)

    left, top, right, bottom = _safe_box(width, height)
    sprite = croc_sprite("intro", 4)
    target_h = SAFE_SIZE[1] - 36
    scale = target_h / sprite.height
    sprite = sprite.resize((int(sprite.width * scale), target_h), Image.Resampling.LANCZOS)

    word = _font(FONT_SANS_BOLD, 92)
    sub = _font(FONT_REGULAR, 42)
    small = _font(FONT_SANS, 28)
    cryptic, _, tail = BRAND.partition(".")
    suffix = f".{tail}" if tail else ""
    name = "Two cryptic clues a day"
    credit = "Cryptic Croc  ·  Fifteen Squared"
    cryptic_w = draw.textlength(cryptic, font=word)
    name_w = cryptic_w + draw.textlength(suffix, font=word)
    text_w = max(name_w, draw.textlength(name, font=sub), draw.textlength(credit, font=small))
    gap = 40
    group_w = sprite.width + gap + int(text_w)
    croc_x = left + max(12, (SAFE_SIZE[0] - group_w) // 2)
    croc_y = top + (SAFE_SIZE[1] - sprite.height) // 2
    img.paste(sprite, (croc_x, croc_y), sprite)

    text_x = croc_x + sprite.width + gap
    word_y = top + 86
    draw.text((text_x, word_y), cryptic, font=word, fill=INK)
    draw.text((text_x + cryptic_w, word_y), suffix, font=word, fill=CRIMSON)
    rule_y = word_y + 116
    draw.rectangle([text_x, rule_y, text_x + 220, rule_y + 8], fill=CRIMSON)
    draw.text((text_x, rule_y + 28), name, font=sub, fill=INK)
    draw.text((text_x, rule_y + 84), credit, font=small, fill=MUTED)

    name_end = text_x + name_w
    if name_end > right - 16 or croc_x < left:
        raise ValueError("Channel name spills out of the YouTube safe area")

    img.save(dest, "PNG", optimize=True)
    if dest.stat().st_size > MAX_BYTES:
        jpeg = dest.with_suffix(".jpg")
        img.save(jpeg, "JPEG", quality=90, optimize=True)
        dest.unlink()
        return jpeg
    return dest
