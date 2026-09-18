from twodown.config import STUDY_SLUG
from twodown.pipeline import published_clue
from twodown.script import write_parts


def test_study_clue_is_pin_up():
    clue = published_clue(STUDY_SLUG)
    assert clue.slug == "independent-12462-6a"
    assert clue.answer == "PIN-UP"
    assert clue.clue == "Model youngster eating in"
    assert clue.enumeration == "3-2"
    parts = write_parts(clue)
    assert parts.clue_speech == "Model youngster eating in."
    assert parts.letters_speech == "Three hyphen two."
    assert parts.think_speech == "Pause the video while you think."
    assert parts.answer_speech == "The answer is PIN-UP."
    script = parts.full
    assert script.index(parts.clue_speech) < script.index(parts.letters_speech)
    assert script.index(parts.letters_speech) < script.index(parts.think_speech)
    assert script.index(parts.think_speech) < script.index(parts.answer_speech)
    assert script.index(parts.answer_speech) < script.index(parts.parse_speech)
