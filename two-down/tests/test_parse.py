from datetime import datetime
from pathlib import Path

from twodown.devices import classify_device
from twodown.ingest import LONDON, parse_title
from twodown.models import PuzzlePost
from twodown.parse import parse_post, usable
from twodown.script import speak_enumeration, to_ssml, write_parts, write_script
from twodown.select import select_pair

FIXTURES = Path(__file__).parent / "fixtures"


def _post(html: str, paper: str = "Independent", puzzle_id: str = "12458", setter: str = "Phi") -> PuzzlePost:
    return PuzzlePost(
        post_id=1,
        url="https://fifteensquared.net/example/",
        title=f"{paper} {puzzle_id} / {setter}",
        date=datetime(2026, 9, 11, 7, 0, tzinfo=LONDON),
        paper=paper,
        puzzle_id=puzzle_id,
        setter=setter,
        blogger="duncanshiell",
        category_slugs=["independent"],
        html=html,
    )


def test_parse_independent_detail_table():
    html = (FIXTURES / "independent_detail.html").read_text(encoding="utf-8")
    clues = parse_post(_post(html))
    by_num = {c.number: c for c in clues}
    end = by_num["12"]
    assert end.answer == "END RESULT"
    assert end.enumeration == "3,6"
    assert end.enumeration_ok
    assert end.device == "anagram"
    assert "LED UNREST" in end.parse
    assert end.skipped_reason is None
    nereids = by_num["10"]
    assert nereids.answer == "NEREIDS"
    assert nereids.skipped_reason == "cross-reference"


def test_parse_three_column_skips_see_n():
    html = (FIXTURES / "guardian_three_col.html").read_text(encoding="utf-8")
    clues = parse_post(_post(html, paper="Guardian", puzzle_id="30108", setter="Paul"))
    usable_clues = usable(clues)
    answers = {c.answer for c in usable_clues}
    assert "PIE CRUST" in answers
    assert "IMPORTED" in answers
    assert "TWINKLETOES" not in answers
    pie = next(c for c in clues if c.answer == "PIE CRUST")
    assert pie.device == "anagram"
    assert pie.definition == "One’s filled"


def test_select_pair_prefers_device_contrast():
    html = (FIXTURES / "guardian_three_col.html").read_text(encoding="utf-8")
    clues = parse_post(_post(html, paper="Guardian", puzzle_id="30108", setter="Paul"))
    pair = select_pair(clues, n=2)
    assert len(pair) == 2
    assert pair[0].device != pair[1].device


def test_script_credits_fifteen_squared():
    html = (FIXTURES / "independent_detail.html").read_text(encoding="utf-8")
    clue = next(c for c in parse_post(_post(html)) if c.number == "12")
    script = write_script(clue)
    assert "Fifteen Squared" in script
    assert "END RESULT" in script
    assert "Phi" in script
    assert "cryptic.fun" in script
    parts = write_parts(clue)
    assert parts.clue_speech == f"{clue.clue}."
    assert "The clue:" not in parts.clue_speech
    assert "(" not in parts.clue_speech
    assert parts.letters_speech == speak_enumeration(clue.enumeration)
    assert parts.think_speech == "Pause the video while you think."
    assert parts.answer_speech == f"The answer is {clue.answer}."
    assert "END RESULT" in parts.breakdown
    assert "Fifteen Squared" in parts.parse_speech
    assert script.index(parts.clue_speech) < script.index(parts.letters_speech)
    assert script.index(parts.letters_speech) < script.index("[pause 1s]")
    assert script.index("[pause 1s]") < script.index(parts.think_speech)
    assert script.index(parts.think_speech) < script.index("[pause 7s]")
    assert script.index("[pause 7s]") < script.index(parts.answer_speech)
    assert script.index(parts.answer_speech) < script.index(parts.parse_speech)
    ssml = to_ssml(parts)
    assert ssml.index(parts.clue_speech) < ssml.index('break time="350ms"')
    assert ssml.index('break time="350ms"') < ssml.index(parts.letters_speech)
    assert ssml.index(parts.letters_speech) < ssml.index('break time="1000ms"')
    assert ssml.index('break time="1000ms"') < ssml.index(parts.think_speech)
    assert ssml.index(parts.think_speech) < ssml.index('break time="7000ms"')
    assert ssml.index('break time="7000ms"') < ssml.index(parts.answer_speech)
    assert ssml.index(parts.answer_speech) < ssml.index('break time="1200ms"')
    assert ssml.index('break time="1200ms"') < ssml.index("Fifteen Squared")


def test_parse_title_variants():
    assert parse_title("Independent 12458 / Phi") == ("Independent", "12458", "Phi")
    assert parse_title("Financial Times 18,477 by NEO") == ("Financial Times", "18477", "NEO")
    assert parse_title("Guardian Cryptic crossword No 30,108 by Paul") == ("Guardian", "30108", "Paul")
    assert parse_title("Independent on Sunday 1,907 by Filbert") == (
        "Independent on Sunday",
        "1907",
        "Filbert",
    )


def test_classify_anagram():
    assert classify_device("anagram of LED UNREST") == "anagram"
    assert classify_device("hidden answer in the clue") == "hidden"
