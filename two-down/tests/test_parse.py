from datetime import datetime
from pathlib import Path

from twodown.devices import classify_device
from twodown.ingest import LONDON, parse_title
from twodown.models import PuzzlePost
from twodown.parse import parse_post, usable
from twodown.config import OUTRO_LINE, THINK_PROMPT, WISDOM_LINES, pick_wisdom
from twodown.script import speak_answer, speak_enumeration, speak_outro, to_ssml, write_parts, write_script
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


def test_highlighted_letter_stays_out_of_the_previous_word():
    """Guardian wraps the deleted letter in <strong><em>, splitting the word."""
    html = """
    <table><tbody>
    <tr><td colspan="3">ACROSS</td></tr>
    <tr>
      <td>9</td>
      <td><span>ELICIT</span></td>
      <td><div>Bring out client I fancy with no end of distinction (6)</div></td>
    </tr>
    <tr>
      <td colspan="2"></td>
      <td>anagram/“fancy” of (clie<strong><em>n</em></strong>t I)*, without the
      <strong><em>n</em></strong> (“no end of distinctio-<strong><em>n</em></strong>“)</td>
    </tr>
    </tbody></table>
    """
    clue = next(c for c in parse_post(_post(html, paper="Guardian", puzzle_id="30124", setter="Chandler")))
    assert clue.answer == "ELICIT"
    assert "(client I)*" in clue.parse
    assert "without the n" in clue.parse
    assert "without then" not in clue.parse
    assert "distinction" in clue.parse
    parts = write_parts(clue)
    assert parts.intro_speech == (
        "Hi, here is your daily dose of AI cryptic clues. "
        "Today's clue is from the Guardian, by Chandler."
    )
    assert parts.source_speech == ""
    assert "without then" not in parts.parse_speech
    assert "client" in parts.parse_speech.lower()
    assert "anagram indicator" in parts.parse_speech.lower()
    assert "no end of distinction" in parts.parse_speech.lower()
    assert '"' not in parts.parse_speech


def test_letter_spans_rejoin():
    html = "<p>c<span>l</span><span>i</span>e</p>"
    from bs4 import BeautifulSoup

    from twodown.parse import _smart_strings

    node = BeautifulSoup(html, "lxml").p
    assert _smart_strings(node) == "clie"


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


def test_script_opens_with_the_paper_and_setter():
    html = (FIXTURES / "independent_detail.html").read_text(encoding="utf-8")
    clue = next(c for c in parse_post(_post(html)) if c.number == "12")
    script = write_script(clue)
    assert "Fifteen Squared" not in script
    assert clue.answer == "END RESULT"
    assert "end result" in script
    assert "Phi" in script
    assert "cryptic.fit" in script
    parts = write_parts(clue)
    assert parts.intro_speech == (
        "Hi, here is your daily dose of AI cryptic clues. "
        "Today's clue is from the Independent, by Phi."
    )
    assert parts.clue_speech == f"{clue.clue}."
    assert "The clue:" not in parts.clue_speech
    assert "(" not in parts.clue_speech
    assert parts.letters_speech == speak_enumeration(clue.enumeration)
    assert THINK_PROMPT == "Pause here to think about it."
    assert parts.think_speech == THINK_PROMPT
    assert parts.think_speech == "Pause here to think about it."
    assert "Have a think." not in script
    assert parts.hint_speech == ""
    assert "Here's a hint" not in script
    assert "No relevant image found" not in script
    assert parts.answer_speech == speak_answer(clue.answer)
    assert parts.answer_speech == "It's end result."
    assert "end result" in parts.breakdown
    assert "Fifteen Squared" not in parts.parse_speech
    assert parts.source_speech == ""
    assert "That's Phi" not in script
    assert "Independent" in parts.intro_speech
    assert "Phi" in parts.intro_speech
    assert parts.outro_speech == speak_outro(clue)
    assert parts.outro_speech == f"{pick_wisdom(clue.slug)} {OUTRO_LINE}"
    assert pick_wisdom(clue.slug) in WISDOM_LINES
    assert parts.outro_speech.endswith(OUTRO_LINE)
    assert "That's Phi" not in parts.outro_speech
    assert script.index(parts.intro_speech) < script.index(parts.clue_speech)
    assert script.index(parts.clue_speech) < script.index(parts.letters_speech)
    assert script.index(parts.letters_speech) < script.index("[pause 1s]")
    assert script.index("[pause 1s]") < script.index(parts.think_speech)
    assert script.index(parts.think_speech) < script.index("[pause 3s]")
    assert script.index("[pause 3s]") < script.index(parts.answer_speech)
    assert "[pause 2s]" not in script
    assert script.index(parts.answer_speech) < script.index(parts.parse_speech)
    assert script.index(parts.parse_speech) < script.index(parts.outro_speech)
    ssml = to_ssml(parts)
    first_800 = ssml.index('break time="800ms"')
    second_800 = ssml.index('break time="800ms"', first_800 + 1)
    first_250 = ssml.index('break time="250ms"')
    first_300 = ssml.index('break time="300ms"')
    second_300 = ssml.index('break time="300ms"', first_300 + 1)
    assert ssml.index(parts.intro_speech) < ssml.index(parts.clue_speech)
    assert ssml.index(parts.intro_speech) < first_300 < ssml.index(parts.clue_speech)
    assert ssml.index(parts.clue_speech) < first_250 < ssml.index(parts.letters_speech)
    assert ssml.index(parts.letters_speech) < first_800 < ssml.index(parts.think_speech)
    assert ssml.index(parts.think_speech) < ssml.index('break time="3000ms"')
    assert ssml.index('break time="3000ms"') < ssml.index(parts.answer_speech)
    assert "Here's a hint" not in ssml
    assert 'break time="2000ms"' not in ssml
    assert ssml.index(parts.answer_speech) < second_800 < ssml.index(parts.parse_speech)
    assert ssml.index(parts.parse_speech) < second_300 < ssml.index(parts.outro_speech)
    assert "That's Phi" not in ssml
    assert "Independent" in parts.intro_speech
    assert ssml.count('break time="250ms"') == 1


def test_parse_title_variants():
    from twodown.models import Clue
    from twodown.script import speak_intro

    assert parse_title("Independent 12458 / Phi") == ("Independent", "12458", "Phi")
    assert parse_title("Financial Times 18,477 by NEO") == ("Financial Times", "18477", "NEO")
    assert parse_title("Guardian Cryptic crossword No 30,108 by Paul") == ("Guardian", "30108", "Paul")
    assert parse_title("Independent on Sunday 1,907 by Filbert") == (
        "Independent on Sunday",
        "1907",
        "Filbert",
    )
    ios = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent on Sunday",
        puzzle_id="1907",
        setter="Filbert",
        blogger="tester",
        number="1",
        direction="across",
        clue="Example",
        enumeration="4",
        answer="TEST",
        parse="example",
        device="unknown",
        enumeration_ok=True,
    )
    assert speak_intro(ios) == (
        "Hi, here is your daily dose of AI cryptic clues. "
        "Today's clue is from the Independent on Sunday, by Filbert."
    )


def test_classify_anagram():
    assert classify_device("anagram of LED UNREST") == "anagram"
    assert classify_device("hidden answer in the clue") == "hidden"
