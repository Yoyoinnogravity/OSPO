from twodown.social import connect_instructions


def test_connect_names_every_secret():
    text = connect_instructions()
    for env in ("TWODOWN_META_TOKEN", "TWODOWN_TIKTOK_TOKEN", "TWODOWN_YOUTUBE_TOKEN"):
        assert env in text


def test_connect_gives_the_meta_permissions_and_ids():
    text = connect_instructions()
    assert "instagram_content_publish" in text
    assert "pages_manage_posts" in text
    assert "GET /me/accounts" in text
    assert "instagram_business_account" in text


def test_connect_warns_about_tiktok_audit():
    assert "audits" in connect_instructions()


def test_connect_never_asks_for_a_password():
    assert "never a password" in connect_instructions()


def test_connect_youtube_prefers_cryptic_fun_then_personal():
    text = connect_instructions()
    youtube = text[text.index("YOUTUBE") :]
    assert "youtube.com/@crypticfun" in youtube
    assert "youtube.com/@carbonyoyo" in youtube
    assert youtube.index("@crypticfun") < youtube.index("@carbonyoyo")
    assert "Prefer" in youtube
