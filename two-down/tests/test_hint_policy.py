from pathlib import Path

from twodown.config import HINT_LINE, HINT_MISS, PACKAGE_ROOT, PINUP_SLUG, STUDY_SLUG
from twodown.hints import AIM, AUTHOR, BRING, CLOSE_ENOUGH, COLE, CROSS, DAVIS, DEFAULT_HINT, FATS, FIELD, MODEL, PAPERS, RASTA, SMILES, TRANCE, USA, WELLINGTON, attach_hint, match_hint
from twodown.models import Clue
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


def test_published_clues_attach_a_definition_hint():
    pinup = published_clue(PINUP_SLUG)
    assert pinup.hint_image == f"assets/hints/{MODEL.filename}"
    assert pinup.hint_credit == MODEL.credit_line
    assert pinup.hint_line == HINT_LINE
    assert "PIN-UP" not in (pinup.hint_credit or "")
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
    assert attached.hint_image == f"assets/hints/{MODEL.filename}"


def test_published_pair_gets_distinct_definition_stills():
    elicit = published_clue("guardian-30124-9a")
    chicago = published_clue("independent-12473-1a")
    assert elicit.answer == "ELICIT"
    assert chicago.answer == "CHICAGO"
    assert elicit.hint_image == f"assets/hints/{BRING.filename}"
    assert chicago.hint_image == f"assets/hints/{USA.filename}"
    assert elicit.hint_image != chicago.hint_image
    assert "ELICIT" not in (elicit.hint_credit or "")
    assert "CHICAGO" not in (chicago.hint_credit or "")
    bring = match_hint("Bring out")
    usa = match_hint("place in the USA")
    assert bring.photo.slug == BRING.slug
    assert bring.closeness >= CLOSE_ENOUGH
    assert usa.photo.slug == USA.slug
    assert usa.closeness >= CLOSE_ENOUGH
    assert (PACKAGE_ROOT / elicit.hint_image).is_file()
    assert (PACKAGE_ROOT / chicago.hint_image).is_file()


def test_aled_bring_out_and_usa_match_at_80_percent():
    leftover = match_hint("Bring out")
    assert leftover.photo.slug == BRING.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint("place in the USA")
    assert leftover.photo.slug == USA.slug
    assert leftover.closeness >= CLOSE_ENOUGH
    leftover = match_hint(
        "Bring out",
        clue="Bring out client I fancy with no end of distinction",
    )
    assert leftover.photo.slug == BRING.slug
    leftover = match_hint(
        "place in the USA",
        clue="Trendy adult board game place in the USA",
        parse="CHIC (elegant and fashionable; trendy) + A (adult) + GO (a board game)",
    )
    assert leftover.photo.slug == USA.slug



def test_unmatched_clue_says_no_relevant_image_found():
    from twodown.hints import hint_for_clue, spoken_hint
    from twodown.script import write_parts

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
    attached = attach_hint(blank)
    assert attached.hint_image is None
    assert attached.hint_line == HINT_MISS
    assert hint_for_clue(attached) is None
    assert spoken_hint(attached) == HINT_MISS
    leftover = match_hint(blank.definition or "", clue=blank.clue, parse=blank.parse)
    assert not leftover.close_enough
    assert leftover.photo is None
    assert leftover.line == HINT_MISS
    parts = write_parts(blank)
    assert parts.hint_speech == HINT_MISS
    assert "Here's a hint" not in parts.full
    assert HINT_MISS in parts.full
    assert parts.full.index(parts.think_speech) < parts.full.index(parts.hint_speech)
    assert parts.full.index(parts.hint_speech) < parts.full.index(parts.answer_speech)


def test_default_hint_is_not_the_sleeping_woman():
    assert DEFAULT_HINT is None
    assert DEFAULT_HINT is not TRANCE
    leftover = match_hint("female")
    assert leftover.photo is not TRANCE
    assert leftover.photo is None
    assert not leftover.close_enough
    leftover = match_hint("Female bearing pressure")
    assert leftover.photo is not TRANCE
    assert leftover.photo is None
    leftover = match_hint("", clue="Female bearing pressure on field")
    assert leftover.photo is not TRANCE
    assert leftover.photo is None
    assert not leftover.close_enough
    assert leftover.line == HINT_MISS


def test_sphere_misses_when_catalog_has_no_globe():
    from twodown.hints import hint_for_clue, spoken_hint
    from twodown.pipeline import published_clue

    clue = published_clue("financial-times-18478-5a")
    assert clue.answer == "SPHERE"
    assert clue.clue == "Female bearing pressure on field"
    attached = attach_hint(clue)
    assert attached.hint_image is None
    assert attached.hint_credit is None
    assert attached.hint_line == HINT_MISS
    assert hint_for_clue(attached) is None
    assert spoken_hint(attached) == HINT_MISS
    assert "SPHERE" not in attached.hint_line
    globe = match_hint("globe / orb / ball / domain")
    assert globe.photo is not TRANCE
    assert globe.photo is not FIELD
    assert not globe.close_enough
    assert globe.photo is None
    leftover = Clue(
        source_url=clue.source_url,
        paper=clue.paper,
        puzzle_id=clue.puzzle_id,
        setter=clue.setter,
        blogger=clue.blogger,
        number=clue.number,
        direction=clue.direction,
        clue=clue.clue,
        enumeration=clue.enumeration,
        answer=clue.answer,
        parse=clue.parse,
        hint_image=f"assets/hints/{TRANCE.filename}",
        hint_credit=TRANCE.credit_line,
        hint_line=HINT_LINE,
    )
    repaired = attach_hint(leftover)
    assert repaired.hint_image is None
    assert repaired.hint_line == HINT_MISS
    assert hint_for_clue(repaired) is None


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
