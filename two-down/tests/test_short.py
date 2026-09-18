from twodown.config import PINUP_SLUG, STUDY_SLUG
from twodown.pipeline import published_clue, resolve_clue, study_clue
from twodown.script import speak_answer, speak_enumeration, speak_parse_tokens, write_parts


def test_study_clue_is_dreamlike():
    clue = study_clue(STUDY_SLUG)
    assert clue is not None
    assert clue.slug == "guardian-30115-12a"
    assert clue.answer == "DREAMLIKE"
    assert clue.clue == "Doctor armed with positive response, as in a trance"
    assert clue.enumeration == "9"
    assert clue.device == "anagram"
    assert clue.setter == "Brendan"
    assert clue.paper == "Guardian"
    assert clue.puzzle_id == "30115"
    assert clue.number == "12"
    assert clue.direction == "across"
    assert clue.blogger == "manehi"
    assert clue.source_url == (
        "https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/"
    )
    assert "(armed)*" in clue.parse
    assert "LIKE" in clue.parse
    parts = write_parts(clue)
    assert parts.intro_speech == "Here is your daily dose of cryptic fun."
    assert parts.clue_speech == "Doctor armed with positive response, as in a trance."
    assert parts.letters_speech == "Nine letters."
    assert parts.think_speech == "Pause the video while you think."
    assert parts.hint_speech == "Here's a clue."
    assert parts.answer_speech == "The answer is dreamlike."
    assert parts.answer_speech == speak_answer(clue.answer)
    assert parts.outro_speech == "Thanks for thinking with cryptic.fun."
    assert "Brendan" in parts.parse_speech
    assert "Guardian" in parts.parse_speech
    assert "Fifteen Squared" in parts.parse_speech
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
    assert script.index(parts.parse_speech) < script.index(parts.outro_speech)


def test_speak_answer_dreamlike_is_a_word():
    assert speak_answer("DREAMLIKE") == "The answer is dreamlike."
    assert speak_answer("DREAMLIKE") != "The answer is D-R-E-A-M-L-I-K-E."
    assert "dreamlike" in speak_answer("DREAMLIKE")


def test_nine_letters():
    clue = study_clue()
    assert clue is not None
    assert clue.enumeration == "9"
    assert speak_enumeration("9") == "Nine letters."
    assert speak_enumeration(clue.enumeration) == "Nine letters."


def test_spoken_parse_says_armed_and_like_as_words():
    clue = study_clue(STUDY_SLUG)
    assert clue is not None
    parts = write_parts(clue)
    assert "armed" in parts.parse_speech
    assert "like" in parts.parse_speech
    assert "anagram indicator" in parts.parse_speech
    assert "positive response" in parts.parse_speech
    assert "as in a trance" in parts.parse_speech
    assert "ARMED" not in parts.parse_speech
    assert "LIKE" not in parts.parse_speech
    assert "DREAMLIKE" not in parts.parse_speech
    assert speak_parse_tokens("ARMED") == "armed"
    assert speak_parse_tokens("LIKE") == "like"
    assert speak_parse_tokens("DREAMLIKE") == "dreamlike"
    assert speak_parse_tokens("ARMED plus LIKE") == "armed plus like"
    assert "dreamlike" not in parts.hint_speech.lower()
    assert "DREAMLIKE" not in parts.hint_speech


def test_resolve_clue_renders_constructed_study_without_site_html():
    constructed = study_clue("dreamlike")
    assert constructed is not None
    resolved = resolve_clue("dreamlike", clue=constructed)
    assert resolved is constructed
    assert resolve_clue(STUDY_SLUG).answer == "DREAMLIKE"


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
