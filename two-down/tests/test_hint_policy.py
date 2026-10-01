from pathlib import Path

from twodown.config import HINT_LINE, HINT_MISS, PACKAGE_ROOT, PINUP_SLUG, STUDY_SLUG
from twodown.hints import AIM, CLOSE_ENOUGH, COLE, DAVIS, DEFAULT_HINT, FATS, PAPERS, RASTA, SMILES, TRANCE, WELLINGTON, attach_hint, match_hint
from twodown.models import Clue
from twodown.pipeline import aimlessly_clue, chicago_clue, cole_clue, davis_cup_clue, dreamlike_clue, elicit_clue, fats_clue, mass_media_clue, published_clue, rasta_clue, smiles_clue, sphere_clue, study_clue, wellington_clue


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
    assert attached.hint_line == HINT_MISS
    assert not attached.hint_image
    assert not attached.hint_credit


def test_unmatched_published_clue_says_no_relevant_image():
    elicit = attach_hint(published_clue("guardian-30124-9a"))
    chicago = attach_hint(published_clue("independent-12473-1a"))
    assert elicit.answer == "ELICIT"
    assert chicago.answer == "CHICAGO"
    assert HINT_MISS == "No relevant image found."
    assert elicit.hint_line == HINT_MISS
    assert chicago.hint_line == HINT_MISS
    assert not elicit.hint_image
    assert not chicago.hint_image
    assert not elicit.hint_credit
    assert not chicago.hint_credit
    leftover = match_hint(elicit.definition or elicit.clue)
    assert leftover.close_enough is False
    leftover = match_hint(chicago.definition or chicago.clue)
    assert leftover.close_enough is False


def test_default_still_does_not_attach_without_a_real_match():
    """The leftover trance / papers still must not ride along on a miss."""
    banned = {
        f"assets/hints/{DEFAULT_HINT.filename}",
        f"assets/hints/{TRANCE.filename}",
        f"assets/hints/{PAPERS.filename}",
    }
    for clue in (
        elicit_clue(),
        chicago_clue(),
        sphere_clue(),
        attach_hint(published_clue("guardian-30124-9a")),
        attach_hint(published_clue("independent-12473-1a")),
        attach_hint(published_clue("financial-times-18478-5a")),
        attach_hint(published_clue(PINUP_SLUG)),
    ):
        assert clue.hint_line == HINT_MISS
        assert clue.hint_image is None
        assert clue.hint_image not in banned
        assert clue.hint_credit is None
    for text in (
        "Bring out",
        "place in the USA",
        "obtain",
        "final analysis",
        "Female",
        "Female bearing pressure on field",
        "field",
        "",
    ):
        matched = match_hint(text)
        assert matched.close_enough is False


def test_sphere_female_bearing_does_not_get_trance_or_sleep_still():
    from twodown.hints import hint_for_clue
    from twodown.pipeline import resolve_clue
    from twodown.script import write_parts

    surface = "Female bearing pressure on field"
    leftover = match_hint(surface)
    assert leftover.closeness < CLOSE_ENOUGH
    assert not leftover.close_enough
    # Even the leftover .photo must not be treated as a sleep / trance match.
    assert leftover.photo.slug != TRANCE.slug or not leftover.close_enough
    female = match_hint("Female")
    assert not female.close_enough
    assert female.photo.slug != TRANCE.slug or not female.close_enough

    published = published_clue("financial-times-18478-5a")
    assert published.answer == "SPHERE"
    assert published.clue == surface
    attached = attach_hint(published)
    assert attached.hint_line == HINT_MISS
    assert not attached.hint_image
    assert not attached.hint_credit
    assert hint_for_clue(attached) is None
    assert "trance" not in (attached.hint_credit or "").lower()
    assert "sleep" not in (attached.hint_credit or "").lower()

    resolved = resolve_clue("financial-times-18478-5a")
    assert resolved.answer == "SPHERE"
    assert resolved.hint_line == HINT_MISS
    assert not resolved.hint_image
    assert hint_for_clue(resolved) is None
    parts = write_parts(resolved)
    assert parts.hint_speech == HINT_MISS
    assert "Here's a hint" not in parts.hint_speech

    # A stored definition of field / globe still must not pick the sleeping woman.
    fielded = attach_hint(
        Clue(
            source_url="https://fifteensquared.net/example/",
            paper="Financial Times",
            puzzle_id="18478",
            setter="Leonidas",
            blogger="Pete Maclean",
            number="5",
            direction="across",
            clue=surface,
            enumeration="6",
            answer="SPHERE",
            definition="field",
            parse="P (pressure) in (bearing) SHE (female) + RE (on)",
        )
    )
    assert fielded.hint_line == HINT_MISS
    assert not fielded.hint_image
    assert hint_for_clue(fielded) is None


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
