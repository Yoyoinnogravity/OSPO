from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from twodown.config import (
    CARD_BG,
    CARD_CREAM,
    CARD_GOLD,
    CARD_MUTED,
    FONT_BOLD,
    FONT_REGULAR,
    FONT_SANS,
)
from twodown.models import Clue

WIDTH, HEIGHT = 1080, 1920


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if draw.textlength(trial, font=font) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def draw_card(clue: Clue, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (WIDTH, HEIGHT), CARD_BG)
    draw = ImageDraw.Draw(img)
    title = _font(FONT_SANS, 36)
    clue_font = _font(FONT_REGULAR, 52)
    answer_font = _font(FONT_BOLD, 64)
    meta = _font(FONT_SANS, 28)
    small = _font(FONT_SANS, 24)

    draw.text((80, 90), "TWO DOWN", font=title, fill=CARD_GOLD)
    draw.text(
        (80, 150),
        f"{clue.paper} {clue.puzzle_id}  ·  {clue.setter}",
        font=meta,
        fill=CARD_MUTED,
    )
    draw.text(
        (80, 190),
        f"{clue.number} {clue.direction}  ·  {clue.device}",
        font=meta,
        fill=CARD_MUTED,
    )

    clue_body = clue.clue
    if clue.enumeration:
        clue_body = f"{clue.clue} ({clue.enumeration})"
    wrapped = _wrap(draw, clue_body, clue_font, WIDTH - 160)
    draw.multiline_text((80, 320), wrapped, font=clue_font, fill=CARD_CREAM, spacing=16)

    clue_box = draw.multiline_textbbox((80, 320), wrapped, font=clue_font, spacing=16)
    answer_y = min(max(clue_box[3] + 80, 900), 1300)
    draw.text((80, answer_y), clue.answer, font=answer_font, fill=CARD_GOLD)

    parse = textwrap.fill(clue.parse, width=42)
    draw.multiline_text((80, answer_y + 110), parse[:320], font=small, fill=CARD_MUTED, spacing=8)

    draw.text((80, HEIGHT - 140), "cryptic.fit", font=meta, fill=CARD_GOLD)
    draw.text((80, HEIGHT - 90), "Parse via Fifteen Squared", font=small, fill=CARD_MUTED)
    img.save(dest, "PNG")
    return dest


def render_video(card: Path, audio: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(card),
        "-i",
        str(audio),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-vf",
        "scale=1080:1920",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest
