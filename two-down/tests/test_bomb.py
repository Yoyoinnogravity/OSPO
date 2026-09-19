from zipfile import ZipFile

from twodown.bomb import (
    how_to_bomb,
    public_record,
    render_bomb_videos,
    write_bomb_zip,
)
from twodown.captions import youtube_drop_description
from twodown.cli import main
from twodown.config import LOCKED_SLUGS, PINUP_SLUG, SELF_SLUG
from twodown.models import Clue
from twodown.pipeline import published_clue
from twodown.youtube import video_title


def _clue(answer: str = "END RESULT", number: str = "12", slug_paper: str = "Independent") -> Clue:
    return Clue(
        source_url="https://fifteensquared.net/example/",
        paper=slug_paper,
        puzzle_id="12458",
        setter="Phi",
        blogger="duncanshiell",
        number=number,
        direction="across",
        clue="Rioting led unrest in the final analysis",
        enumeration="3,6",
        answer=answer,
        parse="Anagram of LED UNREST",
        device="anagram",
        enumeration_ok=True,
    )


def test_public_record_and_description_hide_the_answer():
    clue = _clue()
    row = public_record(clue, index=1, total=100, video=None)
    text = " ".join(str(v) for v in row.values())
    assert "END RESULT" not in text
    assert "Rioting led unrest" in str(row["clue"])
    assert str(row["title"]) == video_title(clue)
    assert "END RESULT" not in youtube_drop_description(clue)
    assert "Have a think" in youtube_drop_description(clue)
    assert "#Shorts" in str(row["title"])


def test_how_to_bomb_is_youtube_drag_drop():
    text = how_to_bomb()
    assert text == "https://www.youtube.com/upload\n\nDrag every mp4.\n"
    assert "PIN-UP" not in text
    assert "END RESULT" not in text


def test_locked_homepage_pair_is_never_recut(tmp_path, monkeypatch):
    pinup = published_clue(PINUP_SLUG)
    self_clue = published_clue(SELF_SLUG)
    assert {pinup.slug, self_clue.slug} == set(LOCKED_SLUGS)
    called: list[str] = []

    def fake_render(slug, dest=None, publish=True, clue=None):
        called.append(slug)
        raise AssertionError("locked Shorts must not be recut")

    monkeypatch.setattr("twodown.bomb.render_one_short", fake_render)
    records = render_bomb_videos([pinup, self_clue], dest=tmp_path, rebuild=True, workers=1)
    assert called == []
    assert len(records) == 2
    assert all(row.get("video") for row in records)
    assert "PIN-UP" not in str(records[0]["title"])
    assert "SELF" not in str(records[1]["title"])


def test_write_bomb_zip_has_titles_no_answers(tmp_path):
    clue = _clue()
    film = tmp_path / "film.mp4"
    film.write_bytes(b"fake-mp4-bytes-here")
    row = public_record(clue, index=7, total=100, video=str(film))
    dest = tmp_path / "youtube-100.zip"
    write_bomb_zip([row], dest)
    with ZipFile(dest) as zf:
        names = set(zf.namelist())
        how = zf.read("HOW.txt").decode("utf-8")
        titles = zf.read("YOUTUBE-TITLES.txt").decode("utf-8")
        paste = zf.read("007-independent-12458-12a.txt").decode("utf-8")
    assert "007-independent-12458-12a.mp4" in names
    assert "HOW.txt" in names
    assert "END RESULT" not in how
    assert "END RESULT" not in titles
    assert "END RESULT" not in paste
    assert "Rioting led unrest" in paste
    assert paste.splitlines()[0] == video_title(clue)


def test_twodown_bomb_is_wired():
    try:
        main(["bomb", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
