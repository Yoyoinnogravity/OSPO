from pathlib import Path

from twodown.config import PACKAGE_ROOT, PINUP_SLUG
from twodown.models import Clue
from twodown.pipeline import dreamlike_clue, published_clue


def test_dreamlike_hint_is_a_hand_picked_definition_still():
    clue = dreamlike_clue()
    assert clue.answer == "DREAMLIKE"
    assert clue.definition == "as in a trance"
    assert clue.hint_line == "Here's a clue."
    assert clue.hint_image == "assets/hints/moonlit-moments.webp"
    assert clue.hint_credit == (
        "Moonlit Moments · Linda Xu / Wikimedia Commons (CC0, via Unsplash)"
    )
    # Definition hint, not wordplay, and never print the answer on the still.
    assert "DREAMLIKE" not in clue.hint_line
    assert "DREAMLIKE" not in clue.hint_image
    assert "DREAMLIKE" not in clue.hint_credit
    assert "armed" not in clue.hint_credit.lower()
    assert "anagram" not in clue.hint_credit.lower()
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


def test_published_clues_do_not_carry_a_matcher_selected_hint():
    pinup = published_clue(PINUP_SLUG)
    assert pinup.hint_image is None
    assert pinup.hint_credit is None
    assert pinup.hint_line is None
    blank = Clue(
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
    )
    assert blank.hint_image is None
    assert blank.hint_credit is None
    assert blank.hint_line is None


def test_no_general_answer_to_picture_matcher():
    root = Path(__file__).resolve().parents[1] / "src" / "twodown"
    forbidden = (
        "match_answer_to_picture",
        "match_answer_to_image",
        "clip_embed",
        "vision_api",
    )
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not grow a {token} matcher"
