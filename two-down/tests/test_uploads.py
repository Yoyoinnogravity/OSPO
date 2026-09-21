from twodown.models import Clue, DailyPair, SpokenClue
from twodown.pipeline import load_published_pair, load_upload_pair
from twodown.social import publish_pair
from twodown.uploads import apply_ledger, record_youtube
from twodown.youtube import upload_pair


def _item(slug_answer: str = "PIN-UP") -> SpokenClue:
    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12462",
        setter="Eccles",
        blogger="Quirister",
        number="6",
        direction="across",
        clue="Model youngster eating in",
        enumeration="3-2",
        answer=slug_answer,
        parse="PUP containing IN",
        device="container",
        enumeration_ok=True,
    )
    return SpokenClue(clue=clue, script="x", voice="en-GB-SoniaNeural")


def test_ledger_remembers_youtube_ids(tmp_path):
    pair = DailyPair(date="2026-09-16", voice="en-GB-SoniaNeural", clues=[_item()])
    pair.clues[0].youtube_id = "abc123"
    assert record_youtube(pair, tmp_path) is True
    assert (tmp_path / "uploads.json").exists()
    again = DailyPair(date="2026-09-16", voice="en-GB-SoniaNeural", clues=[_item()])
    apply_ledger(again, tmp_path)
    assert again.clues[0].youtube_id == "abc123"
    assert again.youtube_ids == ["abc123"]
    assert record_youtube(again, tmp_path) is False


def test_load_published_pair_from_site():
    pair = load_published_pair("2026-09-16")
    assert pair is not None
    assert pair.date == "2026-09-16"
    assert [item.clue.answer for item in pair.clues] == ["PIN-UP", "SELF"]
    assert pair.clues[0].video_path.endswith("independent-12462-6a.mp4")
    assert pair.clues[1].video_path.endswith("guardian-30113-9a.mp4")


def test_load_upload_pair_falls_back_to_site(tmp_path):
    pair = load_upload_pair(tmp_path, "2026-09-16")
    assert pair.clues[0].clue.slug == "independent-12462-6a"


def test_publish_pair_skips_youtube_already_in_ledger(tmp_path, monkeypatch):
    pair = load_published_pair("2026-09-16")
    pair.clues[0].youtube_id = "already1"
    pair.clues[1].youtube_id = "already2"
    record_youtube(pair, tmp_path)

    def fake_upload(ready_pair, privacy="public"):
        return [item.youtube_id or f"new-{privacy}" for item in ready_pair.clues]

    monkeypatch.setattr("twodown.social.youtube_ready", lambda: True)
    monkeypatch.setattr("twodown.social.upload_youtube", fake_upload)
    fresh = load_published_pair("2026-09-16")
    notes = publish_pair(fresh, tiktok=False, instagram=False, facebook=False, site_root=tmp_path)
    assert notes["youtube"] == ["already1", "already2"]
    assert fresh.clues[0].youtube_id == "already1"


def test_upload_pair_does_not_call_api_when_id_exists():
    pair = DailyPair(date="2026-09-16", voice="en-GB-SoniaNeural", clues=[_item()])
    pair.clues[0].youtube_id = "keep-me"
    assert upload_pair(pair) == ["keep-me"]
