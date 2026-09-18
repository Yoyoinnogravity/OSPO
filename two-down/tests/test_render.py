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
    assert draw_beat(_clue(), tmp_path / "source.png", "source").exists()
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
    from twodown.pipeline import cole_clue, davis_cup_clue, dreamlike_clue, fats_clue, rasta_clue, smiles_clue, study_clue, wellington_clue

    davis = davis_cup_clue()
    assert davis.answer == "DAVIS CUP"
    assert _source_footer(davis) == "Brendan in the Guardian · Fifteen Squared"
    smiles = smiles_clue()
    assert smiles.answer == "SMILES"
    assert _source_footer(smiles) == "Brendan in the Guardian · Fifteen Squared"
    cole = cole_clue()
    assert cole.answer == "COLE"
    assert _source_footer(cole) == "Brendan in the Guardian · Fifteen Squared"
    wellington = wellington_clue()
    assert wellington.answer == "WELLINGTON"
    assert _source_footer(wellington) == "Brendan in the Guardian · Fifteen Squared"
    fats = fats_clue()
    assert fats.answer == "FATS"
    assert _source_footer(fats) == "Brendan in the Guardian · Fifteen Squared"
    rasta = rasta_clue()
    assert rasta.answer == "RASTA"
    assert _source_footer(rasta) == "Brendan in the Guardian · Fifteen Squared"
    dreamlike = dreamlike_clue()
    assert dreamlike.answer == "DREAMLIKE"
    assert _source_footer(dreamlike) == "Brendan in the Guardian · Fifteen Squared"
    assert _source_footer(study_clue()) == "Brendan in the Guardian · Fifteen Squared"


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
        source=3.0,
        outro=2.0,
    )
    assert timings.until_answer == 20.0
    assert timings.until_answer == timings.intro + timings.clue + timings.letters + timings.think + timings.hint


def test_hint_beat_is_newsprint_with_credited_photo(tmp_path: Path):
    from PIL import Image

    from twodown.config import HINT_LINE, NEWS_BG
    from twodown.hints import DEFAULT_HINT, RASTA, TRANCE, ensure_hint_photo
    from twodown.pipeline import dreamlike_clue, rasta_clue

    clue = dreamlike_clue()
    assert clue.answer == "DREAMLIKE"
    path = draw_beat(clue, tmp_path / "hint.png", "hint")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    # Newsprint card, not a full-bleed travel still.
    assert img.getpixel((24, 40)) == NEWS_BG
    assert img.getpixel((24, 40)) != (0, 0, 0)
    # The inset photo is not the cream grid.
    photo = img.getpixel((540, 1050))
    assert photo != NEWS_BG
    assert clue.hint_credit == TRANCE.credit_line
    assert "DREAMLIKE" not in (clue.hint_credit or "")
    assert HINT_LINE == "Have a look at this."
    assert DEFAULT_HINT.source == "generated still"
    assert ensure_hint_photo(TRANCE).exists()
    assert ensure_hint_photo(RASTA).exists()
    assert rasta_clue().answer == "RASTA"


def test_hint_beat_does_not_spoil_rasta(tmp_path: Path):
    from PIL import Image

    from twodown.config import CREAM, CRIMSON
    from twodown.pipeline import rasta_clue

    clue = rasta_clue()
    assert clue.answer == "RASTA"
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

    def reddish(img: Image.Image) -> int:
        return sum(1 for r, g, b in img.get_flattened_data() if r > 140 and g < 80 and b < 90)

    # The 84pt RASTA headline sits just under the lights on the answer card.
    hint_head = reddish(hint.crop((80, 730, 1000, 880)))
    answer_head = reddish(answer.crop((80, 730, 1000, 880)))
    assert answer_head > hint_head + 200
    assert CRIMSON[0] > 140
    raw = (tmp_path / "hint.png").read_bytes()
    assert b"RASTA" not in raw
    assert b"rasta" not in raw.lower()


def test_hint_beat_does_not_spoil_dreamlike(tmp_path: Path):
    from PIL import Image

    from twodown.config import CREAM, CRIMSON
    from twodown.pipeline import dreamlike_clue

    clue = dreamlike_clue()
    hint = Image.open(draw_beat(clue, tmp_path / "hint.png", "hint"))
    think = Image.open(draw_beat(clue, tmp_path / "think.png", "think"))
    answer = Image.open(draw_beat(clue, tmp_path / "answer.png", "answer"))
    hint_lights = list(hint.crop((80, 610, 1000, 740)).get_flattened_data())
    think_lights = list(think.crop((80, 610, 1000, 740)).get_flattened_data())
    answer_lights = list(answer.crop((80, 610, 1000, 740)).get_flattened_data())
    assert hint_lights.count(CREAM) > 400
    assert abs(hint_lights.count(CREAM) - think_lights.count(CREAM)) < 80
    assert answer_lights.count(CREAM) < hint_lights.count(CREAM)

    def reddish(img: Image.Image) -> int:
        return sum(1 for r, g, b in img.get_flattened_data() if r > 140 and g < 80 and b < 90)

    hint_head = reddish(hint.crop((80, 730, 1000, 880)))
    answer_head = reddish(answer.crop((80, 730, 1000, 880)))
    assert answer_head > hint_head + 200
    assert CRIMSON[0] > 140
    raw = (tmp_path / "hint.png").read_bytes()
    assert b"DREAMLIKE" not in raw
    assert b"dreamlike" not in raw.lower()


def test_speak_enumeration_is_separate_from_the_clue():
    assert speak_enumeration("5") == "That's five letters."
    assert speak_enumeration("7") == "That's seven letters."
    assert speak_enumeration("9") == "That's nine letters."
    assert speak_enumeration("3-2") == "That's three hyphen two."
    assert speak_enumeration("3,6") == "That's three, six."


def test_speak_answer_is_a_word_not_letters():
    assert speak_answer("PIN-UP") == "It's pin-up."
    assert speak_answer("SMASH-UP") == "It's smash-up."
    assert speak_answer("END RESULT") == "It's end result."
    assert speak_answer("DREAMLIKE") == "It's dreamlike."
    assert speak_answer("RASTA") == "It's rasta."
    assert speak_answer("FATS") == "It's fats."
    assert speak_answer("WELLINGTON") == "It's wellington."
    assert speak_answer("COLE") == "It's cole."
    assert speak_answer("SMILES") == "It's smiles."
    assert speak_answer("DAVIS CUP") == "It's davis cup."
    assert _clue().answer == "PIN-UP"


def test_hint_card_keeps_empty_lights(tmp_path: Path):
    from PIL import Image

    from twodown.config import INK, NEWS_BG
    from twodown.pipeline import study_clue

    clue = study_clue()
    assert clue is not None
    assert clue.answer == "DAVIS CUP"
    hint = draw_beat(clue, tmp_path / "hint.png", "hint")
    answer = draw_beat(clue, tmp_path / "answer.png", "answer")
    hint_img = Image.open(hint)
    answer_img = Image.open(answer)
    assert hint_img.size == (1080, 1920)
    assert hint_img.getpixel((24, 40)) == NEWS_BG
    lights = (80, 600, 1000, 780)
    assert list(hint_img.crop(lights).get_flattened_data()).count(INK) < list(
        answer_img.crop(lights).get_flattened_data()
    ).count(INK)
    # Inset still is not newsprint; the picture is the hint.
    photo = hint_img.crop((140, 980, 940, 1480))
    assert any(pixel != NEWS_BG for pixel in photo.get_flattened_data())


def test_dreamlike_parse_fits_under_the_answer(tmp_path: Path):
    from PIL import Image, ImageDraw

    from twodown.config import FONT_SANS_BOLD, INK
    from twodown.pipeline import dreamlike_clue, rasta_clue
    from twodown.render import PARSE_FONT, PARSE_MAX_LINES, PARSE_SIZE, WIDTH, _font, _wrap

    clue = dreamlike_clue()
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

    rasta = rasta_clue()
    rasta_path = draw_beat(rasta, tmp_path / "rasta-answer.png", "answer")
    rasta_img = Image.open(rasta_path)
    rasta_band = list(rasta_img.crop((80, 830, 1000, 1500)).get_flattened_data())
    assert rasta_band.count(INK) > 800
    rasta_wrapped = _wrap(draw, _spoken_parse(rasta.parse, rasta.answer), parse_font, WIDTH - 160)
    rasta_lines = [line for line in rasta_wrapped.split("\n") if line.strip()]
    assert 1 <= len(rasta_lines) <= PARSE_MAX_LINES
    assert "tsar" in rasta_wrapped.lower() or "TSAR" in rasta_wrapped


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
    assert _probe(dest, "stream=sample_rate") == "44100"
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
