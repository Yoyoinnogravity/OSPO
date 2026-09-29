from PIL import Image

from twodown.banner import BANNER_SIZE, MAX_BYTES, SAFE_SIZE, write_youtube_banner
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
