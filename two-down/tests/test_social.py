from pathlib import Path

from twodown.captions import social_caption
from twodown.meta import facebook_ready, instagram_ready, upload_facebook, upload_instagram
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.social import platform_status, publish_pair
from twodown.tiktok import tiktok_ready, upload_short as upload_tiktok


def _item(video: Path | None = None) -> SpokenClue:
    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12458",
        setter="Phi",
        blogger="duncanshiell",
        number="11",
        direction="across",
        clue="Hotel worker with a lot of guts taking on hotel work",
        enumeration="7",
        answer="BELLHOP",
        parse="BELL + H + OP",
        device="container",
        enumeration_ok=True,
    )
    return SpokenClue(
        clue=clue,
        script="x",
        voice="en-GB-SoniaNeural",
        video_path=str(video) if video else None,
        site_path="https://cryptic.fun/c/independent-12458-11a/",
    )


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        if "creator_info" in url:
            return FakeResponse(
                {"data": {"privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"]}, "error": {"code": "ok"}}
            )
        if "video/init" in url:
            return FakeResponse(
                {
                    "data": {"upload_url": "https://open-upload.tiktokapis.com/upload/", "publish_id": "v_pub_1"},
                    "error": {"code": "ok"},
                }
            )
        if "status/fetch" in url:
            return FakeResponse(
                {
                    "data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": ["777"]},
                    "error": {"code": "ok"},
                }
            )
        if "rupload.facebook.com/ig-api-upload" in url:
            return FakeResponse({"success": True})
        if "rupload.facebook.com/video-upload" in url:
            return FakeResponse({"success": True})
        if url.endswith("/media_publish"):
            return FakeResponse({"id": "ig_99"})
        if url.endswith("/media"):
            return FakeResponse({"id": "ig_c1", "uri": "https://rupload.facebook.com/ig-api-upload/v22.0/ig_c1"})
        if url.endswith("/video_reels"):
            body = kwargs.get("data") or {}
            if body.get("upload_phase") == "start":
                return FakeResponse(
                    {"video_id": "fb_1", "upload_url": "https://rupload.facebook.com/video-upload/v22.0/fb_1"}
                )
            return FakeResponse({"success": True})
        return FakeResponse({})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url))
        return FakeResponse({"error": {"code": "ok"}})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeResponse({"status_code": "FINISHED"})


def test_social_caption_does_not_spoil_the_answer():
    text = social_caption(_item())
    assert "BELLHOP" not in text
    assert "Hotel worker" in text
    assert "#crypticfun" in text
    assert "cryptic.fun" in text


def test_platforms_need_tokens_by_default(monkeypatch):
    monkeypatch.delenv("TWODOWN_TIKTOK_TOKEN", raising=False)
    monkeypatch.delenv("TWODOWN_META_TOKEN", raising=False)
    monkeypatch.delenv("TWODOWN_FB_PAGE_ID", raising=False)
    monkeypatch.delenv("TWODOWN_IG_USER_ID", raising=False)
    monkeypatch.delenv("TWODOWN_META_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TWODOWN_YOUTUBE_TOKEN", raising=False)
    status = platform_status()
    assert status["tiktok"] is False
    assert status["instagram"] is False
    assert status["facebook"] is False
    assert tiktok_ready() is False
    assert instagram_ready() is False
    assert facebook_ready() is False


def test_tiktok_file_upload(tmp_path, monkeypatch):
    token = tmp_path / "tiktok.json"
    token.write_text('{"access_token": "act.example"}', encoding="utf-8")
    monkeypatch.setenv("TWODOWN_TIKTOK_TOKEN", str(token))
    video = tmp_path / "short.mp4"
    video.write_bytes(b"fake-mp4-bytes")
    item = _item(video)
    assert upload_tiktok(item, social_caption(item), session=FakeSession()) == "777"
    assert item.tiktok_id == "777"


def test_instagram_and_facebook_reels(tmp_path, monkeypatch):
    token = tmp_path / "meta.json"
    token.write_text('{"access_token": "page-token", "page_id": "111", "ig_user_id": "222"}', encoding="utf-8")
    monkeypatch.setenv("TWODOWN_META_TOKEN", str(token))
    video = tmp_path / "short.mp4"
    video.write_bytes(b"fake-mp4-bytes")
    item = _item(video)
    session = FakeSession()
    assert upload_instagram(item, social_caption(item), session=session) == "ig_99"
    assert upload_facebook(item, social_caption(item), "Cryptic Fun · test", session=session) == "fb_1"
    assert item.instagram_id == "ig_99"
    assert item.facebook_id == "fb_1"


def test_publish_pair_keeps_going_if_tiktok_fails(tmp_path, monkeypatch):
    token = tmp_path / "meta.json"
    token.write_text('{"access_token": "page-token", "page_id": "111", "ig_user_id": "222"}', encoding="utf-8")
    monkeypatch.setenv("TWODOWN_META_TOKEN", str(token))
    video = tmp_path / "short.mp4"
    video.write_bytes(b"fake-mp4-bytes")
    item = _item(video)
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[item])

    def boom(*_args, **_kwargs):
        raise RuntimeError("tiktok down")

    monkeypatch.setattr("twodown.social.upload_tiktok", boom)
    monkeypatch.setattr("twodown.social.tiktok_ready", lambda: True)
    monkeypatch.setattr("twodown.social.upload_instagram", lambda *_a, **_k: "ig_ok")
    monkeypatch.setattr("twodown.social.upload_facebook", lambda *_a, **_k: "fb_ok")
    monkeypatch.setattr("twodown.social.youtube_ready", lambda: False)
    notes = publish_pair(pair, youtube=False)
    assert any(str(v).startswith("error:") for v in notes["tiktok"])
    assert notes["instagram"] == ["ig_ok"]
    assert notes["facebook"] == ["fb_ok"]
