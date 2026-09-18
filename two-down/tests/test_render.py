import subprocess
from pathlib import Path

from twodown.models import Clue
from twodown.render import (
    AUDIO_LOUDNESS,
    ShortTimings,
    _encode_clips,
    _source_footer,
    draw_beat,
    draw_clue_card,
    draw_reveal_card,
    render_video,
)
from twodown.script import _spoken_parse, speak_answer, speak_enumeration


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
    assert draw_beat(_clue(), tmp_path / "outro.png", "outro").exists()
    assert draw_beat(_clue(), tmp_path / "only-clue.png", "clue").exists()
    assert draw_beat(_clue(), tmp_path / "letters.png", "letters").exists()
    assert draw_beat(_clue(), tmp_path / "hint.png", "hint").exists()
    assert draw_beat(_clue(), tmp_path / "answer.png", "answer").exists()
    # Parse sits under the answer as soon as it is solved.
    assert draw_beat(_clue(), tmp_path / "solved.png", "answer").exists()


def test_answer_footer_credits_setter_paper_and_fifteen_squared():
    clue = _clue()
    assert _source_footer(clue) == "Eccles in the Independent · Fifteen Squared"
    guardian = clue.model_copy(update={"setter": "Dice", "paper": "Guardian"})
    assert _source_footer(guardian) == "Dice in the Guardian · Fifteen Squared"
    from twodown.pipeline import study_clue

    dreamlike = study_clue()
    assert dreamlike is not None
    assert _source_footer(dreamlike) == "Brendan in the Guardian · Fifteen Squared"


def test_parse_under_answer_is_very_bold_ink(tmp_path: Path):
    from PIL import Image, ImageDraw

    from twodown.config import FONT_SANS_BOLD, INK, MUTED
    from twodown.render import (
        PARSE_FILL,
        PARSE_FONT,
        PARSE_MAX_LINES,
        PARSE_SIZE,
        PARSE_SPACING,
        WIDTH,
        _font,
        _wrap,
    )

    assert PARSE_FONT == FONT_SANS_BOLD
    assert 56 <= PARSE_SIZE <= 64
    assert PARSE_FILL == INK
    assert PARSE_MAX_LINES == 5
    assert PARSE_SPACING >= 16

    path = draw_beat(_clue(), tmp_path / "answer.png", "answer")
    img = Image.open(path)
    # Parse sits just under the crimson PIN-UP headline — ink, not muted caption brown.
    band = list(img.crop((80, 830, 1000, 1500)).get_flattened_data())
    assert band.count(INK) > 800
    assert band.count(MUTED) == 0

    from twodown.config import PINUP_SLUG
    from twodown.pipeline import published_clue

    pinup = published_clue(PINUP_SLUG)
    probe = Image.new("RGB", (WIDTH, 200))
    draw = ImageDraw.Draw(probe)
    parse_font = _font(PARSE_FONT, PARSE_SIZE)
    wrapped = _wrap(draw, _spoken_parse(pinup.parse, pinup.answer), parse_font, WIDTH - 160)
    lines = [line for line in wrapped.split("\n") if line.strip()]
    assert 3 <= len(lines) <= 5


def test_short_timings_include_hint_before_answer():
    timings = ShortTimings(
        intro=1.0,
        clue=2.0,
        letters=1.5,
        think=8.0,
        hint=7.5,
        answer=3.0,
        parse=5.0,
        outro=2.0,
    )
    assert timings.until_answer == 20.0
    assert timings.until_answer == timings.intro + timings.clue + timings.letters + timings.think + timings.hint


def test_hint_beat_is_newsprint_with_credited_photo(tmp_path: Path):
    from PIL import Image

    from twodown.config import HINT_LINE, NEWS_BG
    from twodown.hints import DEFAULT_HINT
    from twodown.pipeline import study_clue

    clue = study_clue()
    assert clue is not None
    path = draw_beat(clue, tmp_path / "hint.png", "hint")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    # Newsprint card, not a full-bleed travel still.
    assert img.getpixel((24, 40)) == NEWS_BG
    assert img.getpixel((24, 40)) != (0, 0, 0)
    # The inset photo is darker than the cream grid.
    photo = img.getpixel((540, 1050))
    assert photo != NEWS_BG
    assert DEFAULT_HINT.photographer == "Linda Xu"
    assert DEFAULT_HINT.license == "CC0"
    assert "Wikimedia Commons" in DEFAULT_HINT.credit_line
    assert HINT_LINE == "Here's a clue."
    assert DEFAULT_HINT.path.exists()


def test_hint_beat_does_not_spoil_dreamlike(tmp_path: Path):
    from PIL import Image

    from twodown.config import CREAM, CRIMSON
    from twodown.pipeline import study_clue

    clue = study_clue()
    assert clue is not None
    assert clue.answer == "DREAMLIKE"
    hint = Image.open(draw_beat(clue, tmp_path / "hint.png", "hint"))
    think = Image.open(draw_beat(clue, tmp_path / "think.png", "think"))
    answer = Image.open(draw_beat(clue, tmp_path / "answer.png", "answer"))
    # Lights sit in the same band on think and hint — empty cream cells, not filled letters.
    hint_lights = list(hint.crop((80, 610, 1000, 740)).get_flattened_data())
    think_lights = list(think.crop((80, 610, 1000, 740)).get_flattened_data())
    answer_lights = list(answer.crop((80, 610, 1000, 740)).get_flattened_data())
    assert hint_lights.count(CREAM) > 400
    assert abs(hint_lights.count(CREAM) - think_lights.count(CREAM)) < 80
    assert answer_lights.count(CREAM) < hint_lights.count(CREAM)
    # The crimson DREAMLIKE headline lives on the answer card only.
    hint_head = list(hint.crop((80, 880, 1000, 1080)).get_flattened_data())
    answer_head = list(answer.crop((80, 880, 1000, 1080)).get_flattened_data())
    assert answer_head.count(CRIMSON) > hint_head.count(CRIMSON) + 200
    raw = path_bytes = (tmp_path / "hint.png").read_bytes()
    assert b"DREAMLIKE" not in path_bytes
    assert b"dreamlike" not in raw.lower()


def test_speak_enumeration_is_separate_from_the_clue():
    assert speak_enumeration("7") == "Seven letters."
    assert speak_enumeration("9") == "Nine letters."
    assert speak_enumeration("3-2") == "Three hyphen two."
    assert speak_enumeration("3,6") == "Three, six."


def test_speak_answer_is_a_word_not_letters():
    assert speak_answer("PIN-UP") == "The answer is pin-up."
    assert speak_answer("SMASH-UP") == "The answer is smash-up."
    assert speak_answer("END RESULT") == "The answer is end result."
    assert speak_answer("DREAMLIKE") == "The answer is dreamlike."
    assert _clue().answer == "PIN-UP"


def test_dreamlike_parse_fits_under_the_answer(tmp_path: Path):
    from PIL import Image, ImageDraw

    from twodown.config import FONT_SANS_BOLD, INK
    from twodown.pipeline import study_clue
    from twodown.render import PARSE_FONT, PARSE_MAX_LINES, PARSE_SIZE, WIDTH, _font, _wrap

    clue = study_clue()
    assert clue is not None
    assert clue.answer == "DREAMLIKE"
    path = draw_beat(clue, tmp_path / "dreamlike-answer.png", "answer")
    img = Image.open(path)
    band = list(img.crop((80, 830, 1000, 1500)).get_flattened_data())
    assert band.count(INK) > 800

    probe = Image.new("RGB", (WIDTH, 200))
    draw = ImageDraw.Draw(probe)
    parse_font = _font(PARSE_FONT, PARSE_SIZE)
    wrapped = _wrap(draw, _spoken_parse(clue.parse, clue.answer), parse_font, WIDTH - 160)
    lines = [line for line in wrapped.split("\n") if line.strip()]
    assert 1 <= len(lines) <= PARSE_MAX_LINES
    assert PARSE_SIZE == 60
    assert PARSE_FONT == FONT_SANS_BOLD


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
    assert "aac" in _probe(dest, "stream=codec_name")
    assert "loudnorm" in AUDIO_LOUDNESS
    assert "volume=" in AUDIO_LOUDNESS


def test_encode_maps_loud_audio(tmp_path: Path):
    from PIL import Image

    frame = tmp_path / "frame.png"
    Image.new("RGB", (1080, 1920), (243, 234, 214)).save(frame)
    quiet = tmp_path / "quiet.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=24000",
            "-t",
            "2",
            "-filter:a",
            "volume=-24dB",
            str(quiet),
        ],
        check=True,
        capture_output=True,
    )
    dest = tmp_path / "loud.mp4"
    _encode_clips([(frame, 2.0)], quiet, dest)
    assert _probe(dest, "stream=codec_type").splitlines()[-1] == "audio"
    measure = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(dest),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    mean_line = next(line for line in measure.stderr.splitlines() if "mean_volume" in line)
    mean_db = float(mean_line.rsplit(":", 1)[-1].strip().split()[0])
    assert mean_db > -20.0
