from twodown.models import Clue, DailyPair, SpokenClue
from twodown.site import publish_site
from twodown.youtube import YOUTUBE_CHANNEL, video_title
from twodown.youtube import YOUTUBE_CHANNEL, video_title


def _item(answer: str = "END RESULT", number: str = "12") -> SpokenClue:
    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12458",
        setter="Phi",
        blogger="duncanshiell",
        number=number,
        direction="across",
        clue="Rioting led unrest in the final analysis",
        enumeration="3,6",
        answer=answer,
        parse="Anagram of LED UNREST",
        device="anagram",
        enumeration_ok=True,
    )
    return SpokenClue(clue=clue, script="cryptic.fun. The answer is END RESULT.", voice="en-GB-SoniaNeural")


def test_publish_site_writes_spoiler_pages(tmp_path):
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[_item(), _item(answer="AXES", number="14")])
    root = publish_site(pair, tmp_path)
    index = (root / "index.html").read_text(encoding="utf-8")
    assert "cryptic.fun" in index
    assert "Rioting led unrest" in index
    assert "Solve" in index
    assert "Fifteen Squared" in index
    assert (root / "about.html").exists()
    assert "data-voice-btn" in index
    assert "Sonia" in index
    assert "Ryan" in index
    assert "Libby" in index
    assert "Thomas" in index
    assert "parse-voice" in index
    assert (tmp_path / "c" / "independent-12458-12a" / "index.html").exists()


def test_youtube_titles_use_cryptic_fun_channel():
    clue = _item().clue
    title = video_title(clue)
    assert title.startswith("Cryptic Fun · ")
    assert title.endswith("#Shorts")
    assert YOUTUBE_CHANNEL == "Cryptic Fun"
    assert len(title) <= 100
