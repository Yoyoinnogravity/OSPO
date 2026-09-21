import json

from twodown.cli import main
from twodown.youtube import (
    authorization_code,
    authorize,
    finish_authorization,
    save_client_secret,
    start_authorization,
    youtube_hint,
    youtube_ready,
)


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


def _desktop_client() -> dict:
    return {
        "installed": {
            "client_id": "123.apps.googleusercontent.com",
            "client_secret": "secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def test_save_client_secret_from_json(tmp_path, monkeypatch):
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    dest = save_client_secret(json.dumps(_desktop_client()))
    assert dest == tmp_path / "youtube-client-secret.json"
    assert json.loads(dest.read_text(encoding="utf-8"))["installed"]["client_id"].startswith("123.")


def test_authorization_code_from_redirect_or_bare():
    assert authorization_code("http://localhost/?code=abc123&scope=x") == "abc123"
    assert authorization_code("'http://127.0.0.1/?code=xyz'") == "xyz"
    assert authorization_code("bare-code") == "bare-code"


def test_start_authorization_writes_pending(tmp_path, monkeypatch):
    _clear_youtube(monkeypatch)
    monkeypatch.setenv("TWODOWN_YOUTUBE_CLIENT_SECRET", json.dumps(_desktop_client()))
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    url = start_authorization()
    assert "accounts.google.com" in url
    pending = json.loads((tmp_path / "youtube-auth-pending.json").read_text(encoding="utf-8"))
    assert pending["code_verifier"]
    assert pending["redirect_uri"] == "http://localhost"
    assert (tmp_path / "youtube-client-secret.json").exists()


def test_finish_without_pending_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    try:
        finish_authorization("http://localhost/?code=abc")
    except FileNotFoundError as exc:
        assert "--start" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_finish_authorization_writes_token(tmp_path, monkeypatch):
    _clear_youtube(monkeypatch)
    monkeypatch.setenv("TWODOWN_YOUTUBE_CLIENT_SECRET", json.dumps(_desktop_client()))
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    start_authorization()

    class FakeCreds:
        def to_json(self):
            return json.dumps(
                {
                    "refresh_token": "r",
                    "client_id": "123.apps.googleusercontent.com",
                    "client_secret": "secret",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )

    def fake_fetch(self, code=None):
        assert code == "from-browser"
        self.credentials = FakeCreds()

    monkeypatch.setattr("google_auth_oauthlib.flow.InstalledAppFlow.fetch_token", fake_fetch)
    dest = finish_authorization("http://localhost/?code=from-browser")
    assert dest == tmp_path / "youtube-token.json"
    assert json.loads(dest.read_text(encoding="utf-8"))["refresh_token"] == "r"
    assert not (tmp_path / "youtube-auth-pending.json").exists()


def test_cli_youtube_auth_start(tmp_path, monkeypatch, capsys):
    _clear_youtube(monkeypatch)
    monkeypatch.setenv("TWODOWN_YOUTUBE_CLIENT_SECRET", json.dumps(_desktop_client()))
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    assert main(["youtube-auth", "--start"]) == 0
    out = capsys.readouterr().out
    assert "Cryptic Fit" in out
    assert "accounts.google.com" in out
    assert "--finish" in out


def test_cli_youtube_auth_save_client(tmp_path, monkeypatch, capsys):
    _clear_youtube(monkeypatch)
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", tmp_path)
    client = tmp_path / "from-downloads.json"
    client.write_text(json.dumps(_desktop_client()), encoding="utf-8")
    assert main(["youtube-auth", "--save-client", str(client)]) == 0
    assert "youtube-client-secret.json" in capsys.readouterr().out
    assert (tmp_path / "youtube-client-secret.json").exists()
