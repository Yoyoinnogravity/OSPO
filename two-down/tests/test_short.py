from twodown.config import PINUP_SLUG, SOURCE_VOICE_ALIAS, STUDY_SLUG
from twodown.pipeline import dreamlike_clue, published_clue, rasta_clue, resolve_clue, study_clue
from twodown.script import speak_answer, speak_enumeration, speak_parse_tokens, speak_source, write_parts


def test_study_clue_is_rasta():
    assert STUDY_SLUG == "guardian-30115-20a"
    clue = study_clue(STUDY_SLUG)
    assert clue is not None
    assert clue.slug == "guardian-30115-20a"
    assert clue.answer == "RASTA"
    assert clue.clue == "One emperor backing follower of another"
    assert clue.enumeration == "5"
    assert clue.device == "reversal"
    assert clue.setter == "Brendan"
    assert clue.paper == "Guardian"
    assert clue.puzzle_id == "30115"
    assert clue.number == "20"
    assert clue.direction == "across"
    assert clue.blogger == "manehi"
    assert clue.definition == "a RASTA may be a follower of the Emperor Haile Selassie"
    assert clue.hint_line == "Here's a clue."
    assert clue.hint_image == "assets/hints/rasta-still.webp"
    assert clue.source_url == (
        "https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/"
    )
    assert "TSAR" in clue.parse
    assert "backing" in clue.parse
    parts = write_parts(clue)
    assert parts.intro_speech == "Here is your daily dose of cryptic fun."
    assert parts.clue_speech == "One emperor backing follower of another."
    assert parts.letters_speech == "Five letters."
    assert parts.think_speech == "Pause the video while you think."
    assert parts.hint_speech == "Here's a clue."
    assert parts.answer_speech == "The answer is rasta."
    assert parts.answer_speech == speak_answer(clue.answer)
    assert parts.outro_speech == "Thanks for thinking with cryptic.fun."
    assert "Brendan" not in parts.parse_speech
    assert "Fifteen Squared" not in parts.parse_speech
    assert parts.source_speech == "Brendan in the Guardian, via Fifteen Squared."
    script = parts.full
    assert script.index(parts.intro_speech) < script.index(parts.clue_speech)
    assert script.index(parts.clue_speech) < script.index(parts.letters_speech)
    assert script.index(parts.letters_speech) < script.index(parts.think_speech)
    assert script.index(parts.think_speech) < script.index("[pause 7s]")
    assert script.index("[pause 7s]") < script.index(parts.hint_speech)
    assert script.index(parts.hint_speech) < script.index("[pause 4s]")
    assert script.index("[pause 4s]") < script.index("[pause 2.5s]")
    assert script.index("[pause 2.5s]") < script.index(parts.answer_speech)
    assert script.index(parts.answer_speech) < script.index(parts.parse_speech)
    assert script.index(parts.parse_speech) < script.index(parts.source_speech)
    assert script.index(parts.source_speech) < script.index(parts.outro_speech)


def test_speak_answer_rasta_is_a_word():
    assert speak_answer("RASTA") == "The answer is rasta."
    assert speak_answer("RASTA") != "The answer is R-A-S-T-A."
    assert "rasta" in speak_answer("RASTA")
    assert "R-A-S-T-A" not in speak_answer("RASTA")


def test_source_credit_is_its_own_line():
    clue = rasta_clue()
    assert speak_source(clue) == "Brendan in the Guardian, via Fifteen Squared."
    assert SOURCE_VOICE_ALIAS == "thomas"
    parts = write_parts(clue)
    assert parts.source_speech == speak_source(clue)
    assert "Fifteen Squared" not in parts.parse_speech
    assert parts.outro_speech == "Thanks for thinking with cryptic.fun."


def test_five_letters():
    clue = study_clue()
    assert clue is not None
    assert clue.enumeration == "5"
    assert speak_enumeration("5") == "Five letters."
    assert speak_enumeration(clue.enumeration) == "Five letters."


def test_spoken_parse_says_tsar_as_a_word():
    clue = rasta_clue()
    parts = write_parts(clue)
    assert "tsar" in parts.parse_speech
    assert "backing" in parts.parse_speech
    assert "rasta" in parts.answer_speech
    assert "TSAR" not in parts.parse_speech
    assert "RASTA" not in parts.parse_speech
    assert "R-A-S-T-A" not in parts.parse_speech
    assert "T-S-A-R" not in parts.parse_speech
    assert speak_parse_tokens("TSAR") == "tsar"
    assert speak_parse_tokens("RASTA") == "rasta"
    assert "rasta" not in parts.hint_speech.lower()
    assert "RASTA" not in parts.hint_speech


def test_dreamlike_stays_constructable():
    clue = dreamlike_clue()
    assert clue.answer == "DREAMLIKE"
    assert clue.slug == "guardian-30115-12a"
    assert speak_answer("DREAMLIKE") == "The answer is dreamlike."
    assert speak_enumeration("9") == "Nine letters."
    parts = write_parts(clue)
    assert "armed" in parts.parse_speech
    assert "like" in parts.parse_speech
    assert "DREAMLIKE" not in parts.parse_speech
    assert study_clue("dreamlike") is not None
    assert study_clue("dreamlike").answer == "DREAMLIKE"


def test_resolve_clue_renders_constructed_study_without_site_html():
    constructed = study_clue("rasta")
    assert constructed is not None
    resolved = resolve_clue("rasta", clue=constructed)
    assert resolved is constructed
    assert resolve_clue(STUDY_SLUG).answer == "RASTA"
    assert resolve_clue("dreamlike").answer == "DREAMLIKE"


def test_pin_up_stays_on_the_published_site():
    clue = published_clue(PINUP_SLUG)
    assert clue.slug == "independent-12462-6a"
    assert clue.answer == "PIN-UP"
    assert speak_parse_tokens("PUP") == "pup"
    assert speak_parse_tokens("PUP containing IN") == "pup containing in"
    assert speak_parse_tokens("PIN-UP") == "pin-up"
    assert speak_parse_tokens("END RESULT") == "end result"
    assert speak_parse_tokens("Three hyphen two.") == "Three hyphen two."
    assert speak_parse_tokens("Slang for an attractive person.") == "Slang for an attractive person."
    assert speak_parse_tokens("12 across, 3-2") == "12 across, 3-2"
