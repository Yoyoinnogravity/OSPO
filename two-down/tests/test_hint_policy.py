from pathlib import Path

from twodown.config import PACKAGE_ROOT, PINUP_SLUG, STUDY_SLUG
from twodown.hints import CLOSE_ENOUGH, COLE, DAVIS, FATS, RASTA, SMILES, TRANCE, WELLINGTON, attach_hint, match_hint
from twodown.models import Clue
from twodown.pipeline import cole_clue, davis_cup_clue, dreamlike_clue, fats_clue, published_clue, rasta_clue, smiles_clue, study_clue, wellington_clue


def test_study_slug_and_hint_fields_are_davis_cup():
    assert STUDY_SLUG == "guardian-30115-18d"
    clue = study_clue()
    assert clue is not None
    assert clue.answer == "DAVIS CUP"
    assert clue.slug == STUDY_SLUG
    assert clue.definition == "international court event"
    assert clue.hint_line == "Have a look at this."
    assert clue.hint_image
    assert clue.hint_credit
    # Hint the tennis-court definition, not divas / cricket / UP.
    assert "divas" not in clue.hint_credit.lower()
    assert "cricket" not in clue.hint_credit.lower()
    # Never print the answer on the hint card copy.
    assert "DAVIS" not in clue.hint_line
    assert "DAVIS" not in clue.hint_credit
    assert "CUP" not in clue.hint_line
    assert "CUP" not in clue.hint_credit


def test_davis_cup_hint_matches_definition_at_80_percent():
    clue = davis_cup_clue()
    assert clue.answer == "DAVIS CUP"
    matched = match_hint(clue.definition or "")
    assert matched.photo.slug == DAVIS.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert clue.hint_image == f"assets/hints/{DAVIS.filename}"
    assert clue.hint_credit == DAVIS.credit_line
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


def test_aled_definition_is_close_enough_for_a_reasonable_matcher():
    matched = match_hint("Nat King Cole the jazz musician")
    assert matched.photo.slug == COLE.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    leftover = match_hint("Duke")
    assert leftover.photo.slug == WELLINGTON.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint("such unhealthy foods")
    assert leftover.photo.slug == FATS.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint("visibly pleased")
    assert leftover.photo.slug == SMILES.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint("international court event")
    assert leftover.photo.slug == DAVIS.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    rasta = match_hint("a RASTA may be a follower of the Emperor Haile Selassie")
    assert rasta.photo.slug == RASTA.slug
    assert rasta.closeness >= CLOSE_ENOUGH


def test_dreamlike_leftover_still_matches_at_80_percent():
    clue = dreamlike_clue()
    assert clue.answer == "DREAMLIKE"
    assert clue.definition == "as in a trance"
    matched = match_hint(clue.definition)
    assert matched.photo.slug == TRANCE.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert "DREAMLIKE" not in clue.hint_line
    assert "DREAMLIKE" not in clue.hint_credit
    assert "armed" not in clue.hint_credit.lower()
    assert "anagram" not in clue.hint_credit.lower()


def test_ai_matching_is_allowed():
    src = (PACKAGE_ROOT / "src" / "twodown" / "hints.py").read_text(encoding="utf-8")
    assert "Do not ban AI matching" in src
    assert "human-only gate is superseded" in src
    assert "match_hint" in src
    agents = (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "never add AI picture match" not in agents.lower()
    assert "Do not ban AI matching" in agents
    attached = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/example/",
            paper="Guardian",
            puzzle_id="30115",
            setter="Brendan",
            blogger="manehi",
            number="20",
            direction="across",
            clue="One emperor backing follower of another",
            enumeration="5",
            answer="RASTA",
            definition="a RASTA may be a follower of the Emperor Haile Selassie",
            parse='A="One" + TSAR="emperor"',
        )
    )
    assert attached.hint_image.endswith("rasta-still.webp")
    assert attached.hint_line == "Have a look at this."


def test_published_clues_have_optional_hint_fields():
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
    attached = attach_hint(blank)
    assert attached.hint_line == "Have a look at this."
    assert attached.hint_image
    assert attached.hint_credit


def test_no_cloud_vision_pipeline():
    root = Path(__file__).resolve().parents[1] / "src" / "twodown"
    forbidden = (
        "clip_embed",
        "vision_api",
    )
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not grow a {token} pipeline"
    # A local 80% definition matcher is allowed. Do not ban match_hint.
    assert "def match_hint" in (root / "hints.py").read_text(encoding="utf-8")
