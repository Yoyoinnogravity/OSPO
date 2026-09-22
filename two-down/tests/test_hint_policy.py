from pathlib import Path

from twodown.config import HINT_LINE, NO_PICTURE_LINE, PACKAGE_ROOT, PINUP_SLUG, STUDY_SLUG
from twodown.hints import AIM, AUTHOR, CLOSE_ENOUGH, COLE, CRASH, DAVIS, DICTIONARY, FATS, MAKEUP, PAPERS, PHOTO, RASTA, SHELTER, SMILES, TRANCE, WELLINGTON, attach_hint, has_picture_clue, hint_for_clue, match_hint
from twodown.models import Clue
from twodown.script import write_parts
from twodown.pipeline import aimlessly_clue, cole_clue, davis_cup_clue, dreamlike_clue, fats_clue, mass_media_clue, published_clue, rasta_clue, smiles_clue, study_clue, wellington_clue


def test_study_slug_and_hint_fields_are_mass_media():
    assert STUDY_SLUG == "financial-times-18483-1a"
    clue = study_clue()
    assert clue is not None
    assert clue.answer == "MASS MEDIA"
    assert clue.slug == STUDY_SLUG
    assert clue.definition == "newspapers, the press"
    assert clue.hint_line == HINT_LINE
    assert clue.hint_image
    assert clue.hint_credit
    # Hint newspapers / the press, not maid / mess.
    assert "maid" not in clue.hint_credit.lower()
    assert "mess" not in clue.hint_credit.lower()
    # Never print the answer on the hint card copy.
    assert "MASS" not in clue.hint_line
    assert "MEDIA" not in clue.hint_line
    assert "MASS MEDIA" not in clue.hint_credit


def test_mass_media_hint_matches_definition_at_80_percent():
    clue = mass_media_clue()
    assert clue.answer == "MASS MEDIA"
    matched = match_hint(clue.definition or "")
    assert matched.photo.slug == PAPERS.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert clue.hint_image == f"assets/hints/{PAPERS.filename}"
    assert clue.hint_credit == PAPERS.credit_line
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


def test_aimlessly_hint_matches_definition_at_80_percent():
    clue = aimlessly_clue()
    assert clue.answer == "AIMLESSLY"
    matched = match_hint(clue.definition or "")
    assert matched.photo.slug == AIM.slug
    assert matched.closeness >= CLOSE_ENOUGH
    assert matched.close_enough
    assert clue.hint_image == f"assets/hints/{AIM.filename}"
    assert clue.hint_credit == AIM.credit_line
    still = PACKAGE_ROOT / clue.hint_image
    assert still.is_file()
    assert still.stat().st_size > 0


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
    leftover = match_hint("end, as in a goal or aim")
    assert leftover.photo.slug == AIM.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint("newspapers, the press")
    assert leftover.photo.slug == PAPERS.slug
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
    assert attached.hint_line == HINT_LINE


def test_published_clues_get_a_picture_clue():
    pinup = published_clue(PINUP_SLUG)
    assert pinup.hint_line == HINT_LINE
    assert pinup.hint_image.endswith("photo-still.webp")
    assert pinup.hint_credit == PHOTO.credit_line
    assert "PIN-UP" not in pinup.hint_credit
    mascara = published_clue("guardian-30112-1a")
    assert mascara.hint_image.endswith("makeup-still.webp")
    smash = published_clue("guardian-30112-5a")
    assert smash.hint_image.endswith("crash-still.webp")
    self_clue = published_clue("guardian-30113-9a")
    assert self_clue.hint_image.endswith("author-still.webp")
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
    attached = attach_hint(blank)
    assert attached.hint_line == HINT_LINE
    assert attached.hint_image.endswith("photo-still.webp")


def test_daily_definitions_match_picture_clues_at_80_percent():
    assert match_hint("make-up").photo.slug == MAKEUP.slug
    assert match_hint("a car crash").photo.slug == CRASH.slug
    assert match_hint("an attractive person appearing in photos").photo.slug == PHOTO.slug
    assert match_hint("this author").photo.slug == AUTHOR.slug
    assert match_hint("make-up").closeness >= CLOSE_ENOUGH
    assert match_hint("a car crash").closeness >= CLOSE_ENOUGH
    assert match_hint("this author").closeness >= CLOSE_ENOUGH


def test_ft_take_cover_and_oedipus_surface_clues_get_picture_hints():
    take_cover = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/2026/09/22/financial-times-18486-by-gozo/",
            paper="Financial Times",
            puzzle_id="18486",
            setter="GOZO",
            blogger="Cineraria",
            number="1",
            direction="across",
            clue="Arrange insurance and head for shelter",
            enumeration="4,5",
            answer="TAKE COVER",
            parse="TAKE + COVER",
            device="charade",
        )
    )
    assert take_cover.hint_line == HINT_LINE
    assert take_cover.hint_image == f"assets/hints/{SHELTER.filename}"
    assert has_picture_clue(take_cover)

    oedipus = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/2026/09/22/financial-times-18486-by-gozo/",
            paper="Financial Times",
            puzzle_id="18486",
            setter="GOZO",
            blogger="Cineraria",
            number="9",
            direction="across",
            clue="Dictionary (American) includes one page on tragic figure",
            enumeration="7",
            answer="OEDIPUS",
            parse="{ oed. Dictionary. Plus us. American.} around. Includes. { I. One. Plus P. Page.}. Tragic figure.",
            device="container",
        )
    )
    assert oedipus.hint_line == HINT_LINE
    assert oedipus.hint_image == f"assets/hints/{DICTIONARY.filename}"
    assert has_picture_clue(oedipus)
    matched = match_hint(oedipus.clue)
    assert matched.photo.slug == DICTIONARY.slug
    assert matched.closeness >= CLOSE_ENOUGH


def test_weak_match_says_no_picture_clue_today():
    attached = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/example/",
            paper="Guardian",
            puzzle_id="30117",
            setter="Paul",
            blogger="Andrew",
            number="6",
            direction="down",
            clue="Craft that may be inflated",
            enumeration="4",
            answer="RAFT",
            definition="inflatable craft",
            parse="hidden",
        )
    )
    assert attached.hint_line == NO_PICTURE_LINE
    assert attached.hint_line == "No picture clue today."
    assert attached.hint_image is None
    assert attached.hint_credit is None
    assert hint_for_clue(attached) is None
    assert not has_picture_clue(attached)
    leftover = match_hint("inflatable craft")
    assert leftover.close_enough is False
    assert leftover.line == NO_PICTURE_LINE
    parts = write_parts(attached)
    assert parts.hint_speech == NO_PICTURE_LINE
    assert parts.has_picture is False
    assert "[pause 4s]" not in parts.full
    assert "[pause 2.5s]" in parts.full


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
