"""YouTube channel art for cryptic.fit.

The banner is 2560×1440, YouTube's recommended canvas. The minimum they
accept is 2048×1152. Phones only keep the centre 1546×423, so the name
and Cryptic Croc sit inside that band. The newsprint runs to the edges
for desktop and TV.

The profile picture is an 800×800 still PNG. YouTube masks it to a circle
and shows it as small as 98 pixels, so the scarf and snout sit inside that circle.
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
    TAGLINE,
)
from twodown.croc import croc_portrait, croc_site_sprite, croc_sprite

BANNER_SIZE = (2560, 1440)
# Centre region YouTube keeps on every device, scaled to this canvas.
SAFE_SIZE = (1546, 423)
MAX_BYTES = 6_000_000
# YouTube shows the profile picture as a circle, down to 98 pixels.
PICTURE_SIZE = 800
PICTURE_MAX_BYTES = 4_000_000


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
    name = "One cryptic clue a day"
    credit = TAGLINE
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


def _center_sprite(sprite: Image.Image) -> Image.Image:
    """Square the opaque pixels so a circle crop keeps the snout and the scarf."""
    bbox = sprite.getbbox()
    if bbox is None:
        return sprite
    cropped = sprite.crop(bbox)
    side = max(cropped.size) + 8
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2), cropped)
    return square


def write_site_croc(dest: Path) -> Path:
    """Resting Cryptic Croc for the site. Transparent around her, no ring."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sprite = croc_site_sprite()
    bbox = sprite.getbbox()
    if bbox is None:
        raise ValueError("Cryptic Croc sprite is empty")
    cropped = sprite.crop(bbox)
    pad = 8
    canvas = Image.new("RGBA", (cropped.width + pad * 2, cropped.height + pad * 2), (0, 0, 0, 0))
    canvas.paste(cropped, (pad, pad), cropped)
    canvas.save(dest, "WEBP", quality=82, method=6)
    return dest


def write_youtube_picture(dest: Path, *, ring: bool = True) -> Path:
    """Square PNG for the channel picture. YouTube masks it to a circle."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = PICTURE_SIZE
    img = Image.new("RGB", (size, size), NEWS_BG)
    draw = ImageDraw.Draw(img)
    step = 28
    for x in range(0, size, step):
        draw.line([(x, 0), (x, size)], fill=NEWS_GRID, width=1)
    for y in range(0, size, step):
        draw.line([(0, y), (size, y)], fill=NEWS_GRID, width=1)

    # Quiet pose: eyes open, mouth closed. Centre the head before the circle crop.
    head = _center_sprite(croc_portrait())
    inset = 18 if ring else 10
    ring_width = 22 if ring else 0
    # Inner edge of the ring, with a gap so the scarf and snout are not cut.
    limit = size / 2 - inset - ring_width / 2 - (36 if ring else 24)
    cx = (head.width - 1) / 2
    cy = (head.height - 1) / 2
    alpha = head.getchannel("A")
    farthest = 1.0
    for y in range(head.height):
        for x in range(head.width):
            if alpha.getpixel((x, y)) == 0:
                continue
            farthest = max(farthest, ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5)
    ratio = limit / farthest
    head = head.resize(
        (max(1, int(head.width * ratio)), max(1, int(head.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    x = (size - head.width) // 2
    y = (size - head.height) // 2
    img.paste(head, (x, y), head)
    if ring:
        draw.ellipse(
            [inset, inset, size - 1 - inset, size - 1 - inset],
            outline=CRIMSON,
            width=ring_width,
        )
    img.save(dest, "PNG", optimize=True)
    if dest.stat().st_size > PICTURE_MAX_BYTES:
        raise ValueError("YouTube profile picture is over 4 MB")
    return dest
