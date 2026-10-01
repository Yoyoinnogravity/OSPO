import inspect

from twodown.config import INTRO_BUMPER, INTRO_LINE
from twodown.pipeline import mass_media_clue
from twodown.render import audio_seconds, intro_bumper_path, intro_bumper_seconds
from twodown.script import speak_intro, write_parts
from twodown.voice import build_short_soundtrack, extract_intro_bumper_audio, synthesise


def test_intro_bumper_is_the_recorded_invite():
    """Every Short opens on Aled's dictionary ident, not Andrew TTS or SSML."""
    path = intro_bumper_path()
    assert path == INTRO_BUMPER
    assert path.exists()
    assert path.suffix == ".mp4"
    hold = intro_bumper_seconds()
    assert hold > 0
    assert 4.5 <= hold <= 6.0
    assert audio_seconds(path) == hold
    raw = path.read_bytes()
    assert b"SPARKIEST" not in raw
    assert b"SPARKLIEST" not in raw
    assert b"BELLHOP" not in raw
    assert b"<speak" not in raw
    assert b"speak version" not in raw


def test_intro_bumper_audio_is_not_ssml(tmp_path):
    dest = tmp_path / "intro.mp3"
    extracted = extract_intro_bumper_audio(dest)
    assert extracted == dest
    assert dest.exists()
    assert audio_seconds(dest) > 0
    assert dest.stat().st_size > 1000
    source = inspect.getsource(build_short_soundtrack)
    assert "to_ssml" not in source
    assert "extract_intro_bumper_audio" in source
    assert "parts.intro_speech" not in source
    assert inspect.getsource(extract_intro_bumper_audio).count("synthesise(") == 0
    assert inspect.getsource(synthesise).count("plain speech") >= 1


def test_recorded_invite_does_not_stack_andrew_daily_dose():
    clue = mass_media_clue()
    parts = write_parts(clue)
    assert INTRO_LINE == "Hello, here is your daily dose of AI cryptic crossword."
    assert parts.intro_speech == INTRO_LINE
    assert parts.intro_speech == speak_intro(clue)
    assert "Hi, here is your daily dose of AI cryptic clues." not in parts.intro_speech
    assert "Today's clue is from" not in parts.intro_speech
    assert "Here's Cryptic Croc." not in parts.intro_speech
    assert "speak version" not in parts.full
    assert "<speak" not in parts.full
    assert "xmlns" not in parts.full
    assert parts.clue_speech == "Maid struggling with a mess — newspapers etc."
    assert parts.think_speech == "Pause here to think about it."
    assert parts.outro_speech.endswith("That was cryptic.fit.")
