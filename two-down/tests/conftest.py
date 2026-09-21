import pytest


@pytest.fixture(autouse=True)
def isolate_twodown_secrets(tmp_path, monkeypatch):
    """Keep unit tests away from a real ~/.config/twodown login."""
    cfg = tmp_path / "twodown-config"
    cfg.mkdir()
    monkeypatch.setattr("twodown.tokens.CONFIG_DIR", cfg)
    monkeypatch.setattr("twodown.youtube.CONFIG_DIR", cfg)
    for env in (
        "TWODOWN_YOUTUBE_TOKEN",
        "TWODOWN_YOUTUBE_CLIENT_SECRET",
        "TWODOWN_TIKTOK_TOKEN",
        "TWODOWN_META_TOKEN",
        "TWODOWN_META_ACCESS_TOKEN",
        "TWODOWN_FB_PAGE_ID",
        "TWODOWN_IG_USER_ID",
    ):
        monkeypatch.delenv(env, raising=False)
