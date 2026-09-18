from twodown.config import STUDY_SLUG
from twodown.pipeline import published_clue
from twodown.script import speak_answer, speak_parse_tokens, write_parts


def test_study_clue_is_pin_up():
    clue = published_clue(STUDY_SLUG)
    assert clue.slug == "independent-12462-6a"
    assert clue.answer == "PIN-UP"
    assert clue.clue == "Model youngster eating in"
    assert clue.enumeration == "3-2"
    parts = write_parts(clue)
    assert parts.intro_speech == "Here is your daily dose of cryptic fun."
    assert parts.clue_speech == "Model youngster eating in."
    assert parts.letters_speech == "Three hyphen two."
    assert parts.think_speech == "Pause the video while you think."
    assert parts.answer_speech == "The answer is pin-up."
    assert parts.answer_speech == speak_answer(clue.answer)
    assert parts.outro_speech == "Thanks for thinking with cryptic.fun."
    script = parts.full
    assert script.index(parts.intro_speech) < script.index(parts.clue_speech)
    assert script.index(parts.clue_speech) < script.index(parts.letters_speech)
    assert script.index(parts.letters_speech) < script.index(parts.think_speech)
    assert script.index(parts.think_speech) < script.index(parts.answer_speech)
    assert script.index(parts.answer_speech) < script.index(parts.parse_speech)
    assert script.index(parts.parse_speech) < script.index(parts.outro_speech)


def test_spoken_parse_says_pup_as_a_word():
    clue = published_clue(STUDY_SLUG)
    parts = write_parts(clue)
    assert "pup" in parts.parse_speech
    assert "PUP" not in parts.parse_speech
    assert speak_parse_tokens("PUP") == "pup"
    assert speak_parse_tokens("PUP containing IN") == "pup containing in"
    assert speak_parse_tokens("PIN-UP") == "pin-up"
    assert speak_parse_tokens("END RESULT") == "end result"
    assert speak_parse_tokens("Three hyphen two.") == "Three hyphen two."
    assert speak_parse_tokens("Slang for an attractive person.") == "Slang for an attractive person."
    assert speak_parse_tokens("12 across, 3-2") == "12 across, 3-2"
