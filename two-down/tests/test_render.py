import subprocess
from pathlib import Path

from PIL import Image

from twodown.models import Clue
from twodown.render import (
    AUDIO_LOUDNESS,
    ShortTimings,
    _concat_motion,
    _encode_clips,
    _source_footer,
    draw_beat,
    draw_clue_card,
    draw_reveal_card,
    render_video,
)
from twodown.script import _spoken_parse, speak_answer, speak_enumeration, speak_intro


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


def _is_spoiler_red(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    return red > 150 and green < 80 and blue < 90


def _rgb_pixels(img: Image.Image):
    flat = getattr(img, "get_flattened_data", None)
    return flat() if flat else img.getdata()


def test_thumbnail_is_the_unsolved_clue(tmp_path: Path):
    from twodown.render import write_thumbnail

    thumb = write_thumbnail(_clue(), tmp_path / "thumb.jpg")
    web = write_thumbnail(_clue(), tmp_path / "poster.webp")
    letters = Image.open(draw_beat(_clue(), tmp_path / "letters.png", "letters")).convert("RGB")
    answer = Image.open(draw_beat(_clue(), tmp_path / "answer.png", "answer")).convert("RGB")
    assert thumb.suffix == ".jpg"
    assert web.suffix == ".webp"
    assert Image.open(thumb).size == (1080, 1920)
    assert thumb.stat().st_size < 2_000_000
    # Pixels that turn crimson only when the answer is drawn.
    spoilers = [
        index
        for index, (solved, unsolved) in enumerate(zip(_rgb_pixels(answer), _rgb_pixels(letters), strict=True))
        if _is_spoiler_red(solved) and not _is_spoiler_red(unsolved)
    ]
    assert len(spoilers) > 2000
    for poster in (Image.open(thumb).convert("RGB"), Image.open(web).convert("RGB")):
        pixels = list(_rgb_pixels(poster))
        leaked = sum(1 for index in spoilers if _is_spoiler_red(pixels[index]))
        assert leaked < len(spoilers) * 0.05


def test_cryptic_croc_moves_on_the_card(tmp_path: Path):
    from twodown.config import NEWS_BG
    from twodown.render import compose_beat

    talking = compose_beat(_clue(), "letters", 2)
    later = compose_beat(_clue(), "letters", 6)
    assert talking.size == (1080, 1920)
    assert talking.getpixel((24, 40)) == NEWS_BG
    assert talking.crop((20, 1400, 420, 1880)).tobytes() != later.crop((20, 1400, 420, 1880)).tobytes()
    greeting = compose_beat(_clue(), "intro", 3)
    assert greeting.crop((200, 1000, 880, 1700)).tobytes() != talking.crop((200, 1000, 880, 1700)).tobytes()


def test_clue_card_is_a_solve_along(tmp_path: Path):
    from PIL import Image

    from twodown.config import NEWS_BG

    path = draw_clue_card(_clue(), tmp_path / "clue.png", scene="kyoto")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    # Travel photos stay off the Short — the clue is the picture.
    assert img.getpixel((24, 40)) == NEWS_BG
    intro = draw_beat(_clue(), tmp_path / "intro.png", "intro")
    assert intro.exists()
    assert speak_intro(_clue()) == "Hello, here is your daily dose of AI cryptic crossword."
    assert "Today's clue is from" not in speak_intro(_clue())
    assert draw_beat(_clue(), tmp_path / "outro.png", "outro").exists()
    assert draw_beat(_clue(), tmp_path / "source.png", "source").exists()
    assert draw_beat(_clue(), tmp_path / "only-clue.png", "clue").exists()
    assert draw_beat(_clue(), tmp_path / "letters.png", "letters").exists()
    assert draw_beat(_clue(), tmp_path / "hint.png", "hint").exists()
    assert draw_beat(_clue(), tmp_path / "answer.png", "answer").exists()
    # Parse sits under the answer as soon as it is solved.
    assert draw_beat(_clue(), tmp_path / "solved.png", "answer").exists()


def test_intro_and_letters_show_unsolved_clue_and_empty_lights(tmp_path: Path):
    """The first beat is the unsolved clue and blank cells, not a title card."""
    from twodown.config import CREAM, INK

    intro = Image.open(draw_beat(_clue(), tmp_path / "intro.png", "intro")).convert("RGB")
    letters = Image.open(draw_beat(_clue(), tmp_path / "letters.png", "letters")).convert("RGB")
    think = Image.open(draw_beat(_clue(), tmp_path / "think.png", "think")).convert("RGB")
    answer = Image.open(draw_beat(_clue(), tmp_path / "answer.png", "answer")).convert("RGB")
    outro = Image.open(draw_beat(_clue(), tmp_path / "outro.png", "outro")).convert("RGB")

    clue_box = (80, 200, 1000, 580)
    intro_clue = list(_rgb_pixels(intro.crop(clue_box)))
    letters_clue = list(_rgb_pixels(letters.crop(clue_box)))
    think_clue = list(_rgb_pixels(think.crop(clue_box)))
    outro_clue = list(_rgb_pixels(outro.crop(clue_box)))
    assert intro_clue.count(INK) > 400
    assert abs(intro_clue.count(INK) - letters_clue.count(INK)) < 80
    assert abs(intro_clue.count(INK) - think_clue.count(INK)) < 80
    # Outro is the wisdom closer, not the clue text.
    assert abs(intro_clue.count(INK) - outro_clue.count(INK)) > 200

    lights = (80, 610, 1000, 740)
    intro_lights = list(_rgb_pixels(intro.crop(lights)))
    letters_lights = list(_rgb_pixels(letters.crop(lights)))
    think_lights = list(_rgb_pixels(think.crop(lights)))
    answer_lights = list(_rgb_pixels(answer.crop(lights)))
    assert intro_lights.count(CREAM) > 400
    assert abs(intro_lights.count(CREAM) - letters_lights.count(CREAM)) < 80
    assert abs(intro_lights.count(CREAM) - think_lights.count(CREAM)) < 80
    assert answer_lights.count(CREAM) < intro_lights.count(CREAM)

    raw = (tmp_path / "intro.png").read_bytes()
    assert b"PIN-UP" not in raw
    assert b"PINUP" not in raw

    def reddish(img: Image.Image, box: tuple[int, int, int, int]) -> int:
        return sum(1 for r, g, b in _rgb_pixels(img.crop(box)) if r > 140 and g < 80 and b < 90)

    # The crimson PIN-UP headline sits under the lights only on the answer card.
    assert reddish(answer, (80, 730, 1000, 880)) > reddish(intro, (80, 730, 1000, 880)) + 200
    assert reddish(letters, (80, 730, 1000, 880)) < reddish(answer, (80, 730, 1000, 880))


def test_answer_footer_credits_setter_and_paper():
    clue = _clue()
    assert _source_footer(clue) == "Eccles in the Independent"
    guardian = clue.model_copy(update={"setter": "Dice", "paper": "Guardian"})
    assert _source_footer(guardian) == "Dice in the Guardian"
    from twodown.pipeline import aimlessly_clue, cole_clue, davis_cup_clue, dreamlike_clue, fats_clue, mass_media_clue, rasta_clue, smiles_clue, study_clue, wellington_clue

    mass_media = mass_media_clue()
    assert mass_media.answer == "MASS MEDIA"
    assert _source_footer(mass_media) == "Arrietty in the Financial Times"
    aimlessly = aimlessly_clue()
    assert aimlessly.answer == "AIMLESSLY"
    assert _source_footer(aimlessly) == "Brendan in the Guardian"
    davis = davis_cup_clue()
    assert davis.answer == "DAVIS CUP"
    assert _source_footer(davis) == "Brendan in the Guardian"
    smiles = smiles_clue()
    assert smiles.answer == "SMILES"
    assert _source_footer(smiles) == "Brendan in the Guardian"
    cole = cole_clue()
    assert cole.answer == "COLE"
    assert _source_footer(cole) == "Brendan in the Guardian"
    wellington = wellington_clue()
    assert wellington.answer == "WELLINGTON"
    assert _source_footer(wellington) == "Brendan in the Guardian"
    fats = fats_clue()
    assert fats.answer == "FATS"
    assert _source_footer(fats) == "Brendan in the Guardian"
    rasta = rasta_clue()
    assert rasta.answer == "RASTA"
    assert _source_footer(rasta) == "Brendan in the Guardian"
    dreamlike = dreamlike_clue()
    assert dreamlike.answer == "DREAMLIKE"
    assert _source_footer(dreamlike) == "Brendan in the Guardian"
    assert _source_footer(study_clue()) == "Arrietty in the Financial Times"


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
    from twodown.hints import DEFAULT_HINT, FIELD, RASTA, TRANCE, ensure_hint_photo
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
    assert HINT_LINE == "Here's a hint."
    assert DEFAULT_HINT is None
    assert ensure_hint_photo(TRANCE).exists()
    assert ensure_hint_photo(RASTA).exists()
    assert ensure_hint_photo(FIELD).exists()
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


def test_published_pair_hint_beats_use_different_stills(tmp_path: Path):
    from PIL import Image

    from twodown.hints import BRING, USA
    from twodown.pipeline import published_clue

    elicit = published_clue("guardian-30124-9a")
    chicago = published_clue("independent-12473-1a")
    assert elicit.hint_image == f"assets/hints/{BRING.filename}"
    assert chicago.hint_image == f"assets/hints/{USA.filename}"
    elicit_hint = Image.open(draw_beat(elicit, tmp_path / "elicit-hint.png", "hint"))
    chicago_hint = Image.open(draw_beat(chicago, tmp_path / "chicago-hint.png", "hint"))
    elicit_photo = list(elicit_hint.crop((140, 1040, 940, 1580)).get_flattened_data())
    chicago_photo = list(chicago_hint.crop((140, 1040, 940, 1580)).get_flattened_data())
    assert elicit_photo != chicago_photo
    assert elicit_hint.getpixel((540, 1200)) != chicago_hint.getpixel((540, 1200))
    raw_elicit = (tmp_path / "elicit-hint.png").read_bytes()
    raw_chicago = (tmp_path / "chicago-hint.png").read_bytes()
    assert b"ELICIT" not in raw_elicit
    assert b"CHICAGO" not in raw_chicago


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
    assert speak_enumeration("5") == "Five letters."
    assert speak_enumeration("7") == "Seven letters."
    assert speak_enumeration("9") == "Nine letters."
    assert speak_enumeration("3-2") == "Three hyphen two."
    assert speak_enumeration("3,6") == "Three, six."


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
    assert speak_answer("AIMLESSLY") == "It's aimlessly."
    assert speak_answer("MASS MEDIA") == "It's mass media."
    assert _clue().answer == "PIN-UP"


def test_hint_card_keeps_empty_lights(tmp_path: Path):
    from PIL import Image

    from twodown.config import INK, NEWS_BG
    from twodown.pipeline import study_clue

    clue = study_clue()
    assert clue is not None
    assert clue.answer == "MASS MEDIA"
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


def test_bellhop_hint_beat_uses_generated_hotel_worker_still(tmp_path: Path):
    from PIL import Image

    from twodown.config import HINT_LINE, NEWS_BG
    from twodown.hints import PORTER, TRANCE, hint_for_clue
    from twodown.pipeline import published_clue

    clue = published_clue("independent-12458-11a")
    assert clue.answer == "BELLHOP"
    assert hint_for_clue(clue).slug == PORTER.slug
    assert clue.hint_line == HINT_LINE
    assert clue.hint_image == f"assets/hints/{PORTER.filename}"
    path = draw_beat(clue, tmp_path / "bellhop-hint.png", "hint")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    assert img.getpixel((24, 40)) == NEWS_BG
    raw = path.read_bytes()
    assert b"BELLHOP" not in raw
    assert b"bellhop" not in raw.lower()
    photo = img.crop((140, 1040, 940, 1580))
    assert any(pixel != NEWS_BG for pixel in photo.get_flattened_data())
    trance = Image.open(TRANCE.path).convert("RGB")
    assert img.getpixel((540, 1200)) != trance.getpixel((trance.size[0] // 2, trance.size[1] // 2))


def test_sphere_hint_beat_uses_the_globe_still(tmp_path: Path):
    from PIL import Image

    from twodown.config import CREAM, HINT_LINE, NEWS_BG
    from twodown.hints import FIELD, GLOBE, TRANCE, hint_for_clue
    from twodown.pipeline import published_clue

    clue = published_clue("financial-times-18478-5a")
    assert clue.answer == "SPHERE"
    assert hint_for_clue(clue).slug == GLOBE.slug
    assert clue.hint_line == HINT_LINE
    assert clue.hint_image == f"assets/hints/{GLOBE.filename}"
    path = draw_beat(clue, tmp_path / "sphere-hint.png", "hint")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    assert img.getpixel((24, 40)) == NEWS_BG
    lights = list(img.crop((80, 610, 1000, 740)).get_flattened_data())
    assert lights.count(CREAM) > 400
    raw = path.read_bytes()
    assert b"SPHERE" not in raw
    assert b"sphere" not in raw.lower()
    band = img.crop((140, 900, 940, 1280))
    newsprint = sum(1 for pixel in band.get_flattened_data() if pixel == NEWS_BG)
    assert newsprint < 20_000
    inset = img.getpixel((540, 1200))
    trance = Image.open(TRANCE.path).convert("RGB")
    field = Image.open(FIELD.path).convert("RGB")
    globe = Image.open(GLOBE.path).convert("RGB")
    assert inset != trance.getpixel((trance.size[0] // 2, trance.size[1] // 2))
    assert inset != field.getpixel((field.size[0] // 2, field.size[1] // 2))
    assert inset != NEWS_BG
    # Globe still is a dark orb on black, not a green meadow.
    assert inset[1] < 140 or inset[2] > inset[1]
    assert globe.size[0] >= 640


def test_unmatched_hint_beat_has_empty_lights_and_no_photo(tmp_path: Path):
    from PIL import Image

    from twodown.config import CREAM, NEWS_BG
    from twodown.hints import hint_for_clue
    from twodown.models import Clue

    blank = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="99999",
        setter="Phi",
        blogger="tester",
        number="12",
        direction="across",
        clue="Rioting led unrest in the final analysis",
        enumeration="3,6",
        answer="END RESULT",
        parse="Anagram of LED UNREST",
    )
    assert hint_for_clue(blank) is None
    path = draw_beat(blank, tmp_path / "miss-hint.png", "hint")
    img = Image.open(path)
    assert img.size == (1080, 1920)
    assert img.getpixel((24, 40)) == NEWS_BG
    lights = list(img.crop((80, 610, 1000, 740)).get_flattened_data())
    assert lights.count(CREAM) > 400
    band = img.crop((140, 1040, 940, 1580))
    newsprint = sum(1 for pixel in band.get_flattened_data() if pixel == NEWS_BG)
    assert newsprint > 200_000
    raw = path.read_bytes()
    assert b"END RESULT" not in raw


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
    video_d = float(_probe(dest, "format=duration"))
    audio_d = float(_probe(audio, "format=duration"))
    assert abs(video_d - audio_d) < 0.4
    assert _probe(dest, "stream=sample_rate") == "44100"
    assert _probe(dest, "stream=width,height").splitlines()[0] == "1080"
    assert "aac" in _probe(dest, "stream=codec_name")
    assert "loudnorm" in AUDIO_LOUDNESS
    assert "volume=" in AUDIO_LOUDNESS


def _solid_clip(path: Path, seconds: float, fps: float, colour: str) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={colour}:s=1080x1920:r={fps}",
            "-t",
            f"{seconds:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


def _frame_rgb(video: Path, at: float, dest: Path) -> tuple[int, int, int]:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{at:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return Image.open(dest).convert("RGB").getpixel((20, 20))


def test_concat_motion_keeps_clip_holds(tmp_path: Path):
    """Uneven timebases must not stretch the picture past the voice."""
    clips = [
        _solid_clip(tmp_path / "intro.mp4", 1.00, 6.02176, "red"),
        _solid_clip(tmp_path / "parse.mp4", 1.60, 5.88643, "green"),
        _solid_clip(tmp_path / "outro.mp4", 0.80, 5.87017, "blue"),
    ]
    audio = tmp_path / "voice.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "3.4",
            str(audio),
        ],
        check=True,
        capture_output=True,
    )
    dest = tmp_path / "short.mp4"
    _concat_motion(clips, audio, dest)
    video_d = float(_probe(dest, "format=duration"))
    audio_d = float(_probe(audio, "format=duration"))
    assert abs(video_d - audio_d) < 0.35
    listing = dest.with_suffix(".concat.txt").read_text(encoding="utf-8")
    assert "duration " in listing
    assert "outpoint " in listing
    red = _frame_rgb(dest, 0.25, tmp_path / "at-intro.png")
    green = _frame_rgb(dest, 1.70, tmp_path / "at-parse.png")
    blue = _frame_rgb(dest, 3.00, tmp_path / "at-outro.png")
    assert red[0] > 180 and red[1] < 40 and red[2] < 40
    assert green[1] > 100 and green[0] < 40 and green[2] < 40
    assert blue[2] > 180 and blue[0] < 40 and blue[1] < 40
    assert _probe(dest, "stream=codec_type").splitlines()[-1] == "audio"


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
