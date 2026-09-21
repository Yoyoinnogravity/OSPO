from twodown.cli import main
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.pipeline import load_published_pair, load_upload_pair, load_youtube_queue, unpublished_shorts
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

    def fake_upload(ready_pair, privacy="public", limit=1):
        return upload_pair(ready_pair, privacy=privacy, limit=limit)

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


def test_upload_pair_posts_one_new_short_by_default(monkeypatch):
    calls: list[str] = []

    def fake_short(item, privacy="public"):
        calls.append(item.clue.answer)
        item.youtube_id = f"yt-{len(calls)}"
        return item.youtube_id

    monkeypatch.setattr("twodown.youtube.upload_short", fake_short)
    pair = DailyPair(date="2026-09-16", voice="en-GB-SoniaNeural", clues=[_item("PIN-UP"), _item("SELF")])
    assert upload_pair(pair) == ["yt-1"]
    assert calls == ["PIN-UP"]
    assert pair.clues[1].youtube_id is None


def test_unpublished_queue_is_oldest_daily_pair_first():
    waiting = unpublished_shorts()
    slugs = [item.clue.slug for _date, item in waiting]
    assert slugs[0] == "independent-12458-11a"
    assert len(slugs) == 12
    assert slugs[1] == "financial-times-18477-14a"
    assert "independent-12462-6a" in slugs
    assert "smiles-libby" not in slugs
    assert "rasta-study" not in slugs
    queued = load_youtube_queue(limit=1)
    assert queued is not None
    assert [item.clue.slug for item in queued.clues] == ["independent-12458-11a"]


def test_unpublished_queue_skips_ledger(tmp_path, monkeypatch):
    waiting = unpublished_shorts()
    first_date, first = waiting[0]
    first.youtube_id = "already"
    record_youtube(DailyPair(date=first_date, voice=first.voice, clues=[first]), tmp_path)
    monkeypatch.setattr(
        "twodown.pipeline.apply_ledger",
        lambda pair, site_root=None: apply_ledger(pair, tmp_path),
    )
    remaining = unpublished_shorts()
    assert remaining[0][1].clue.slug != first.clue.slug


def test_cli_queue_lists_oldest_first(capsys):
    assert main(["queue"]) == 0
    out = capsys.readouterr().out
    assert "12 unpublished" in out
    assert out.index("independent-12458-11a") < out.index("independent-12462-6a")
