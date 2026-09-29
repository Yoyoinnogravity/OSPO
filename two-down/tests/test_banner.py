from PIL import Image

from twodown.banner import (
    BANNER_SIZE,
    MAX_BYTES,
    PICTURE_MAX_BYTES,
    PICTURE_SIZE,
    SAFE_SIZE,
    write_youtube_banner,
    write_youtube_picture,
)
from twodown.config import NEWS_BG


def test_youtube_banner_fits_the_channel_art_spec(tmp_path):
    path = write_youtube_banner(tmp_path / "youtube-banner.png")
    img = Image.open(path)
    assert img.size == BANNER_SIZE
    assert img.size[0] >= 2048 and img.size[1] >= 1152
    assert path.stat().st_size < MAX_BYTES
    width, height = img.size
    safe_w, safe_h = SAFE_SIZE
    left = (width - safe_w) // 2
    top = (height - safe_h) // 2
    safe = img.crop((left, top, left + safe_w, top + safe_h))
    samples = [safe.getpixel((x, y)) for x in range(0, safe_w, 24) for y in range(0, safe_h, 24)]
    assert any(green > red and green > 90 for red, green, _blue in samples)
    assert any(red > 150 and green < 70 for red, green, _blue in samples)
    assert safe.getpixel((8, 8)) == NEWS_BG


def test_youtube_picture_is_a_square_png(tmp_path):
    path = write_youtube_picture(tmp_path / "youtube-picture.png")
    img = Image.open(path).convert("RGB")
    assert path.suffix == ".png"
    assert img.size == (PICTURE_SIZE, PICTURE_SIZE)
    assert img.size[0] >= 98 and img.size[1] >= 98
    assert path.stat().st_size < PICTURE_MAX_BYTES
    # YouTube masks the square to a circle. The bow sits inside the ring.
    centre = PICTURE_SIZE / 2
    ring_inner = centre - 18 - 11
    bow = face = 0
    for y in range(0, PICTURE_SIZE, 2):
        for x in range(0, PICTURE_SIZE, 2):
            dist = ((x - centre) ** 2 + (y - centre) ** 2) ** 0.5
            red, green, _blue = img.getpixel((x, y))
            is_bow = red > 150 and green < 80
            is_face = green > red + 30 and green > 90
            if dist > centre - 1:
                assert not is_face
                assert not is_bow
            if y < centre and dist < ring_inner - 24 and is_bow:
                bow += 1
            if dist < ring_inner - 24 and is_face:
                face += 1
    assert bow > 20
    assert face > 400
