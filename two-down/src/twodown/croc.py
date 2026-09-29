"""Cryptic Croc, the crossword presenter.

A small female crocodile drawn on the card. She talks, blinks, and waves
while a Short is playing. The clue stays in the middle of the picture.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from twodown.config import CREAM, CRIMSON, INK

SCALE = (78, 138, 86)
SCALE_DARK = (46, 92, 58)
BELLY = (244, 228, 196)
SNOUT = (96, 156, 104)
TOOTH = (252, 247, 236)

# Talking beats move her mouth. The think beat is the quiet wait.
_TALKING = {"intro", "clue", "letters", "hint", "answer", "parse", "source", "outro"}
_BIG = {"intro", "outro"}


def _mood(beat: str) -> str:
    if beat in {"intro", "outro"}:
        return "wave"
    if beat == "hint":
        return "point"
    if beat == "think":
        return "think"
    if beat == "answer":
        return "cheer"
    return "talk"


def croc_sprite(beat: str, frame: int) -> Image.Image:
    """One pose of Cryptic Croc, transparent around the edges."""
    mood = _mood(beat)
    talking = beat in _TALKING and mood != "think"
    blink = frame % 22 in {0, 1}
    mouth = (frame % 4) if talking else 0
    tail = int(8 * math.sin(frame / 2.2))
    wave = int(18 * math.sin(frame / 1.6))
    canvas = Image.new("RGBA", (520, 460), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Tail, behind the body.
    draw.polygon(
        [(150, 250 + tail), (70, 210 + tail), (48, 250), (92, 300), (160, 290)],
        fill=SCALE_DARK,
    )
    draw.ellipse([118, 168, 360, 360], fill=SCALE)
    draw.ellipse([168, 210, 330, 348], fill=BELLY)
    # Haunches.
    draw.ellipse([150, 300, 230, 390], fill=SCALE_DARK)
    draw.ellipse([250, 308, 330, 392], fill=SCALE_DARK)
    # Claws.
    for claw_x in (168, 196, 274, 302):
        draw.ellipse([claw_x, 360, claw_x + 16, 376], fill=TOOTH)

    # Head and snout.
    draw.ellipse([250, 70, 470, 270], fill=SCALE)
    draw.ellipse([360, 130, 512, 250], fill=SNOUT)
    draw.ellipse([430, 168, 446, 184], fill=SCALE_DARK)
    draw.ellipse([468, 172, 484, 188], fill=SCALE_DARK)

    # Crimson bow. She is Cryptic Croc, and she is female.
    draw.polygon([(300, 78), (248, 48), (268, 108)], fill=CRIMSON)
    draw.polygon([(332, 78), (386, 46), (364, 112)], fill=CRIMSON)
    draw.ellipse([292, 64, 340, 112], fill=CRIMSON)
    draw.ellipse([304, 76, 328, 100], fill=CREAM)

    _eye(draw, 300, 130, blink, glance=8 if mood == "think" else 0)
    _eye(draw, 390, 124, blink, glance=8 if mood == "think" else 0)
    _lashes(draw, 300, 108)
    _lashes(draw, 390, 102)

    if mouth == 0 and mood != "cheer":
        draw.arc([390, 176, 490, 230], 20, 160, fill=SCALE_DARK, width=4)
    else:
        open_by = 16 + mouth * 8 + (10 if mood == "cheer" else 0)
        draw.pieslice([392, 168, 500, 188 + open_by], 10, 170, fill=(176, 64, 72))
        draw.rectangle([408, 186, 484, 196], fill=TOOTH)

    if mood == "wave":
        _arm(draw, 236, 214, -80 + wave)
    elif mood == "point":
        _arm(draw, 220, 200, -120)
    else:
        _arm(draw, 176, 268, 100)

    return canvas


def _eye(draw: ImageDraw.ImageDraw, x: int, y: int, blink: bool, glance: int) -> None:
    if blink:
        draw.arc([x - 22, y, x + 22, y + 16], 200, 340, fill=INK, width=4)
        return
    draw.ellipse([x - 22, y - 16, x + 22, y + 18], fill=CREAM, outline=INK, width=3)
    draw.ellipse([x - 8 + glance, y - 8, x + 8 + glance, y + 10], fill=INK)
    draw.ellipse([x - 2 + glance, y - 4, x + 4 + glance, y + 2], fill=CREAM)


def _lashes(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line([(x - 16, y + 8), (x - 24, y - 2)], fill=INK, width=3)
    draw.line([(x, y + 2), (x - 2, y - 10)], fill=INK, width=3)
    draw.line([(x + 16, y + 8), (x + 22, y - 2)], fill=INK, width=3)


def _arm(draw: ImageDraw.ImageDraw, x: int, y: int, angle: int) -> None:
    radians = math.radians(angle)
    reach = 70
    tip_x = x + int(math.cos(radians) * reach)
    tip_y = y + int(math.sin(radians) * reach)
    draw.line([(x, y), (tip_x, tip_y)], fill=SCALE_DARK, width=16)
    draw.ellipse([tip_x - 14, tip_y - 14, tip_x + 14, tip_y + 14], fill=SCALE)


def paste_croc(img: Image.Image, beat: str, frame: int) -> None:
    """Put Cryptic Croc on the card. She stays clear of the clue and the footer."""
    sprite = croc_sprite(beat, frame)
    bob = int(7 * math.sin(frame / 1.7))
    if beat in _BIG:
        sprite = sprite.resize((640, 566), Image.Resampling.LANCZOS)
        x = (img.width - sprite.width) // 2
        y = 1040 + bob
    else:
        sprite = sprite.resize((390, 345), Image.Resampling.LANCZOS)
        x = 28
        y = img.height - sprite.height - 70 + bob
    img.paste(sprite, (x, y), sprite)
