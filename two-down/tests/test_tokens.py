from twodown.tokens import secret_text


def test_secret_text_reads_inline_json(monkeypatch):
    monkeypatch.setenv("TWODOWN_TIKTOK_TOKEN", '{"access_token": "act.example"}')
    assert secret_text("TWODOWN_TIKTOK_TOKEN", "tiktok-token.json") == '{"access_token": "act.example"}'


def test_secret_text_reads_file_path(tmp_path, monkeypatch):
    token = tmp_path / "youtube-token.json"
    token.write_text('{"refresh_token": "r"}', encoding="utf-8")
    monkeypatch.setenv("TWODOWN_YOUTUBE_TOKEN", str(token))
    assert secret_text("TWODOWN_YOUTUBE_TOKEN", "youtube-token.json") == '{"refresh_token": "r"}'


def test_secret_text_missing_path_is_none(monkeypatch):
    monkeypatch.setenv("TWODOWN_YOUTUBE_TOKEN", "/tmp/does-not-exist-twodown.json")
    assert secret_text("TWODOWN_YOUTUBE_TOKEN", "youtube-token.json") is None
