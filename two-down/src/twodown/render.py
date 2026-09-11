from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from twodown.config import (
    CRIMSON,
    FONT_BOLD,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    INK,
    MUTED,
    NEWS_BG,
    NEWS_GRID,
)
from twodown.models import Clue
from twodown.script import _spoken_parse

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


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), NEWS_BG)
    draw = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 54):
        draw.line([(x, 0), (x, HEIGHT)], fill=NEWS_GRID, width=1)
    for y in range(0, HEIGHT, 54):
        draw.line([(0, y), (WIDTH, y)], fill=NEWS_GRID, width=1)
    draw.rectangle([64, 64, WIDTH - 64, 72], fill=CRIMSON)
    draw.rectangle([64, HEIGHT - 72, WIDTH - 64, HEIGHT - 64], fill=CRIMSON)
    return img, draw


def _wordmark(draw: ImageDraw.ImageDraw) -> None:
    brand = _font(FONT_SANS_BOLD, 42)
    draw.text((80, 100), "cryptic", font=brand, fill=INK)
    w = draw.textlength("cryptic", font=brand)
    draw.text((80 + w, 100), ".fun", font=brand, fill=CRIMSON)


def _meta(draw: ImageDraw.ImageDraw, clue: Clue) -> None:
    meta = _font(FONT_SANS, 28)
    draw.text((80, 168), f"{clue.paper} {clue.puzzle_id}  ·  {clue.setter}", font=meta, fill=MUTED)
    draw.text((80, 210), f"{clue.number} {clue.direction}  ·  {clue.device}", font=meta, fill=CRIMSON)


def _clue_block(draw: ImageDraw.ImageDraw, clue: Clue, y: int = 320) -> int:
    clue_font = _font(FONT_REGULAR, 56)
    body = f"{clue.clue} ({clue.enumeration})" if clue.enumeration else clue.clue
    wrapped = _wrap(draw, body, clue_font, WIDTH - 160)
    draw.multiline_text((80, y), wrapped, font=clue_font, fill=INK, spacing=18)
    box = draw.multiline_textbbox((80, y), wrapped, font=clue_font, spacing=18)
    return box[3]


def draw_clue_card(clue: Clue, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img, draw = _canvas()
    _wordmark(draw)
    _meta(draw, clue)
    _clue_block(draw, clue)
    hint = _font(FONT_SANS, 28)
    draw.text((80, HEIGHT - 180), "Have a think. Answer in a moment.", font=hint, fill=MUTED)
    img.save(dest, "PNG")
    return dest


def draw_reveal_card(clue: Clue, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img, draw = _canvas()
    _wordmark(draw)
    _meta(draw, clue)
    bottom = _clue_block(draw, clue, y=280)
    answer_font = _font(FONT_BOLD, 72)
    parse_font = _font(FONT_SANS, 26)
    answer_y = min(max(bottom + 70, 860), 1180)
    draw.text((80, answer_y), clue.answer, font=answer_font, fill=CRIMSON)
    parse = textwrap.fill(_spoken_parse(clue.parse, clue.answer), width=40)
    draw.multiline_text((80, answer_y + 110), parse[:300], font=parse_font, fill=MUTED, spacing=8)
    foot = _font(FONT_SANS, 24)
    draw.text((80, HEIGHT - 180), "Parse via Fifteen Squared", font=foot, fill=MUTED)
    img.save(dest, "PNG")
    return dest


def draw_card(clue: Clue, dest: Path) -> Path:
    return draw_reveal_card(clue, dest)


def _ffprobe_seconds(path: Path) -> float:
    ffmpeg_probe = shutil.which("ffprobe")
    if not ffmpeg_probe:
        return 24.0
    result = subprocess.run(
        [
            ffmpeg_probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 24.0


def audio_seconds(path: Path) -> float:
    return _ffprobe_seconds(path)


def render_video(
    clue_card: Path,
    reveal_card: Path,
    audio: Path,
    dest: Path,
    clue_hold: float | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    duration = _ffprobe_seconds(audio)
    if clue_hold is None:
        clue_secs = max(7.0, min(duration * 0.42, duration - 6.0))
    else:
        clue_secs = max(4.0, min(clue_hold, duration - 4.0))
    reveal_secs = max(4.0, duration - clue_secs + 0.4)
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-t",
        f"{clue_secs:.2f}",
        "-i",
        str(clue_card),
        "-loop",
        "1",
        "-t",
        f"{reveal_secs:.2f}",
        "-i",
        str(reveal_card),
        "-i",
        str(audio),
        "-filter_complex",
        "[0:v]fps=30,scale=1080:1920,setsar=1[v0];"
        "[1:v]fps=30,scale=1080:1920,setsar=1[v1];"
        "[v0][v1]concat=n=2:v=1:a=0,format=yuv420p[v]",
        "-map",
        "[v]",
        "-map",
        "2:a",
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest
