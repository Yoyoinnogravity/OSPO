from pathlib import Path

from twodown.config import PACKAGE_ROOT, PINUP_SLUG
from twodown.hints import CLOSE_ENOUGH, RASTA, TRANCE, attach_hint, match_hint
from twodown.models import Clue
from twodown.pipeline import dreamlike_clue, published_clue, rasta_clue


def test_dreamlike_hint_matches_definition_at_80_percent():
    clue = dreamlike_clue()
    assert clue.answer == "DREAMLIKE"
    assert clue.definition == "as in a trance"
    assert clue.hint_line == "Here's a clue."
    matched = match_hint(clue.definition)
    assert matched.photo.slug == TRANCE.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert clue.hint_image == f"assets/hints/{TRANCE.filename}"
    assert clue.hint_credit == TRANCE.credit_line
    # Definition hint, not wordplay, and never print the answer on the still.
    assert "DREAMLIKE" not in clue.hint_line
    assert "DREAMLIKE" not in clue.hint_image
    assert "DREAMLIKE" not in clue.hint_credit
    assert "armed" not in clue.hint_credit.lower()
    assert "anagram" not in clue.hint_credit.lower()
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


def test_rasta_hint_matches_definition_at_80_percent():
    clue = rasta_clue()
    assert clue.answer == "RASTA"
    assert "Haile Selassie" in (clue.definition or "")
    assert clue.hint_line == "Here's a clue."
    matched = match_hint(clue.definition)
    assert matched.photo.slug == RASTA.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert clue.hint_image == f"assets/hints/{RASTA.filename}"
    assert clue.hint_credit == RASTA.credit_line
    assert "RASTA" not in clue.hint_line
    assert "RASTA" not in clue.hint_image
    assert "RASTA" not in clue.hint_credit
    assert "tsar" not in clue.hint_credit.lower()
    assert "reversal" not in clue.hint_credit.lower()
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


def test_ai_matching_is_allowed():
    src = (PACKAGE_ROOT / "src" / "twodown" / "hints.py").read_text(encoding="utf-8")
    assert "Do not ban AI matching" in src
    assert "human-only gate is superseded" in src
    assert "match_hint" in src
    attached = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/example/",
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="12",
            direction="across",
            clue="Doctor armed with positive response, as in a trance",
            enumeration="9",
            answer="DREAMLIKE",
            definition="as in a trance",
            parse="armed plus like",
        )
    )
    assert attached.hint_image.endswith("trance-still.webp")
    assert attached.hint_line == "Here's a clue."


def test_published_clues_do_not_need_a_hint_until_attached():
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


def test_no_cloud_vision_pipeline():
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
            assert token not in text, f"{path.name} must not grow a {token} pipeline"
