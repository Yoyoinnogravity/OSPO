from twodown.ads import ads_enabled, ads_status, ads_txt, adsense_client


def test_ads_off_without_env(monkeypatch):
    monkeypatch.delenv("TWODOWN_ADSENSE_CLIENT", raising=False)
    monkeypatch.delenv("TWODOWN_ADSENSE_SLOT", raising=False)
    assert adsense_client() is None
    assert ads_enabled() is False
    assert ads_txt() is None
    state, _hint = ads_status()
    assert state == "off"


def test_ads_reject_garbage_publisher_id(monkeypatch):
    monkeypatch.setenv("TWODOWN_ADSENSE_CLIENT", "not-a-pub")
    monkeypatch.setenv("TWODOWN_ADSENSE_SLOT", "abc")
    assert ads_enabled() is False
    assert ads_txt() is None


def test_ads_txt_line(monkeypatch):
    monkeypatch.setenv("TWODOWN_ADSENSE_CLIENT", "ca-pub-1234567890123456")
    monkeypatch.setenv("TWODOWN_ADSENSE_SLOT", "9988776655")
    assert ads_enabled() is True
    assert ads_txt() == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n"
    assert ads_status()[0] == "ready"
