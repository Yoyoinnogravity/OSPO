from twodown.config import DEFAULT_VOICE_ALIAS, HINT_LINE, HINT_LOOK, HINT_OFFER, HINT_VOICE_ALIAS, INTRO_VOICE_ALIAS, PINUP_SLUG, SOURCE_VOICE_ALIAS, STUDY_SLUG, VOICE_RATE, VOICES
from twodown.pipeline import (
    dreamlike_clue,
    fats_clue,
    published_clue,
    rasta_clue,
    resolve_clue,
    study_clue,
    wellington_clue,
    cole_clue,
    smiles_clue,
    davis_cup_clue,
    aimlessly_clue,
    mass_media_clue,
)
from twodown.script import (
    speak_answer,
    speak_enumeration,
    speak_parse_asides,
    speak_parse_tokens,
    speak_source,
    write_parts,
)
from twodown.voice import _speech_sentences


def test_solver_voice_is_warm_sonia():
    assert DEFAULT_VOICE_ALIAS == "sonia"
    assert VOICES["sonia"] == "en-GB-SoniaNeural"
    assert VOICE_RATE == "-10%"


def test_parse_is_split_into_spoken_sentences():
    lines = _speech_sentences("S, first letter of school, plus miles. A long way. Visibly pleased.")
    assert lines == [
        "S, first letter of school, plus miles.",
        "A long way.",
        "Visibly pleased.",
    ]


def test_study_clue_is_mass_media():
    assert STUDY_SLUG == "financial-times-18483-1a"
    clue = study_clue(STUDY_SLUG)
    assert clue is not None
    assert clue.slug == "financial-times-18483-1a"
    assert clue.answer == "MASS MEDIA"
    assert clue.clue == "Maid struggling with a mess — newspapers etc"
    assert clue.enumeration == "4,5"
    assert clue.setter == "Arrietty"
    assert clue.paper == "Financial Times"
    assert clue.puzzle_id == "18483"
    assert clue.number == "1"
    assert clue.direction == "across"
    assert clue.blogger == "Turbolegs"
    assert clue.definition == "newspapers, the press"
    assert clue.hint_line == HINT_LINE
    assert HINT_OFFER == "If you need a clue."
    assert HINT_LOOK == "Have a look at this."
    assert clue.hint_line == "If you need a clue. Have a look at this."
    assert clue.hint_image == "assets/hints/papers-still.webp"
    assert clue.source_url == (
        "https://fifteensquared.net/2026/09/18/financial-times-18483-by-arrietty/"
    )
    assert "struggling" in clue.parse.lower()
    assert "mess" in clue.parse.lower()
    parts = write_parts(clue)
    assert parts.intro_speech == "Right — let's be Cryptic AI for Fun."
    assert parts.clue_speech == "Maid struggling with a mess — newspapers etc."
    assert parts.letters_speech == "That's four, five."
    assert parts.think_speech == "Just pause here, and have a think."
    assert parts.hint_speech == HINT_LINE
    assert parts.hint_speech.startswith(HINT_OFFER)
    assert parts.hint_speech.endswith(HINT_LOOK)
    assert parts.hint_speech == "If you need a clue. Have a look at this."
    assert HINT_VOICE_ALIAS == "ryan"
    assert HINT_VOICE_ALIAS == INTRO_VOICE_ALIAS
    assert parts.answer_speech == "It's mass media."
    assert parts.answer_speech == speak_answer(clue.answer)
    assert parts.outro_speech == "We are here to help then dominate."
    assert "Brendan" not in parts.parse_speech
    assert "Fifteen Squared" not in parts.parse_speech
    assert parts.source_speech == "That's Arrietty, in the Financial Times — via Fifteen Squared."
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
    assert speak_answer("RASTA") == "It's rasta."
    assert speak_answer("RASTA") != "The answer is R-A-S-T-A."
    assert "rasta" in speak_answer("RASTA")
    assert "R-A-S-T-A" not in speak_answer("RASTA")


def test_source_credit_is_its_own_line():
    clue = rasta_clue()
    assert speak_source(clue) == "That's Brendan, in the Guardian — via Fifteen Squared."
    assert SOURCE_VOICE_ALIAS == "thomas"
    parts = write_parts(clue)
    assert parts.source_speech == speak_source(clue)
    assert "Fifteen Squared" not in parts.parse_speech
    assert parts.outro_speech == "We are here to help then dominate."


def test_spoken_parse_says_mass_media_as_words():
    clue = mass_media_clue()
    parts = write_parts(clue)
    assert "mass media" in parts.answer_speech
    assert "struggling" in parts.parse_speech.lower()
    assert "maid" in parts.parse_speech.lower()
    assert "mess" in parts.parse_speech.lower()
    assert "newspapers" in parts.parse_speech.lower() or "press" in parts.parse_speech.lower()
    assert "MASS MEDIA" not in parts.parse_speech
    assert "M-A-S-S" not in parts.parse_speech
    assert speak_parse_tokens("MASS MEDIA") == "mass media"
    assert "mass media" not in parts.hint_speech.lower()
    assert "MASS" not in parts.hint_speech


def test_five_three_letters():
    clue = davis_cup_clue()
    assert clue.enumeration == "5,3"
    assert speak_enumeration("5,3") == "That's five, three."
    assert speak_enumeration(clue.enumeration) == "That's five, three."


def test_spoken_parse_says_aimlessly_as_a_word():
    clue = aimlessly_clue()
    parts = write_parts(clue)
    assert "aimlessly" in parts.answer_speech
    assert "recycled" in parts.parse_speech.lower()
    assert "sly" in parts.parse_speech.lower()
    assert "e-mails" in parts.parse_speech.lower() or "emails" in parts.parse_speech.lower()
    assert "goal" in parts.parse_speech.lower() or "aim" in parts.parse_speech.lower()
    assert "AIMLESSLY" not in parts.parse_speech
    assert "A-I-M-L-E-S-S-L-Y" not in parts.parse_speech
    assert speak_parse_tokens("AIMLESSLY") == "aimlessly"
    assert "aimlessly" not in parts.hint_speech.lower()
    assert "AIMLESSLY" not in parts.hint_speech


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


def test_spoken_parse_says_smiles_and_miles_as_words():
    clue = smiles_clue()
    parts = write_parts(clue)
    assert "smiles" in parts.answer_speech
    assert "miles" in parts.parse_speech.lower()
    assert "first letter of school" in parts.parse_speech.lower()
    assert "a long way" in parts.parse_speech.lower()
    assert "visibly pleased" in parts.parse_speech.lower()
    assert "SMILES" not in parts.parse_speech
    assert "MILES" not in parts.parse_speech
    assert "S-M-I-L-E-S" not in parts.parse_speech
    assert speak_parse_tokens("MILES") == "miles"
    assert speak_parse_tokens("SMILES") == "smiles"
    assert "smiles" not in parts.hint_speech.lower()
    assert "SMILES" not in parts.hint_speech


def test_spoken_parse_says_davis_cup_as_words():
    clue = davis_cup_clue()
    parts = write_parts(clue)
    assert "davis cup" in parts.answer_speech
    assert "divas" in parts.parse_speech.lower()
    assert "frenzied" in parts.parse_speech.lower()
    assert "caught" in parts.parse_speech.lower()
    assert "international court event" in parts.parse_speech.lower()
    assert "DAVIS CUP" not in parts.parse_speech
    assert "D-A-V-I-S" not in parts.parse_speech
    assert speak_parse_tokens("DAVIS CUP") == "davis cup"
    assert speak_parse_tokens("DIVAS") == "divas"
    assert "davis" not in parts.hint_speech.lower()
    assert "DAVIS" not in parts.hint_speech
    assert "(" not in parts.parse_speech


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
    assert speak_answer("DREAMLIKE") == "It's dreamlike."
    assert speak_enumeration("9") == "That's nine letters."
    parts = write_parts(clue)
    assert "armed" in parts.parse_speech
    assert "like" in parts.parse_speech
    assert "DREAMLIKE" not in parts.parse_speech
    assert study_clue("dreamlike") is not None
    assert study_clue("dreamlike").answer == "DREAMLIKE"


def test_resolve_clue_renders_constructed_study_without_site_html():
    constructed = study_clue("davis-cup")
    assert constructed is not None
    resolved = resolve_clue("davis-cup", clue=constructed)
    assert resolved is constructed
    assert resolve_clue(STUDY_SLUG).answer == "MASS MEDIA"
    assert resolve_clue("mass-media").answer == "MASS MEDIA"
    assert resolve_clue("aimlessly").answer == "AIMLESSLY"
    assert resolve_clue("davis-cup").answer == "DAVIS CUP"
    assert resolve_clue("smiles").answer == "SMILES"
    assert resolve_clue("cole").answer == "COLE"
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
