from zipfile import ZipFile

from twodown.cli import main
from twodown.drop import collect_drops, drop_caption, how_to_invade, write_drop_pack
from twodown.models import DailyPair
from twodown.pipeline import site_pair


def test_drop_caption_does_not_spoil():
    text = drop_caption("Name of girl making second statement on first birthday (6)", "Guardian 30115 · Brendan")
    assert "SIMONE" not in text
    assert "Name of girl" in text
    assert "Cryptic AI for Fun" in text
    assert "#crypticaiforfun" in text


def test_how_to_invade_names_all_four():
    text = how_to_invade()
    assert "YouTube" in text
    assert "Facebook" in text
    assert "Instagram" in text
    assert "TikTok" in text
    assert "@crypticaiforfun" in text
    assert "@crypticfun" in text  # the warning
    assert "Do not use @crypticfun" in text
    assert text.index("tiktok.com/signup") < text.index("youtube.com/create_channel")


def test_write_drop_pack_from_published_site(tmp_path):
    pair = site_pair("2026-09-16")
    dest = tmp_path / "drop.zip"
    write_drop_pack(pair, dest)
    with ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert "HOW.txt" in names
    assert "independent-12462-6a.mp4" in names
    assert "independent-12462-6a.txt" in names
    assert "guardian-30115-23d.mp4" in names
    caption = ZipFile(dest).read("guardian-30115-23d.txt").decode("utf-8")
    assert "SIMONE" not in caption
    assert "Name of girl" in caption
    how = ZipFile(dest).read("HOW.txt").decode("utf-8")
    assert "PIN-UP" not in how
    films = collect_drops(pair)
    assert {film.slug for film in films} >= {
        "independent-12462-6a",
        "guardian-30113-9a",
        "guardian-30115-23d",
        "financial-times-18483-26a",
        "financial-times-18483-1a",
    }


def test_twodown_drop_writes_zip(tmp_path):
    dest = tmp_path / "invade.zip"
    assert main(["drop", "--out", str(dest), "--date", "2026-09-16"]) == 0
    assert dest.exists()
    assert dest.stat().st_size > 1000


def test_collect_drops_skips_missing_extras(tmp_path):
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[])
    assert collect_drops(pair, tmp_path) == []
