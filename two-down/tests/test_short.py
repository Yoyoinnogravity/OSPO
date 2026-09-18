from twodown.config import DEFAULT_VOICE_ALIAS, PINUP_SLUG, SOURCE_VOICE_ALIAS, STUDY_SLUG, VOICE_RATE, VOICES
from twodown.pipeline import (
    dreamlike_clue,
    fats_clue,
    published_clue,
    rasta_clue,
    resolve_clue,
    study_clue,
    wellington_clue,
    cole_clue,
)
from twodown.script import (
    speak_answer,
    speak_enumeration,
    speak_parse_asides,
    speak_parse_tokens,
    speak_source,
    write_parts,
)


def test_solver_voice_is_clear_libby():
    assert DEFAULT_VOICE_ALIAS == "libby"
    assert VOICES["libby"] == "en-GB-LibbyNeural"
    assert VOICE_RATE == "-8%"


def test_study_clue_is_cole():
    assert STUDY_SLUG == "guardian-30115-8d"
    clue = study_clue(STUDY_SLUG)
    assert clue is not None
    assert clue.slug == "guardian-30115-8d"
    assert clue.answer == "COLE"
    assert clue.clue == "So-called King of jazz, or another one accompanied by string trio"
    assert clue.enumeration == "4"
    assert clue.setter == "Brendan"
    assert clue.paper == "Guardian"
    assert clue.puzzle_id == "30115"
    assert clue.number == "8"
    assert clue.direction == "down"
    assert clue.blogger == "manehi"
    assert clue.definition == "King, as in Nat King Cole the jazz musician"
    assert clue.hint_line == "Here's a clue."
    assert clue.hint_image == "assets/hints/cole-still.webp"
    assert clue.source_url == (
        "https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/"
    )
    assert "fiddlers three" in clue.parse
    assert "Nat King Cole" in clue.parse
    parts = write_parts(clue)
    assert parts.intro_speech == "Here is your daily dose of cryptic fun."
    assert parts.clue_speech == "So-called King of jazz, or another one accompanied by string trio."
    assert parts.letters_speech == "Four letters."
    assert parts.think_speech == "Pause the video while you think."
    assert parts.hint_speech == "Here's a clue."
    assert parts.answer_speech == "The answer is cole."
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


def test_four_letters():
    clue = study_clue()
    assert clue is not None
    assert clue.enumeration == "4"
    assert speak_enumeration("4") == "Four letters."
    assert speak_enumeration(clue.enumeration) == "Four letters."


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


def test_spoken_parse_says_cole_as_a_word():
    clue = cole_clue()
    parts = write_parts(clue)
    assert "cole" in parts.answer_speech
    assert "nat king cole" in parts.parse_speech.lower()
    assert "fiddlers three" in parts.parse_speech.lower()
    assert "string trio" in parts.parse_speech.lower()
    assert "Jazz.;" not in parts.parse_speech
    assert "(" not in parts.parse_speech
    assert "COLE" not in parts.parse_speech
    assert "C-O-L-E" not in parts.parse_speech
    assert speak_parse_tokens("COLE") == "cole"
    assert "cole" not in parts.hint_speech.lower()
    assert "COLE" not in parts.hint_speech


def test_spoken_parse_says_wellington_pieces_as_words():
    clue = wellington_clue()
    parts = write_parts(clue)
    assert "well in" in parts.parse_speech.lower()
    assert "ton" in parts.parse_speech.lower()
    assert "(" not in parts.parse_speech
    assert ")" not in parts.parse_speech
    assert ". Thoroughly acquainted." in parts.parse_speech
    assert ". Good." in parts.parse_speech
    assert ". Style." in parts.parse_speech
    assert "wellington" in parts.answer_speech
    assert "WELLINGTON" not in parts.parse_speech
    assert "W-E-L-L" not in parts.parse_speech
    spaced = speak_parse_asides("well in (thoroughly acquainted) plus G (good).")
    assert "(" not in spaced
    assert spaced.lower().index("well in") < spaced.lower().index("thoroughly acquainted")
    assert speak_parse_tokens("WELL IN") == "well in"
    assert speak_parse_tokens("TON") == "ton"
    assert speak_parse_tokens("WELLINGTON") == "wellington"
    assert "wellington" not in parts.hint_speech.lower()
    assert "WELLINGTON" not in parts.hint_speech


def test_spoken_parse_says_fast_as_a_word():
    clue = fats_clue()
    parts = write_parts(clue)
    assert "fast" in parts.parse_speech.lower()
    assert "final twist" in parts.parse_speech.lower()
    assert "fats" in parts.answer_speech
    assert "FAST" not in parts.parse_speech
    assert "FATS" not in parts.parse_speech
    assert "F-A-S-T" not in parts.parse_speech
    assert speak_parse_tokens("FAST") == "fast"
    assert speak_parse_tokens("FATS") == "fats"
    assert "fats" not in parts.hint_speech.lower()
    assert "FATS" not in parts.hint_speech


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
    constructed = study_clue("cole")
    assert constructed is not None
    resolved = resolve_clue("cole", clue=constructed)
    assert resolved is constructed
    assert resolve_clue(STUDY_SLUG).answer == "COLE"
    assert resolve_clue("wellington").answer == "WELLINGTON"
    assert resolve_clue("fats").answer == "FATS"
    assert resolve_clue("rasta").answer == "RASTA"
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
