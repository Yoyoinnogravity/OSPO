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
from twodown.scenes import DEFAULT_SCENE, Scene, get_scene
from twodown.script import _spoken_parse

WIDTH, HEIGHT = 1080, 1920
PHOTO_INK = (252, 247, 236)
PHOTO_MUTED = (220, 208, 190)
PHOTO_SHADOW = (8, 6, 4)


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


def _cover_crop(photo: Image.Image, size: tuple[int, int] = (WIDTH, HEIGHT)) -> Image.Image:
    width, height = size
    image = photo.convert("RGB")
    iw, ih = image.size
    scale = max(width / iw, height / ih)
    nw, nh = max(width, int(iw * scale)), max(height, int(ih * scale))
    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - width) // 2
    top = (nh - height) // 2
    return image.crop((left, top, left + width, top + height))


def _gradient_band(size: tuple[int, int], top: bool, depth: int, max_alpha: int) -> Image.Image:
    width, height = size
    ramp = Image.linear_gradient("L")
    if not top:
        ramp = ramp.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    strip = ramp.resize((width, depth), Image.Resampling.BILINEAR)
    alpha = Image.new("L", (width, height), 0)
    alpha.paste(strip.point(lambda p: int(p * max_alpha / 255)), (0, 0 if top else height - depth))
    overlay = Image.new("RGBA", (width, height), (10, 8, 6, 0))
    overlay.putalpha(alpha)
    return overlay


def _photo_canvas(scene: Scene) -> Image.Image:
    path = scene.path
    if path is None or not path.exists():
        img, _ = _newsprint_canvas()
        return img
    base = _cover_crop(Image.open(path)).convert("RGBA")
    dim = Image.new("RGBA", (WIDTH, HEIGHT), (12, 10, 8, 78))
    base = Image.alpha_composite(base, dim)
    base = Image.alpha_composite(base, _gradient_band((WIDTH, HEIGHT), top=True, depth=520, max_alpha=170))
    base = Image.alpha_composite(base, _gradient_band((WIDTH, HEIGHT), top=False, depth=420, max_alpha=190))
    return base.convert("RGB")


def _newsprint_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), NEWS_BG)
    draw = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 54):
        draw.line([(x, 0), (x, HEIGHT)], fill=NEWS_GRID, width=1)
    for y in range(0, HEIGHT, 54):
        draw.line([(0, y), (WIDTH, y)], fill=NEWS_GRID, width=1)
    return img, draw


def _canvas(scene: Scene) -> tuple[Image.Image, ImageDraw.ImageDraw, bool]:
    if scene.is_photo:
        img = _photo_canvas(scene)
        draw = ImageDraw.Draw(img)
        photo = True
    else:
        img, draw = _newsprint_canvas()
        photo = False
    draw.rectangle([64, 64, WIDTH - 64, 72], fill=CRIMSON)
    draw.rectangle([64, HEIGHT - 72, WIDTH - 64, HEIGHT - 64], fill=CRIMSON)
    return img, draw, photo


def _palette(photo: bool) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int] | None]:
    if photo:
        return PHOTO_INK, PHOTO_MUTED, PHOTO_SHADOW
    return INK, MUTED, None


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    shadow: tuple[int, int, int] | None = None,
) -> None:
    if shadow:
        draw.text((xy[0] + 2, xy[1] + 3), text, font=font, fill=shadow)
    draw.text(xy, text, font=font, fill=fill)


def _multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: int,
    shadow: tuple[int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    if shadow:
        draw.multiline_text((xy[0] + 2, xy[1] + 3), text, font=font, fill=shadow, spacing=spacing)
    draw.multiline_text(xy, text, font=font, fill=fill, spacing=spacing)
    return draw.multiline_textbbox(xy, text, font=font, spacing=spacing)


def _wordmark(draw: ImageDraw.ImageDraw, ink: tuple[int, int, int], shadow: tuple[int, int, int] | None) -> None:
    brand = _font(FONT_SANS_BOLD, 42)
    _text(draw, (80, 100), "cryptic", brand, ink, shadow)
    w = draw.textlength("cryptic", font=brand)
    _text(draw, (80 + int(w), 100), ".fun", brand, CRIMSON, shadow)


def _meta(
    draw: ImageDraw.ImageDraw,
    clue: Clue,
    muted: tuple[int, int, int],
    shadow: tuple[int, int, int] | None,
) -> None:
    meta = _font(FONT_SANS, 28)
    _text(draw, (80, 168), f"{clue.paper} {clue.puzzle_id}  ·  {clue.setter}", meta, muted, shadow)
    _text(draw, (80, 210), f"{clue.number} {clue.direction}  ·  {clue.device}", meta, CRIMSON, shadow)


def _clue_block(
    draw: ImageDraw.ImageDraw,
    clue: Clue,
    ink: tuple[int, int, int],
    shadow: tuple[int, int, int] | None,
    y: int = 320,
) -> int:
    clue_font = _font(FONT_REGULAR, 56)
    body = f"{clue.clue} ({clue.enumeration})" if clue.enumeration else clue.clue
    wrapped = _wrap(draw, body, clue_font, WIDTH - 160)
    box = _multiline(draw, (80, y), wrapped, clue_font, ink, 18, shadow)
    return box[3]


def _credit(draw: ImageDraw.ImageDraw, scene: Scene, muted: tuple[int, int, int], shadow: tuple[int, int, int] | None) -> None:
    foot = _font(FONT_SANS, 22)
    _text(draw, (80, HEIGHT - 118), scene.credit_line[:64], foot, muted, shadow)


def _resolve_scene(scene: str | Scene | None) -> Scene:
    if isinstance(scene, Scene):
        return scene
    return get_scene(scene or DEFAULT_SCENE)


def draw_clue_card(clue: Clue, dest: Path, scene: str | Scene | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resolved = _resolve_scene(scene)
    img, draw, photo = _canvas(resolved)
    ink, muted, shadow = _palette(photo)
    _wordmark(draw, ink, shadow)
    _meta(draw, clue, muted, shadow)
    _clue_block(draw, clue, ink, shadow)
    hint = _font(FONT_SANS, 28)
    _text(draw, (80, HEIGHT - 180), "Have a think. Answer in a moment.", hint, muted, shadow)
    _credit(draw, resolved, muted, shadow)
    img.save(dest, "PNG")
    return dest


def draw_reveal_card(clue: Clue, dest: Path, scene: str | Scene | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resolved = _resolve_scene(scene)
    img, draw, photo = _canvas(resolved)
    ink, muted, shadow = _palette(photo)
    _wordmark(draw, ink, shadow)
    _meta(draw, clue, muted, shadow)
    bottom = _clue_block(draw, clue, ink, shadow, y=280)
    answer_font = _font(FONT_BOLD, 72)
    parse_font = _font(FONT_SANS, 26)
    answer_y = min(max(bottom + 70, 860), 1180)
    _text(draw, (80, answer_y), clue.answer, answer_font, CRIMSON, shadow)
    parse = textwrap.fill(_spoken_parse(clue.parse, clue.answer), width=40)
    _multiline(draw, (80, answer_y + 110), parse[:300], parse_font, muted, 8, shadow)
    foot = _font(FONT_SANS, 24)
    _text(draw, (80, HEIGHT - 180), "Parse via Fifteen Squared", foot, muted, shadow)
    _credit(draw, resolved, muted, shadow)
    img.save(dest, "PNG")
    return dest


def draw_card(clue: Clue, dest: Path, scene: str | Scene | None = None) -> Path:
    return draw_reveal_card(clue, dest, scene=scene)


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
