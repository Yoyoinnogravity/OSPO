import pytest

from twodown.youtube import authorization_code, youtube_ready


def test_authorization_code_from_redirect_url():
    url = "http://localhost/?state=abc&code=4%2F0test&scope=youtube"
    assert authorization_code(url) == "4/0test"


def test_authorization_code_accepts_bare_code():
    assert authorization_code("4/0bare-code") == "4/0bare-code"


def test_authorization_code_rejects_empty():
    with pytest.raises(ValueError, match="No authorization code"):
        authorization_code("   ")


def test_youtube_ready_false_without_token(monkeypatch):
    monkeypatch.delenv("TWODOWN_YOUTUBE_TOKEN", raising=False)
    assert youtube_ready() is False
