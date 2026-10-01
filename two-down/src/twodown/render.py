from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dataclasses import dataclass

from twodown.config import (
    BRAND,
    CREAM,
    CRIMSON,
    FONT_BOLD,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    HINT_LINE,
    INK,
    INTRO_LINE,
    TAGLINE,
    MUTED,
    OUTRO_LINE,
    NEWS_BG,
    NEWS_GRID,
    THINK_PROMPT,
)
from twodown.croc import paste_croc
from twodown.hints import ensure_hint_photo, hint_for_clue
from twodown.models import Clue
from twodown.scenes import DEFAULT_SCENE, Scene, get_scene
from twodown.script import _spoken_parse

WIDTH, HEIGHT = 1080, 1920
PHOTO_INK = (252, 247, 236)
PHOTO_MUTED = (220, 208, 190)
MARGIN = 72
# Parse under the answer: second-loudest thing on the card after the crimson answer.
PARSE_FONT = FONT_SANS_BOLD
PARSE_SIZE = 60
PARSE_FILL = INK
PARSE_MAX_LINES = 5
PARSE_SPACING = 20
# Map speech into the Short and make it unmistakable (widgets often play quiet).
AUDIO_LOUDNESS = "loudnorm=I=-16:TP=-1.5:LRA=11,volume=3,alimiter=limit=0.95"


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


def _brand_parts() -> tuple[str, str]:
    head, _, tail = BRAND.partition(".")
    return head, f".{tail}" if tail else ""


def _draw_wordmark(draw: ImageDraw.ImageDraw) -> None:
    brand = _font(FONT_SANS_BOLD, 34)
    cryptic, suffix = _brand_parts()
    w = draw.textlength(cryptic, font=brand)
    x = (WIDTH - w - draw.textlength(suffix, font=brand)) / 2
    draw.text((x, 48), cryptic, font=brand, fill=INK)
    draw.text((x + w, 48), suffix, font=brand, fill=CRIMSON)


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
    """One Short line naming the setter and the paper."""
    setter = (clue.setter or "").strip()
    paper = (clue.paper or "").strip()
    if paper and not paper.lower().startswith("the "):
        paper = f"the {paper}"
    if setter and paper:
        return f"{setter} in {paper}"
    if setter:
        return setter
    if paper:
        return paper
    return BRAND


def _footer(draw: ImageDraw.ImageDraw, text: str) -> None:
    foot = _font(FONT_SANS, 22)
    _center_text(draw, HEIGHT - 88, text, foot, MUTED, spacing=0)


def _draw_hint_photo(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    y: int,
    clue: Clue,
) -> int:
    """Inset a credited hint still. Never a full-bleed travel photo."""
    matched = hint_for_clue(clue)
    photo = Image.open(ensure_hint_photo(matched)).convert("RGB")
    frame_w, frame_h = 900, 560
    left = (WIDTH - frame_w) // 2
    crop = _cover_crop(photo, (frame_w - 16, frame_h - 16))
    draw.rounded_rectangle(
        [left, y, left + frame_w, y + frame_h],
        radius=10,
        fill=CREAM,
        outline=INK,
        width=3,
    )
    img.paste(crop, (left + 8, y + 8))
    credit = _font(FONT_SANS, 18)
    line = clue.hint_credit or matched.credit_line
    wrapped = _wrap(draw, line, credit, WIDTH - 160)
    return _center_text(draw, y + frame_h + 16, wrapped, credit, MUTED, spacing=4)


def _new_card() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    return _newsprint_canvas()


def _paint_beat(clue: Clue, beat: str) -> Image.Image:
    """The card without Cryptic Croc, so each animation frame can reuse it."""
    img, draw = _new_card()
    _draw_wordmark(draw)
    if beat in {"intro", "outro"}:
        line = INTRO_LINE if beat == "intro" else OUTRO_LINE
        line_font = _font(FONT_REGULAR, 64)
        wrapped = _wrap(draw, line.rstrip("."), line_font, WIDTH - 180)
        _center_text(draw, 280, wrapped, line_font, INK, spacing=16)
        _footer(draw, "")
        return img
    _draw_kicker(draw, clue)
    show_lights = beat != "clue"
    filled = beat in {"answer", "parse", "source"}
    show_answer = beat in {"answer", "parse", "source"}
    show_parse = beat in {"answer", "parse", "source"}
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
    if beat == "hint":
        # Empty lights stay; the picture is the hint. Never fill or print the answer.
        prompt_y = min(lights_bottom + 36, 980)
        line = (clue.hint_line or HINT_LINE).rstrip(".")
        wrapped = _wrap(draw, line, prompt, WIDTH - 160)
        next_y = _center_text(draw, prompt_y, wrapped, prompt, CRIMSON, spacing=8)
        _draw_hint_photo(img, draw, min(next_y + 18, 1040), clue)
        _footer(draw, _source_footer(clue))
        return img
    if show_answer:
        answer = _font(FONT_BOLD, 84)
        answer_y = min(lights_bottom + 40, 1080)
        _center_text(draw, answer_y, clue.answer, answer, CRIMSON, spacing=0)
        if show_parse:
            parse_font = _font(PARSE_FONT, PARSE_SIZE)
            parse = _wrap(draw, _spoken_parse(clue.parse, clue.answer), parse_font, WIDTH - 160)
            if parse.count("\n") >= PARSE_MAX_LINES:
                parse = "\n".join(parse.split("\n")[:PARSE_MAX_LINES])
            _center_text(draw, answer_y + 118, parse, parse_font, PARSE_FILL, spacing=PARSE_SPACING)
            _footer(draw, _source_footer(clue))
        else:
            _footer(draw, "")
    elif beat == "clue":
        _footer(draw, "")
    elif beat == "letters":
        _footer(draw, "How many letters")
    else:
        _footer(draw, "")
    return img


def compose_beat(clue: Clue, beat: str = "think", frame: int = 0) -> Image.Image:
    """One frame of a beat, with Cryptic Croc in that pose."""
    img = _paint_beat(clue, beat)
    paste_croc(img, beat, frame)
    return img


def draw_beat(clue: Clue, dest: Path, beat: str = "think") -> Path:
    """One visual beat of the Short. Scene never appears — the clue is the picture."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    compose_beat(clue, beat, 0).save(dest, "PNG")
    return dest


def draw_clue_card(clue: Clue, dest: Path, scene: str | Scene | None = None, **_extra: object) -> Path:
    return draw_beat(clue, dest, beat="think")


def opening_frame_poster(video: Path, dest: Path) -> Path:
    """Opening frame of the Short, before the answer is drawn.

    Use this only when the clue text is not available to draw a fresh
    unsolved card. JPEG for a one-off grab; WebP when the site will serve it.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to copy the opening frame")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    grab = dest if dest.suffix.lower() in {".jpg", ".jpeg"} else dest.with_suffix(".jpg")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-ss", "0.05", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(grab)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("could not copy the opening frame") from exc
    if grab.resolve() != dest.resolve():
        Image.open(grab).convert("RGB").save(dest, "WEBP", quality=82)
        grab.unlink(missing_ok=True)
    return dest


def write_thumbnail(clue: Clue, dest: Path) -> Path:
    """Poster for the site and the YouTube Short.

    The unsolved clue and empty lights only. The answer word and the filled
    grid stay off this image, so a thumbnail cannot spoil the solve.
    YouTube takes JPEG. The site takes WebP, because Git LFS would otherwise
    publish a pointer instead of the picture.
    """
    dest = Path(dest)
    if dest.suffix.lower() not in {".jpg", ".jpeg", ".webp"}:
        dest = dest.with_suffix(".jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    png = dest.with_suffix(".png")
    draw_beat(clue, png, beat="letters")
    image = Image.open(png).convert("RGB")
    if dest.suffix.lower() == ".webp":
        image.save(dest, "WEBP", quality=82)
    else:
        image.save(dest, "JPEG", quality=85, optimize=True)
    if png.resolve() != dest.resolve() and png.exists():
        png.unlink()
    return dest


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
    cryptic, suffix = _brand_parts()
    draw.text((72, 200), cryptic, font=word, fill=ink)
    fit_x = 72 + draw.textlength(cryptic, font=word)
    draw.text((fit_x, 200), suffix, font=word, fill=CRIMSON)
    draw.text((72, 300), "Two cryptic clues a day", font=sub, fill=muted)
    draw.text((72, 350), TAGLINE, font=sub, fill=muted)
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
    hint: float
    answer: float
    parse: float
    source: float
    outro: float

    @property
    def until_answer(self) -> float:
        return self.intro + self.clue + self.letters + self.think + self.hint


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
            + f";[{audio_i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,{AUDIO_LOUDNESS}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "192k",
            "-ar",
            "44100",
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


def _motion_clip(clue: Clue, beat: str, seconds: float, folder: Path) -> Path:
    """A few poses of Cryptic Croc, held for this beat."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    seconds = max(float(seconds), 0.24)
    fps = 6
    frames = max(4, int(round(seconds * fps)))
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    base = _paint_beat(clue, beat)
    for index in range(frames):
        card = base.copy()
        paste_croc(card, beat, index)
        card.save(folder / f"{index:04d}.png")
    dest = folder.with_suffix(".mp4")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(folder / "%04d.png"),
            "-frames:v",
            str(frames),
            "-t",
            f"{seconds:.5f}",
            "-r",
            str(fps),
            "-video_track_timescale",
            "6000",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest


def _concat_motion(clips: list[Path], audio: Path, dest: Path) -> Path:
    """Join croc clips on a shared clock so the picture matches the voice.

    The concat demuxer ignores per-clip duration when timebases differ, and
    the picture then overruns the soundtrack. Filter concat keeps each hold.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    if not clips:
        raise ValueError("need motion clips to build the Short")
    hold = max(_ffprobe_seconds(audio), 1.0)
    listing = dest.with_suffix(".concat.txt")
    lines: list[str] = []
    for path in clips:
        clip_hold = max(_ffprobe_seconds(path), 0.2)
        lines.append(f"file '{path}'\n")
        lines.append(f"duration {clip_hold:.5f}\n")
        lines.append(f"outpoint {clip_hold:.5f}\n")
    listing.write_text("".join(lines), encoding="utf-8")
    cmd: list[str] = [ffmpeg, "-y"]
    filters: list[str] = []
    for i, path in enumerate(clips):
        cmd.extend(["-i", str(path)])
        filters.append(
            f"[{i}:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v{i}]"
        )
    audio_i = len(clips)
    cmd.extend(["-i", str(audio)])
    concat = "".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]"
    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters)
            + ";"
            + concat
            + f";[{audio_i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,{AUDIO_LOUDNESS}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-t",
            f"{hold:.3f}",
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
        work = Path("/tmp/twodown-beats") / dest.parent.name / dest.stem
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True, exist_ok=True)
        if timings is None:
            slice_ = max(0.6, duration / 8)
            timings = ShortTimings(
                slice_, slice_, slice_, slice_, slice_, slice_, slice_, slice_, slice_
            )
        names = (
            "intro",
            "clue",
            "letters",
            "think",
            "hint",
            "answer",
            "parse",
            "source",
            "outro",
        )
        holds = (
            timings.intro,
            timings.clue,
            timings.letters,
            timings.think,
            timings.hint,
            timings.answer,
            timings.parse,
            timings.source,
            timings.outro,
        )
        clips = [
            _motion_clip(clue, name, hold, work / name)
            for name, hold in zip(names, holds, strict=True)
        ]
        return _concat_motion(clips, audio, dest)
    if clue_hold is None:
        clue_secs = max(7.0, min(duration * 0.42, duration - 6.0))
    else:
        clue_secs = max(4.0, min(clue_hold, duration - 4.0))
    reveal_secs = max(4.0, duration - clue_secs + 0.4)
    return _encode_clips([(clue_card, clue_secs), (reveal_card, reveal_secs)], audio, dest)

