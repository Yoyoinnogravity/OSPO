from unittest.mock import patch

import requests

from twodown.live import (
    NAMECHEAP_BUY,
    PR_URL,
    go_live_next_steps,
    probe,
    registry_status,
)


class FakeResponse:
    def __init__(self, status: int):
        self.status_code = status


def test_registry_absent_on_rdap_404():
    with patch("twodown.live.requests.get", return_value=FakeResponse(404)):
        assert registry_status() == ("absent", "RDAP 404 — not in the .fun registry")


def test_registry_present_on_rdap_200():
    with patch("twodown.live.requests.get", return_value=FakeResponse(200)):
        assert registry_status() == ("present", "RDAP 200")


def test_registry_unknown_on_timeout():
    with patch("twodown.live.requests.get", side_effect=requests.exceptions.Timeout()):
        assert registry_status() == ("unknown", "Timeout")


def test_go_live_when_name_is_not_registered():
    steps = go_live_next_steps(registry="absent", pages_live=False, domain_live=False)
    assert NAMECHEAP_BUY in steps[0]
    assert "cryptic.fit" in steps[1]
    assert PR_URL in steps[2]
    assert "GitHub Actions" in steps[3]
    assert not any("A records" in step for step in steps)


def test_go_live_when_registered_but_pages_off():
    steps = go_live_next_steps(registry="present", pages_live=False, domain_live=False)
    assert any("Merge" in step for step in steps)
    assert any("A records" in step for step in steps)
    assert any("185.199.108.153" in step for step in steps)


def test_go_live_empty_when_site_is_up():
    assert go_live_next_steps(registry="present", pages_live=True, domain_live=True) == []


def test_probe_live_on_200():
    with patch("twodown.live.requests.get", return_value=FakeResponse(200)):
        assert probe("https://example.test/") == ("live", "200")


def test_probe_down_on_connection_error():
    with patch(
        "twodown.live.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        assert probe("https://cryptic.fun/") == ("down", "no DNS or connection")
