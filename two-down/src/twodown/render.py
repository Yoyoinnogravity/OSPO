from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from functools import lru_cache

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from dataclasses import dataclass

from twodown.config import (
    BRAND,
    CREAM,
    CRIMSON,
    DEFAULT_OUTPUT,
    FONT_BOLD,
    FONT_DISPLAY,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    HIGHLIGHT,
    HINT_LINE,
    INK,
    MUTED,
    NEWS_BG,
    NEWS_GRID,
    OUTRO_LINE,
    PACKAGE_ROOT,
    SITE_ROOT,
    THINK_PROMPT,
    THUMBNAIL_ISSUE_FIRST_SLUG,
    THUMBNAIL_ISSUE_START,
    YELLOW,
)
from twodown.hints import ensure_hint_photo, hint_for_clue
from twodown.models import Clue
from twodown.scenes import DEFAULT_SCENE, Scene, get_scene
from twodown.script import _spoken_parse

WIDTH, HEIGHT = 1080, 1920
THUMB_W, THUMB_H = 1280, 720
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
INTRO_KALEIDOSCOPE_FPS = 24
# One stock open for every film. Dictionary of "cryptic", not a per-clue graphic.
INTRO_KALEIDOSCOPE_WORDS = ("CRYPTIC",)
INTRO_DICTIONARY_HEADWORD = "cryptic"
INTRO_DICTIONARY_PRONUNCIATION = "/KRIP-tik/"
INTRO_DICTIONARY_POS = "adjective"
INTRO_DICTIONARY_SOURCE = "Webster 1913"
INTRO_DICTIONARY_GUIDE = ("cry", "crystal")
# Aled's photographed opening — tight on crypt / cryptic / cryptogram.
INTRO_DICTIONARY_PHOTO = PACKAGE_ROOT / "assets" / "intro-dictionary-page.jpg"
INTRO_DICTIONARY_CROP = (500, 240, 820, 1000)
INTRO_DICTIONARY_SOURCE_FOCUS = (648, 492)
INTRO_DICTIONARY_SOURCE_GLANCE = (675, 700)
INTRO_THESAURUS_SOURCE = "Roget 1911"
INTRO_THESAURUS_HEADING = "§ 526  Concealment"
INTRO_THESAURUS_WORDS = (
    "hidden",
    "occult",
    "secret",
    "cryptic",
    "recondite",
    "mysterious",
    "enigmatical",
    "latent",
    "under cover",
    "in petto",
)


@dataclass(frozen=True)
class DictionaryEntry:
    """One headword on the stock dictionary open. Public-domain Webster, plus one modern sense."""

    headword: str
    pos: str
    senses: tuple[str, ...]
    featured: bool = False


# Webster's Unabridged 1913 (public domain) around CRYPTIC, so the page has
# real neighbours. The crossword sense is the living usage, from Wiktionary.
INTRO_DICTIONARY_ENTRIES: tuple[DictionaryEntry, ...] = (
    DictionaryEntry("Cry", "v. i.", ("To utter a loud call; to shout; to weep.",)),
    DictionaryEntry("Crying", "a.", ("Calling for notice; notorious; compelling attention.",)),
    DictionaryEntry("Cryolite", "n.", ("A fluoride of sodium and aluminium, found in Greenland.",)),
    DictionaryEntry(
        "Crypt",
        "n.",
        (
            "A vault wholly or partly under ground; especially, a vault under a church, used for burial purposes.",
            "(Anat.) A simple gland, glandular cavity, or tube; a follicle.",
        ),
    ),
    DictionaryEntry(
        "Cryptic, Cryptical",
        "a.",
        (
            "Hidden; secret; occult. “Her more cryptic ways of working.” Glanvill.",
            "Of a crossword: clues that use wordplay rather than a plain definition.",
        ),
        featured=True,
    ),
    DictionaryEntry("Cryptically", "adv.", ("Secretly; occultly.",)),
    DictionaryEntry("Cryptogam", "n.", ("A plant of the Cryptogamia; a flowerless plant, as a fern or moss.",)),
    DictionaryEntry(
        "Cryptogamia",
        "n. pl.",
        ("The series or division of flowerless plants, or those never having true stamens and pistils, but propagated by spores.",),
    ),
    DictionaryEntry("Cryptogram", "n.", ("A cipher writing; a communication in secret characters.",)),
    DictionaryEntry("Cryptograph", "n.", ("Cipher; something written in cipher; a system of secret writing.",)),
    DictionaryEntry(
        "Cryptography",
        "n.",
        ("The act or art of writing in secret characters; also, secret characters, or cipher.",),
    ),
    DictionaryEntry("Cryptology", "n.", ("Secret or enigmatical language.",)),
    DictionaryEntry(
        "Crystal",
        "n.",
        (
            "The regular form which a substance tends to assume in solidifying.",
            "A fine kind of glass, used for vessels or for covering a watch dial.",
        ),
    ),
    DictionaryEntry("Crystalline", "a.", ("Consisting of, or like, crystal; clear; transparent; pellucid.",)),
    DictionaryEntry("Crystallize", "v.", ("To cause to form crystals, or to assume a crystalline form.",)),
    DictionaryEntry("Cub", "n.", ("A young animal, especially the young of the bear.",)),
    DictionaryEntry("Cube", "n.", ("A regular solid body, with six equal square sides.",)),
    DictionaryEntry("Cubic", "a.", ("Having the form or properties of a cube.",)),
)
INTRO_DICTIONARY_SENSES = next(entry.senses for entry in INTRO_DICTIONARY_ENTRIES if entry.featured)
INTRO_KALEIDOSCOPE_HOLD = 8.5
INTRO_KALEIDOSCOPE_ASSET = PACKAGE_ROOT / "assets" / "intro-kaleidoscope.mp4"
INTRO_KALEIDOSCOPE_STILL = PACKAGE_ROOT / "assets" / "intro-kaleidoscope.jpg"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
BRASS = (176, 132, 48)
BRASS_LIGHT = (228, 196, 110)


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


def _center_on(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    canvas_w: int,
    *,
    spacing: int = 10,
) -> int:
    cursor = y
    for line in text.split("\n"):
        width = draw.textlength(line, font=font)
        draw.text(((canvas_w - width) / 2, cursor), line, font=font, fill=fill)
        box = draw.textbbox((0, 0), line or " ", font=font)
        cursor += (box[3] - box[1]) + spacing
    return cursor


def _center_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    *,
    spacing: int = 10,
) -> int:
    return _center_on(draw, y, text, font, fill, WIDTH, spacing=spacing)


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


def _beat_footer(clue: Clue, beat: str) -> str:
    """Setter and paper only land on the source beat, when Thomas speaks."""
    if beat == "source":
        return _source_footer(clue)
    if beat == "letters":
        return "How many letters"
    return ""


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


def intro_kaleidoscope_words(clue: Clue | None = None) -> list[str]:
    """The lexicon headword only. Same on every film — never the clue, never the answer."""
    del clue
    return list(INTRO_KALEIDOSCOPE_WORDS)


def _circle_mask(size: int, inset: int = 2) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, size - 1 - inset, size - 1 - inset), fill=255)
    return mask


def _entry_block_height(
    draw: ImageDraw.ImageDraw,
    entry: DictionaryEntry,
    col_w: int,
    head_font: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
    pos_font: ImageFont.FreeTypeFont | None = None,
) -> int:
    pad = 6 if entry.featured else 2
    gap = 14 if entry.featured else 10
    height = pad + head_font.size + 8
    if entry.featured:
        height += (pos_font.size if pos_font is not None else 20) + 8
    for i, sense in enumerate(entry.senses, start=1):
        wrapped = _wrap(draw, f"{i}.  {sense}", body_font, col_w - 8)
        height += (wrapped.count("\n") + 1) * (body_font.size + 6) + 4
    return height + gap


def _draw_dictionary_entry(
    draw: ImageDraw.ImageDraw,
    entry: DictionaryEntry,
    x: int,
    y: int,
    col_w: int,
    head_font: ImageFont.FreeTypeFont,
    pos_font: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
) -> int:
    """Typeset one column entry. Returns the y under it."""
    cursor = y + (6 if entry.featured else 2)
    head = entry.headword
    draw.text((x, cursor), head, font=head_font, fill=INK)
    if entry.featured:
        cursor += head_font.size + 2
        draw.text(
            (x, cursor),
            f"{INTRO_DICTIONARY_PRONUNCIATION}   {entry.pos}",
            font=pos_font,
            fill=MUTED,
        )
        cursor += pos_font.size + 8
    else:
        head_w = draw.textlength(head, font=head_font)
        draw.text((x + head_w, cursor + 4), f"  {entry.pos}", font=pos_font, fill=MUTED)
        cursor += head_font.size + 8
    for i, sense in enumerate(entry.senses, start=1):
        wrapped = _wrap(draw, f"{i}.  {sense}", body_font, col_w - 8)
        draw.multiline_text((x, cursor), wrapped, font=body_font, fill=INK, spacing=4)
        cursor += (wrapped.count("\n") + 1) * (body_font.size + 6) + 4
    return cursor + (14 if entry.featured else 10)


def _draw_thesaurus_panel(draw: ImageDraw.ImageDraw, x: int, y: int, width: int) -> None:
    """Roget cluster under the left column — synonyms around cryptic."""
    pad = 16
    heading = _font(FONT_SANS_BOLD, 18)
    body = _font(FONT_ITALIC, 22)
    label = _font(FONT_SANS, 16)
    words = _wrap(draw, ",  ".join(INTRO_THESAURUS_WORDS), body, width - pad * 2)
    lines = words.count("\n") + 1
    box_h = 92 + lines * (body.size + 6)
    draw.rectangle([x - 4, y, x + width + 4, y + box_h], outline=INK, width=2)
    draw.rectangle([x - 4, y, x + width + 4, y + 36], fill=INK)
    draw.text((x + pad, y + 8), f"{INTRO_THESAURUS_SOURCE}  ·  {INTRO_THESAURUS_HEADING}", font=label, fill=CREAM)
    draw.multiline_text((x + pad, y + 48), words, font=body, fill=INK, spacing=6)
    draw.text((x + pad, y + box_h - 28), "see also  § 519 Enigma", font=heading, fill=CRIMSON)


def _photo_point(src_xy: tuple[int, int], box: tuple[int, int, int, int], scale: float, top_trim: int) -> tuple[int, int]:
    left, top, _, _ = box
    return (
        int((src_xy[0] - left) * scale),
        int((src_xy[1] - top) * scale) - top_trim,
    )


def _photographed_dictionary_page() -> tuple[Image.Image, tuple[int, int], tuple[int, int]]:
    """Aled's real page, tight on cryptic, plus the glass start and glance."""
    src = Image.open(INTRO_DICTIONARY_PHOTO).convert("RGB")
    box = INTRO_DICTIONARY_CROP
    left, top, right, bottom = box
    crop = src.crop(box)
    scale = WIDTH / crop.size[0]
    resized = crop.resize((WIDTH, max(HEIGHT, int(crop.size[1] * scale))), Image.Resampling.LANCZOS)
    top_trim = 0
    if resized.size[1] > HEIGHT:
        focus_y = int((INTRO_DICTIONARY_SOURCE_FOCUS[1] - top) * scale)
        top_trim = max(0, min(resized.size[1] - HEIGHT, focus_y - int(HEIGHT * 0.38)))
        resized = resized.crop((0, top_trim, WIDTH, top_trim + HEIGHT))
    elif resized.size[1] < HEIGHT:
        canvas = Image.new("RGB", (WIDTH, HEIGHT), (248, 243, 230))
        canvas.paste(resized, (0, (HEIGHT - resized.size[1]) // 2))
        resized = canvas
    page = ImageEnhance.Contrast(resized).enhance(1.2)
    page = ImageEnhance.Brightness(page).enhance(1.04)
    page = ImageEnhance.Sharpness(page).enhance(1.55)
    focus = _photo_point(INTRO_DICTIONARY_SOURCE_FOCUS, box, scale, top_trim)
    glance = _photo_point(INTRO_DICTIONARY_SOURCE_GLANCE, box, scale, top_trim)
    return page, focus, glance


@lru_cache(maxsize=1)
def _dictionary_layout() -> tuple[Image.Image, tuple[int, int], tuple[int, int]]:
    """Real photographed page when we have one; otherwise the typeset Webster stand-in."""
    if INTRO_DICTIONARY_PHOTO.exists():
        return _photographed_dictionary_page()
    page, focus = _typeset_dictionary_page()
    return page, focus, (min(WIDTH - 220, focus[0] + 40), min(HEIGHT - 220, focus[1] + 360))


def _typeset_dictionary_page() -> tuple[Image.Image, tuple[int, int]]:
    """Two-column Webster page around cryptic, plus the centre of that entry."""
    img, draw = _newsprint_canvas()
    header = _font(FONT_SANS, 20)
    guide = _font(FONT_ITALIC, 24)
    draw.text((56, 48), f"{INTRO_DICTIONARY_SOURCE.upper()}  ·  C", font=header, fill=MUTED)
    brand = _font(FONT_SANS_BOLD, 20)
    brand_w = draw.textlength(BRAND, font=brand)
    draw.text((WIDTH - 56 - brand_w, 48), BRAND, font=brand, fill=CRIMSON)
    draw.line([(56, 84), (WIDTH - 56, 84)], fill=CRIMSON, width=3)
    left_guide, right_guide = INTRO_DICTIONARY_GUIDE
    draw.text((56, 96), f"{left_guide}  —  {right_guide}", font=guide, fill=(168, 150, 128))
    draw.text((WIDTH - 200, 96), "folio  348", font=_font(FONT_SANS, 18), fill=MUTED)
    draw.line([(56, 132), (WIDTH - 56, 132)], fill=INK, width=2)

    margin_x = 56
    top = 148
    bottom = 1848
    gutter = 32
    col_w = (WIDTH - margin_x * 2 - gutter) // 2
    columns = (margin_x, margin_x + col_w + gutter)
    draw.line([(columns[1] - gutter // 2, top), (columns[1] - gutter // 2, bottom)], fill=NEWS_GRID, width=2)

    head_font = _font(FONT_BOLD, 26)
    featured_head = _font(FONT_BOLD, 36)
    pos_font = _font(FONT_ITALIC, 20)
    body_font = _font(FONT_REGULAR, 21)
    featured_body = _font(FONT_REGULAR, 24)

    featured_idx = next(i for i, entry in enumerate(INTRO_DICTIONARY_ENTRIES) if entry.featured)
    # Cryptic stays mid-left; the rest of the C-R neighbours open the right column.
    split_at = featured_idx + 2
    featured_box: tuple[int, int, int, int] | None = None
    for col, chunk in (
        (0, INTRO_DICTIONARY_ENTRIES[:split_at]),
        (1, INTRO_DICTIONARY_ENTRIES[split_at:]),
    ):
        y = top
        x = columns[col]
        for entry in chunk:
            hfont = featured_head if entry.featured else head_font
            bfont = featured_body if entry.featured else body_font
            block_h = _entry_block_height(draw, entry, col_w, hfont, bfont, pos_font)
            if y + block_h > bottom:
                break
            if entry.featured:
                wash = ImageDraw.Draw(img)
                wash.rectangle([x - 8, y, x + col_w + 4, y + block_h - 4], fill=(252, 236, 196))
                wash.rectangle([x - 8, y, x - 2, y + block_h - 4], fill=CRIMSON)
                featured_box = (x, y, x + col_w, y + block_h)
            y = _draw_dictionary_entry(draw, entry, x, y, col_w, hfont, pos_font, bfont)

    _draw_thesaurus_panel(draw, columns[0], 1388, col_w)
    draw.text(
        (56, 1864),
        "Webster’s Unabridged, 1913  ·  Roget 1911  ·  crossword sense via Wiktionary",
        font=_font(FONT_ITALIC, 18),
        fill=MUTED,
    )
    if featured_box is None:
        featured_center = (columns[0] + col_w // 2, 640)
    else:
        featured_center = (
            (featured_box[0] + featured_box[2]) // 2,
            (featured_box[1] + featured_box[3]) // 2,
        )
    return img, featured_center


def _dictionary_page() -> Image.Image:
    """Open lexicon: real Webster neighbours around cryptic. Same on every film."""
    return _dictionary_layout()[0]


def _with_magnifier(page: Image.Image, center: tuple[int, int], radius: int = 268, zoom: float = 1.7) -> Image.Image:
    """Brass glass over the dictionary page."""
    cx, cy = center
    src_r = int(radius / zoom)
    box = (
        max(0, cx - src_r),
        max(0, cy - src_r),
        min(page.size[0], cx + src_r),
        min(page.size[1], cy + src_r),
    )
    crop = page.crop(box).resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)
    lens = Image.new("RGBA", page.size, (0, 0, 0, 0))
    left, top = cx - radius, cy - radius
    lens.paste(crop.convert("RGBA"), (left, top), _circle_mask(radius * 2))
    overlay = ImageDraw.Draw(lens)
    ring = [left, top, left + radius * 2, top + radius * 2]
    overlay.ellipse(ring, outline=(*BRASS, 255), width=22)
    overlay.ellipse(
        (left + 8, top + 8, left + radius * 2 - 8, top + radius * 2 - 8),
        outline=(*BRASS_LIGHT, 255),
        width=6,
    )
    overlay.arc(
        (left + 36, top + 28, left + radius - 10, top + radius - 20),
        start=200,
        end=300,
        fill=(255, 255, 255, 92),
        width=10,
    )
    hx, hy = cx + int(radius * 0.72), cy + int(radius * 0.72)
    overlay.line((hx, hy, hx + 132, hy + 158), fill=(*BRASS, 255), width=36)
    overlay.line((hx, hy, hx + 132, hy + 158), fill=(*INK, 255), width=7)
    overlay.ellipse((hx + 114, hy + 142, hx + 168, hy + 196), fill=(*BRASS, 255), outline=(*INK, 255), width=4)
    out = page.convert("RGBA")
    out = Image.alpha_composite(out, lens)
    return out.convert("RGB")


def _compose_intro_frame(progress: float) -> Image.Image:
    """Real dictionary page: hold on cryptic, then read the neighbours."""
    t = max(0.0, min(1.0, progress))
    page, focus, glance = _dictionary_layout()
    # First half of the open is for the definition. Then a slow glance down the column.
    hold = 0.0 if t < 0.42 else min(1.0, (t - 0.42) / 0.58)
    ease = hold * hold * (3 - 2 * hold)
    glass = (
        int(focus[0] + (glance[0] - focus[0]) * ease),
        int(focus[1] + (glance[1] - focus[1]) * ease),
    )
    frame = _with_magnifier(page, glass, radius=248, zoom=1.55)
    draw = ImageDraw.Draw(frame)
    draw.rectangle([0, 0, WIDTH, 14], fill=HIGHLIGHT)
    draw.rectangle([0, HEIGHT - 14, WIDTH, HEIGHT], fill=HIGHLIGHT)
    return frame


def draw_intro_kaleidoscope_still(clue: Clue | None = None, dest: Path | None = None) -> Image.Image:
    """One stock lexicon frame. Same still on every film."""
    del clue
    if INTRO_KALEIDOSCOPE_STILL.exists():
        frame = Image.open(INTRO_KALEIDOSCOPE_STILL).convert("RGB")
        if frame.size != (WIDTH, HEIGHT):
            frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    else:
        frame = _compose_intro_frame(0.28)
        INTRO_KALEIDOSCOPE_STILL.parent.mkdir(parents=True, exist_ok=True)
        frame.save(INTRO_KALEIDOSCOPE_STILL, "JPEG", quality=90)
    if dest is not None:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        frame.save(dest)
    return frame


def _bake_intro_kaleidoscope(dest: Path) -> Path:
    """Render the stock open once. Later films reuse this file."""
    dest = Path(dest).with_suffix(".mp4")
    dest.parent.mkdir(parents=True, exist_ok=True)
    hold = INTRO_KALEIDOSCOPE_HOLD
    fps = INTRO_KALEIDOSCOPE_FPS
    count = max(8, int(round(hold * fps)))
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    frames = dest.parent / f"{dest.stem}-frames"
    frames.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        progress = i / max(count - 1, 1)
        _compose_intro_frame(progress).save(frames / f"{i:04d}.jpg", "JPEG", quality=86)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames / "%04d.jpg"),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-t",
            f"{hold:.2f}",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-800:])
    shutil.rmtree(frames, ignore_errors=True)
    still = _compose_intro_frame(0.28)
    INTRO_KALEIDOSCOPE_STILL.parent.mkdir(parents=True, exist_ok=True)
    still.save(INTRO_KALEIDOSCOPE_STILL, "JPEG", quality=90)
    return dest


def ensure_intro_kaleidoscope() -> Path:
    """Return the shared intro clip. Build it once if the asset is missing."""
    asset = INTRO_KALEIDOSCOPE_ASSET
    if asset.exists() and asset.stat().st_size > 1000:
        return asset
    return _bake_intro_kaleidoscope(asset)


def render_intro_kaleidoscope(clue: Clue | None, dest: Path, duration: float) -> Path:
    """Trim the stock kaleidoscope to this film's spoken open. No per-clue rebuild."""
    del clue
    dest = Path(dest).with_suffix(".mp4")
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = ensure_intro_kaleidoscope()
    hold = max(0.4, duration)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-an",
            "-t",
            f"{hold:.2f}",
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
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-800:])
    return dest


def draw_beat(clue: Clue, dest: Path, beat: str = "think") -> Path:
    """One visual beat of the Short. Scene never appears — the clue is the picture."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if beat == "intro":
        draw_intro_kaleidoscope_still(clue, dest)
        return dest
    img, draw = _new_card()
    _draw_wordmark(draw)
    if beat == "outro":
        line_font = _font(FONT_REGULAR, 72)
        wrapped = _wrap(draw, OUTRO_LINE.rstrip("."), line_font, WIDTH - 160)
        _center_text(draw, 760, wrapped, line_font, INK, spacing=18)
        _footer(draw, "")
        img.save(dest, "PNG")
        return dest
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
        _footer(draw, _beat_footer(clue, beat))
        img.save(dest, "PNG")
        return dest
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
        _footer(draw, _beat_footer(clue, beat))
    elif beat == "clue":
        _footer(draw, "")
    else:
        _footer(draw, _beat_footer(clue, beat))
    img.save(dest, "PNG")
    return dest


def draw_clue_card(clue: Clue, dest: Path, scene: str | Scene | None = None, **_extra: object) -> Path:
    return draw_beat(clue, dest, beat="think")


def draw_reveal_card(clue: Clue, dest: Path, scene: str | Scene | None = None) -> Path:
    return draw_beat(clue, dest, beat="parse")


def _draw_empty_lights(
    draw: ImageDraw.ImageDraw,
    clue: Clue,
    y: int,
    canvas_w: int,
    *,
    max_cell: int = 72,
) -> int:
    """Crossword lights with no letters. Used on thumbnails so the answer stays hidden."""
    groups = _enum_groups(clue)
    total = sum(groups)
    gap = 6
    hyphen_w = 22
    cell = min(
        max_cell,
        int((canvas_w - 160 - (total - 1) * gap - max(0, len(groups) - 1) * hyphen_w) / max(total, 1)),
    )
    cell = max(36, cell)
    row_w = total * cell + max(0, total - 1) * gap + max(0, len(groups) - 1) * hyphen_w
    x = (canvas_w - row_w) // 2
    for g, size in enumerate(groups):
        if g:
            mid_y = y + cell // 2
            draw.rectangle([x + 3, mid_y - 2, x + hyphen_w - 3, mid_y + 2], fill=INK)
            x += hyphen_w
        for _ in range(size):
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=5, fill=CREAM, outline=INK, width=3)
            x += cell + gap
    return y + cell


def published_pair_slugs(site_root: Path | None = None) -> list[str]:
    """Oldest-first pair slugs from the published archive."""
    days = Path(site_root or SITE_ROOT) / "d"
    if not days.is_dir():
        return []
    slugs: list[str] = []
    for page in sorted(days.glob("*/index.html")):
        slugs.extend(re.findall(r'data-slug="([^"]+)"', page.read_text(encoding="utf-8")))
    return slugs


THUMBNAIL_ISSUE_LEDGER = SITE_ROOT / "media" / "thumbnail-issues.json"


def _unique_slugs(slugs: list[str]) -> list[str]:
    seen: list[str] = []
    for slug in slugs:
        if slug and slug not in seen:
            seen.append(slug)
    return seen


def _study_slugs(out_dir: Path | None = None) -> list[str]:
    root = Path(out_dir or DEFAULT_OUTPUT) / "study"
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def _load_issue_ledger(path: Path | None = None) -> list[str]:
    ledger = Path(path or THUMBNAIL_ISSUE_LEDGER)
    if not ledger.exists():
        return []
    raw = json.loads(ledger.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [str(slug) for slug in raw]
    if isinstance(raw, dict):
        return [str(slug) for slug, _num in sorted(raw.items(), key=lambda item: item[1])]
    return []


def _save_issue_ledger(slugs: list[str], path: Path | None = None) -> None:
    ledger = Path(path or THUMBNAIL_ISSUE_LEDGER)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(slugs, indent=2) + "\n", encoding="utf-8")


def issue_catalog(slugs: list[str] | None = None) -> list[str]:
    """One slug, one issue. Published films first, then review cuts, then the ledger."""
    if slugs is not None:
        catalog = _unique_slugs(list(slugs))
    else:
        catalog = _unique_slugs(published_pair_slugs() + _load_issue_ledger() + _study_slugs())
    if THUMBNAIL_ISSUE_FIRST_SLUG in catalog:
        catalog = catalog[catalog.index(THUMBNAIL_ISSUE_FIRST_SLUG) :]
    return catalog


def thumbnail_issue(clue: Clue, slugs: list[str] | None = None, *, persist: bool = False) -> int:
    """Running Cryptic Fit issue. Each slug gets its own number. #287 is first on the channel."""
    catalog = issue_catalog(slugs)
    if clue.slug not in catalog:
        catalog.append(clue.slug)
        if persist and slugs is None:
            _save_issue_ledger(catalog)
    return THUMBNAIL_ISSUE_START + catalog.index(clue.slug)


def _display_font(size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DISPLAY if Path(FONT_DISPLAY).exists() else FONT_SANS_BOLD
    return _font(path, size)


def _circle_offsets(width: int) -> list[tuple[int, int]]:
    return [
        (dx, dy)
        for dx in range(-width, width + 1)
        for dy in range(-width, width + 1)
        if dx * dx + dy * dy <= width * width
    ]


def _stroke_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    width: int,
) -> None:
    x, y = xy
    for dx, dy in _circle_offsets(width):
        draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _issue_lockup(clue: Clue, size: tuple[int, int], *, brand_size: int, number_size: int) -> Image.Image:
    """Tilted CRYPTIC FIT #N — bold yellow letters on a red highlighter. Never the answer."""
    width, height = size
    issue = thumbnail_issue(clue, persist=True)
    brand = "CRYPTIC FIT"
    number = f"#{issue}"
    tilt = -8 + (issue % 3) * 4
    layer = Image.new("RGBA", (width + 160, height + 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    brand_font = _display_font(brand_size)
    number_font = _display_font(number_size)
    brand_w = draw.textlength(brand, font=brand_font)
    number_w = draw.textlength(number, font=number_font)
    brand_box = draw.textbbox((0, 0), brand, font=brand_font)
    number_box = draw.textbbox((0, 0), number, font=number_font)
    brand_h = brand_box[3] - brand_box[1]
    number_h = number_box[3] - number_box[1]
    gap = max(12, int(brand_size * 0.12))
    block_w = max(brand_w, number_w)
    block_h = brand_h + gap + number_h
    left = (layer.size[0] - block_w) / 2
    top = (layer.size[1] - block_h) / 2 - 10
    pad_x, pad_y = 36, 22
    highlight = [
        left - pad_x + 18,
        top - pad_y + 8,
        left + block_w + pad_x + 10,
        top + block_h + pad_y,
    ]
    draw.rounded_rectangle(highlight, radius=28, fill=(*HIGHLIGHT, 255))
    # Marker swipe: a second, slightly offset highlight so it feels hand-drawn.
    draw.rounded_rectangle(
        [highlight[0] - 14, highlight[1] + 10, highlight[2] + 8, highlight[3] - 6],
        radius=24,
        fill=(*CRIMSON, 255),
    )
    draw.rounded_rectangle(highlight, radius=28, fill=(*HIGHLIGHT, 255))
    brand_x = left + (block_w - brand_w) / 2
    number_x = left + (block_w - number_w) / 2
    stroke = max(6, brand_size // 16)
    _stroke_text(draw, (brand_x, top), brand, brand_font, YELLOW, INK, stroke)
    _stroke_text(
        draw,
        (number_x, top + brand_h + gap),
        number,
        number_font,
        YELLOW,
        INK,
        max(8, number_size // 14),
    )
    return layer.rotate(tilt, resample=Image.Resampling.BICUBIC, expand=False)


def _paste_centered(base: Image.Image, overlay: Image.Image, *, dy: int = 0) -> None:
    x = (base.size[0] - overlay.size[0]) // 2
    y = (base.size[1] - overlay.size[1]) // 2 + dy
    base.paste(overlay, (x, y), overlay)


def _dark_canvas(size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, INK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size[0], 14], fill=HIGHLIGHT)
    draw.rectangle([0, size[1] - 14, size[0], size[1]], fill=HIGHLIGHT)
    return img


def _thumbnail_clue(clue: Clue) -> str:
    """Surface and letter count only. Never the answer."""
    surface = (clue.clue or "").strip()
    enum = (clue.enumeration or "").strip()
    if enum and f"({enum})" not in surface:
        return f"{surface} ({enum})"
    return surface


def _draw_thumbnail_clue(img: Image.Image, clue: Clue) -> None:
    """Sit the clue under the lockup. Keep it readable on a small YouTube tile."""
    draw = ImageDraw.Draw(img)
    text = _thumbnail_clue(clue)
    max_width = img.size[0] - 120
    size = 46
    font = _font(FONT_BOLD, size)
    wrapped = _wrap(draw, text, font, max_width)
    while wrapped.count("\n") >= 3 and size > 32:
        size -= 2
        font = _font(FONT_BOLD, size)
        wrapped = _wrap(draw, text, font, max_width)
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10)
    y = img.size[1] - 52 - (box[3] - box[1])
    _center_on(draw, y, wrapped, font, CREAM, img.size[0], spacing=10)


def draw_thumbnail(clue: Clue, dest: Path) -> Path:
    """16:9 YouTube thumbnail. Yellow CRYPTIC FIT #N on red, clue underneath. Never the answer."""
    dest = dest.with_suffix(".jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = _dark_canvas((THUMB_W, THUMB_H))
    _paste_centered(
        img,
        _issue_lockup(clue, (THUMB_W, THUMB_H), brand_size=100, number_size=200),
        dy=-70,
    )
    _draw_thumbnail_clue(img, clue)
    img.save(dest, "JPEG", quality=90)
    return dest


def draw_poster(clue: Clue, dest: Path) -> Path:
    """9:16 video poster. Same yellow-on-red lockup. Never the answer."""
    dest = dest.with_suffix(".jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = _dark_canvas((WIDTH, HEIGHT))
    _paste_centered(
        img,
        _issue_lockup(clue, (WIDTH, HEIGHT), brand_size=130, number_size=280),
        dy=-40,
    )
    img.save(dest, "JPEG", quality=90)
    return dest


def write_spoiler_free_stills(clue: Clue, dest_dir: Path) -> tuple[Path, Path]:
    """YouTube 16:9 thumb plus a 9:16 video poster. Neither shows the answer."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    thumb = draw_thumbnail(clue, dest_dir / f"{clue.slug}-thumb.jpg")
    poster = draw_poster(clue, dest_dir / f"{clue.slug}-poster.jpg")
    return thumb, poster


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
    hint: float
    answer: float
    parse: float
    source: float
    outro: float

    @property
    def until_answer(self) -> float:
        return self.intro + self.clue + self.letters + self.think + self.hint


def _is_video_clip(path: Path) -> bool:
    return Path(path).suffix.lower() in {".mp4", ".mov", ".webm", ".m4v"}


def _encode_clips(clips: list[tuple[Path, float]], audio: Path, dest: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short")
    cmd: list[str] = [ffmpeg, "-y"]
    filters: list[str] = []
    for i, (path, hold) in enumerate(clips):
        seconds = max(hold, 0.2)
        if _is_video_clip(path):
            cmd.extend(["-i", str(path)])
            filters.append(
                f"[{i}:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,setsar=1,format=yuv420p,trim=duration={seconds:.2f},"
                f"setpts=PTS-STARTPTS[v{i}]"
            )
        else:
            cmd.extend(["-loop", "1", "-t", f"{seconds:.2f}", "-i", str(path)])
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
            slice_ = max(0.6, duration / 8)
            timings = ShortTimings(
                slice_, slice_, slice_, slice_, slice_, slice_, slice_, slice_, slice_
            )
        clips = [
            (render_intro_kaleidoscope(clue, work / "intro.mp4", timings.intro), timings.intro),
            (draw_beat(clue, work / "clue.png", "clue"), timings.clue),
            (draw_beat(clue, work / "letters.png", "letters"), timings.letters),
            (draw_beat(clue, work / "think.png", "think"), timings.think),
            (draw_beat(clue, work / "hint.png", "hint"), timings.hint),
            (draw_beat(clue, work / "answer.png", "answer"), timings.answer),
            (draw_beat(clue, work / "parse.png", "parse"), timings.parse),
            (draw_beat(clue, work / "source.png", "source"), timings.source),
            (draw_beat(clue, work / "outro.png", "outro"), timings.outro),
        ]
        return _encode_clips(clips, audio, dest)
    if clue_hold is None:
        clue_secs = max(7.0, min(duration * 0.42, duration - 6.0))
    else:
        clue_secs = max(4.0, min(clue_hold, duration - 4.0))
    reveal_secs = max(4.0, duration - clue_secs + 0.4)
    return _encode_clips([(clue_card, clue_secs), (reveal_card, reveal_secs)], audio, dest)

