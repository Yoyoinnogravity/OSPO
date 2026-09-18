from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dataclasses import dataclass

from twodown.config import (
    CREAM,
    CRIMSON,
    FONT_BOLD,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    INK,
    INTRO_LINE,
    MUTED,
    NEWS_BG,
    NEWS_GRID,
    THINK_PROMPT,
)
from twodown.models import Clue
from twodown.scenes import DEFAULT_SCENE, Scene, get_scene
from twodown.script import _spoken_parse

WIDTH, HEIGHT = 1080, 1920
PHOTO_INK = (252, 247, 236)
PHOTO_MUTED = (220, 208, 190)
MARGIN = 72


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


def _newsprint_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), NEWS_BG)
    draw = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 54):
        draw.line([(x, 0), (x, HEIGHT)], fill=NEWS_GRID, width=1)
    for y in range(0, HEIGHT, 54):
        draw.line([(0, y), (WIDTH, y)], fill=NEWS_GRID, width=1)
    draw.rectangle([0, 0, WIDTH, 18], fill=CRIMSON)
    draw.rectangle([0, HEIGHT - 18, WIDTH, HEIGHT], fill=CRIMSON)
    return img, draw


def _enum_groups(clue: Clue) -> list[int]:
    found = [int(n) for n in re.findall(r"\d+", clue.enumeration or "")]
    if found:
        return found
    letters = re.sub(r"[^A-Za-z]", "", clue.answer)
    return [len(letters)] if letters else [1]


def _cell_letters(clue: Clue, groups: list[int]) -> list[str]:
    compact = re.sub(r"[^A-Za-z]", "", clue.answer).upper()
    needed = sum(groups)
    compact = (compact + (" " * needed))[:needed]
    return list(compact)


def _center_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    *,
    spacing: int = 10,
) -> int:
    cursor = y
    for line in text.split("\n"):
        width = draw.textlength(line, font=font)
        draw.text(((WIDTH - width) / 2, cursor), line, font=font, fill=fill)
        box = draw.textbbox((0, 0), line or " ", font=font)
        cursor += (box[3] - box[1]) + spacing
    return cursor


def _draw_wordmark(draw: ImageDraw.ImageDraw) -> None:
    brand = _font(FONT_SANS_BOLD, 34)
    cryptic = "cryptic"
    w = draw.textlength(cryptic, font=brand)
    x = (WIDTH - w - draw.textlength(".fun", font=brand)) / 2
    draw.text((x, 48), cryptic, font=brand, fill=INK)
    draw.text((x + w, 48), ".fun", font=brand, fill=CRIMSON)


def _draw_kicker(draw: ImageDraw.ImageDraw, clue: Clue) -> None:
    kicker = _font(FONT_SANS, 24)
    line = f"{clue.paper} {clue.puzzle_id}  ·  {clue.setter}  ·  {clue.number} {clue.direction}"
    _center_text(draw, 100, line.upper(), kicker, MUTED, spacing=0)


def _draw_clue(draw: ImageDraw.ImageDraw, clue: Clue, y: int = 280) -> int:
    clue_font = _font(FONT_REGULAR, 68)
    wrapped = _wrap(draw, clue.clue, clue_font, WIDTH - (MARGIN * 2))
    return _center_text(draw, y, wrapped, clue_font, INK, spacing=16)


def _draw_lights(
    draw: ImageDraw.ImageDraw,
    clue: Clue,
    y: int,
    *,
    filled: bool,
) -> int:
    groups = _enum_groups(clue)
    letters = _cell_letters(clue, groups)
    total = sum(groups)
    gap = 8
    hyphen_w = 28
    cell = min(92, int((WIDTH - 160 - (total - 1) * gap - max(0, len(groups) - 1) * hyphen_w) / max(total, 1)))
    cell = max(52, cell)
    row_w = total * cell + max(0, total - 1) * gap + max(0, len(groups) - 1) * hyphen_w
    x = (WIDTH - row_w) // 2
    letter_i = 0
    font = _font(FONT_SANS_BOLD, max(30, cell - 24))
    for g, size in enumerate(groups):
        if g:
            mid_y = y + cell // 2
            draw.rectangle([x + 4, mid_y - 3, x + hyphen_w - 4, mid_y + 3], fill=INK)
            x += hyphen_w
        for _ in range(size):
            box = (x, y, x + cell, y + cell)
            draw.rounded_rectangle(box, radius=6, fill=CREAM, outline=INK, width=3)
            if filled:
                glyph = letters[letter_i]
                if glyph.strip():
                    draw.text((x + cell / 2, y + cell / 2), glyph, font=font, fill=INK, anchor="mm")
            letter_i += 1
            x += cell + gap
    return y + cell


def _source_footer(clue: Clue) -> str:
    """One Short line naming the setter, paper, and Fifteen Squared."""
    setter = (clue.setter or "").strip()
    paper = (clue.paper or "").strip()
    if paper and not paper.lower().startswith("the "):
        paper = f"the {paper}"
    if setter and paper:
        return f"{setter} in {paper} · Fifteen Squared"
    if setter:
        return f"Parse via Fifteen Squared · {setter}"
    return "Parse via Fifteen Squared"


def _footer(draw: ImageDraw.ImageDraw, text: str) -> None:
    foot = _font(FONT_SANS, 22)
    _center_text(draw, HEIGHT - 88, text, foot, MUTED, spacing=0)


def _new_card() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    return _newsprint_canvas()


def draw_beat(clue: Clue, dest: Path, beat: str = "think") -> Path:
    """One visual beat of the Short. Scene never appears — the clue is the picture."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img, draw = _new_card()
    _draw_wordmark(draw)
    if beat == "intro":
        line_font = _font(FONT_REGULAR, 72)
        wrapped = _wrap(draw, INTRO_LINE.rstrip("."), line_font, WIDTH - 160)
        _center_text(draw, 760, wrapped, line_font, INK, spacing=18)
        _footer(draw, "")
        img.save(dest, "PNG")
        return dest
    _draw_kicker(draw, clue)
    show_lights = beat != "clue"
    filled = beat in {"answer", "parse"}
    show_answer = beat in {"answer", "parse"}
    show_parse = beat in {"answer", "parse"}
    bottom = _draw_clue(draw, clue, y=240 if beat == "clue" else 210)
    lights_bottom = bottom
    if show_lights:
        lights_y = min(max(bottom + 44, 620), 880)
        lights_bottom = _draw_lights(draw, clue, lights_y, filled=filled)
        if clue.enumeration and beat == "letters":
            enum_font = _font(FONT_SANS_BOLD, 36)
            _center_text(draw, lights_bottom + 28, clue.enumeration, enum_font, CRIMSON)
    prompt_y = min(lights_bottom + 80, 1180)
    prompt = _font(FONT_SANS, 34)
    if beat == "think":
        wrapped = _wrap(draw, THINK_PROMPT, prompt, WIDTH - 160)
        _center_text(draw, prompt_y, wrapped, prompt, CRIMSON, spacing=8)
    if show_answer:
        answer = _font(FONT_BOLD, 84)
        answer_y = min(lights_bottom + 40, 1080)
        _center_text(draw, answer_y, clue.answer, answer, CRIMSON, spacing=0)
        if show_parse:
            parse_font = _font(FONT_SANS, 30)
            parse = _wrap(draw, _spoken_parse(clue.parse, clue.answer), parse_font, WIDTH - 160)
            if parse.count("\n") > 3:
                parse = "\n".join(parse.split("\n")[:3])
            _center_text(draw, answer_y + 110, parse, parse_font, MUTED, spacing=8)
            _footer(draw, _source_footer(clue))
        else:
            _footer(draw, "")
    elif beat == "clue":
        _footer(draw, "")
    elif beat == "letters":
        _footer(draw, "How many letters")
    else:
        _footer(draw, "")
    img.save(dest, "PNG")
    return dest


def draw_clue_card(clue: Clue, dest: Path, scene: str | Scene | None = None, **_extra: object) -> Path:
    return draw_beat(clue, dest, beat="think")


def draw_reveal_card(clue: Clue, dest: Path, scene: str | Scene | None = None) -> Path:
    return draw_beat(clue, dest, beat="parse")


def write_share_card(dest: Path, scene: str | Scene | None = None) -> Path:
    """1200×630 Open Graph card. Webp so Git LFS does not swallow it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest = dest.with_suffix(".webp")
    resolved = get_scene(scene)
    width, height = 1200, 630
    if resolved.is_photo and resolved.path and resolved.path.exists():
        img = _cover_crop(Image.open(resolved.path), (width, height)).convert("RGBA")
        dim = Image.new("RGBA", (width, height), (12, 10, 8, 96))
        img = Image.alpha_composite(img, dim).convert("RGB")
        ink, muted = PHOTO_INK, PHOTO_MUTED
    else:
        img = Image.new("RGB", (width, height), NEWS_BG)
        ink, muted = INK, MUTED
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 10], fill=CRIMSON)
    draw.rectangle([0, height - 10, width, height], fill=CRIMSON)
    word = _font(FONT_SANS_BOLD, 74)
    sub = _font(FONT_REGULAR, 34)
    draw.text((72, 200), "cryptic", font=word, fill=ink)
    fun_x = 72 + draw.textlength("cryptic", font=word)
    draw.text((fun_x, 200), ".fun", font=word, fill=CRIMSON)
    draw.text((72, 300), "Two cryptic clues a day", font=sub, fill=muted)
    draw.text((72, 350), "from Fifteen Squared", font=sub, fill=muted)
    img.save(dest, "WEBP", quality=82)
    return dest


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


@dataclass(frozen=True)
class ShortTimings:
    intro: float
    clue: float
    letters: float
    think: float
    answer: float
    parse: float

    @property
    def until_answer(self) -> float:
        return self.intro + self.clue + self.letters + self.think


def _encode_clips(clips: list[tuple[Path, float]], audio: Path, dest: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    cmd: list[str] = [ffmpeg, "-y"]
    filters: list[str] = []
    for i, (path, hold) in enumerate(clips):
        cmd.extend(["-loop", "1", "-t", f"{max(hold, 0.2):.2f}", "-i", str(path)])
        filters.append(f"[{i}:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[v{i}]")
    audio_i = len(clips)
    cmd.extend(["-i", str(audio)])
    concat = "".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]"
    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters)
            + ";"
            + concat
            + f";[{audio_i}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-shortest",
            str(dest),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


def render_video(
    clue_card: Path,
    reveal_card: Path,
    audio: Path,
    dest: Path,
    clue_hold: float | None = None,
    clue: Clue | None = None,
    timings: ShortTimings | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration = _ffprobe_seconds(audio)
    if clue is not None:
        work = Path("/tmp/twodown-beats") / dest.stem
        work.mkdir(parents=True, exist_ok=True)
        if timings is None:
            slice_ = max(0.6, duration / 6)
            timings = ShortTimings(slice_, slice_, slice_, slice_, slice_, slice_)
        clips = [
            (draw_beat(clue, work / "intro.png", "intro"), timings.intro),
            (draw_beat(clue, work / "clue.png", "clue"), timings.clue),
            (draw_beat(clue, work / "letters.png", "letters"), timings.letters),
            (draw_beat(clue, work / "think.png", "think"), timings.think),
            (draw_beat(clue, work / "answer.png", "answer"), timings.answer),
            (draw_beat(clue, work / "parse.png", "parse"), timings.parse),
        ]
        return _encode_clips(clips, audio, dest)
    if clue_hold is None:
        clue_secs = max(7.0, min(duration * 0.42, duration - 6.0))
    else:
        clue_secs = max(4.0, min(clue_hold, duration - 4.0))
    reveal_secs = max(4.0, duration - clue_secs + 0.4)
    return _encode_clips([(clue_card, clue_secs), (reveal_card, reveal_secs)], audio, dest)

