import subprocess
from pathlib import Path

from twodown.models import Clue
from twodown.render import _source_footer, draw_beat, draw_clue_card, draw_reveal_card, render_video
from twodown.script import speak_enumeration


def _clue() -> Clue:
    return Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12462",
        setter="Eccles",
        blogger="Quirister",
        number="6",
        direction="across",
        clue="Model youngster eating in",
        enumeration="3-2",
        answer="PIN-UP",
        parse="PUP containing IN",
        device="container",
        enumeration_ok=True,
    )


def _probe(path: Path, entries: str) -> str:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            entries,
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_clue_card_is_a_solve_along(tmp_path: Path):
    from PIL import Image

    from twodown.config import NEWS_BG

    path = draw_clue_card(_clue(), tmp_path / "clue.png", scene="kyoto")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    # Travel photos stay off the Short — the clue is the picture.
    assert img.getpixel((24, 40)) == NEWS_BG
    assert draw_beat(_clue(), tmp_path / "intro.png", "intro").exists()
    assert draw_beat(_clue(), tmp_path / "only-clue.png", "clue").exists()
    assert draw_beat(_clue(), tmp_path / "letters.png", "letters").exists()
    assert draw_beat(_clue(), tmp_path / "answer.png", "answer").exists()
    # Parse sits under the answer as soon as it is solved.
    assert draw_beat(_clue(), tmp_path / "solved.png", "answer").exists()


def test_answer_footer_credits_setter_paper_and_fifteen_squared():
    clue = _clue()
    assert _source_footer(clue) == "Eccles in the Independent · Fifteen Squared"
    guardian = clue.model_copy(update={"setter": "Dice", "paper": "Guardian"})
    assert _source_footer(guardian) == "Dice in the Guardian · Fifteen Squared"


def test_parse_under_answer_is_bold_ink(tmp_path: Path):
    from PIL import Image

    from twodown.config import FONT_SANS_BOLD, INK, MUTED
    from twodown.render import PARSE_FILL, PARSE_FONT, PARSE_MAX_LINES, PARSE_SIZE

    assert PARSE_FONT == FONT_SANS_BOLD
    assert 40 <= PARSE_SIZE <= 48
    assert PARSE_FILL == INK
    assert PARSE_MAX_LINES == 4

    path = draw_beat(_clue(), tmp_path / "answer.png", "answer")
    img = Image.open(path)
    # Parse sits just under the crimson PIN-UP headline — ink, not muted caption brown.
    band = list(img.crop((80, 830, 1000, 1100)).get_flattened_data())
    assert band.count(INK) > 400
    assert band.count(MUTED) == 0


def test_speak_enumeration_is_separate_from_the_clue():
    assert speak_enumeration("7") == "Seven letters."
    assert speak_enumeration("3-2") == "Three hyphen two."
    assert speak_enumeration("3,6") == "Three, six."


def test_render_video_is_browser_playable(tmp_path: Path):
    clue = _clue()
    clue_card = draw_clue_card(clue, tmp_path / "clue.png", scene="aurora")
    reveal = draw_reveal_card(clue, tmp_path / "reveal.png", scene="aurora")
    audio = tmp_path / "voice.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            "3",
            str(audio),
        ],
        check=True,
        capture_output=True,
    )
    dest = tmp_path / "short.mp4"
    render_video(clue_card, reveal, audio, dest, clue_hold=1.4, clue=clue)
    data = dest.read_bytes()
    assert 0 < data.find(b"moov") < data.find(b"mdat")
    assert _probe(dest, "stream=sample_rate") == "48000"
    assert _probe(dest, "stream=width,height").splitlines()[0] == "1080"
