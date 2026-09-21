import json

from twodown.cli import main
from twodown.youtube import authorize, youtube_hint, youtube_ready


def _clear_youtube(monkeypatch):
    monkeypatch.delenv("TWODOWN_YOUTUBE_TOKEN", raising=False)
    monkeypatch.delenv("TWODOWN_YOUTUBE_CLIENT_SECRET", raising=False)


def test_youtube_ready_needs_refresh_token_and_client(tmp_path, monkeypatch):
    _clear_youtube(monkeypatch)
    token = tmp_path / "youtube-token.json"
    token.write_text(
        json.dumps(
            {
                "refresh_token": "r",
                "client_id": "id.apps.googleusercontent.com",
                "client_secret": "s",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TWODOWN_YOUTUBE_TOKEN", str(token))
    assert youtube_ready() is True


def test_youtube_merges_separate_client_secret(tmp_path, monkeypatch):
    _clear_youtube(monkeypatch)
    token = tmp_path / "youtube-token.json"
    token.write_text(json.dumps({"refresh_token": "r"}), encoding="utf-8")
    client = tmp_path / "client.json"
    client.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "id.apps.googleusercontent.com",
                    "client_secret": "s",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TWODOWN_YOUTUBE_TOKEN", str(token))
    monkeypatch.setenv("TWODOWN_YOUTUBE_CLIENT_SECRET", str(client))
    assert youtube_ready() is True


def test_youtube_not_ready_without_refresh_token(tmp_path, monkeypatch):
    _clear_youtube(monkeypatch)
    token = tmp_path / "youtube-token.json"
    token.write_text(
        json.dumps(
            {
                "token": "ya29.short-lived",
                "client_id": "id.apps.googleusercontent.com",
                "client_secret": "s",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TWODOWN_YOUTUBE_TOKEN", str(token))
    assert youtube_ready() is False
    assert "refresh_token" in youtube_hint()


def test_youtube_auth_without_client_fails(monkeypatch):
    _clear_youtube(monkeypatch)
    try:
        authorize()
    except FileNotFoundError as exc:
        assert "TWODOWN_YOUTUBE_CLIENT_SECRET" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_cli_upload_without_token_exits_2(monkeypatch):
    _clear_youtube(monkeypatch)
    monkeypatch.delenv("TWODOWN_TIKTOK_TOKEN", raising=False)
    monkeypatch.delenv("TWODOWN_META_TOKEN", raising=False)
    assert main(["upload"]) == 2
