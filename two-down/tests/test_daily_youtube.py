from twodown.models import Clue, DailyPair, SpokenClue
from twodown.pipeline import published_clue
from twodown.staging import apply_feed_matches, load_uploads, parse_channel_feed, record_youtube_upload
from twodown.youtube import upload_pair, video_title


def _clue(**kwargs) -> Clue:
    fields = dict(
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
    fields.update(kwargs)
    return Clue(**fields)


def test_record_youtube_upload_keeps_the_first_id(tmp_path):
    slug = "independent-12458-11a"
    (tmp_path / "c" / slug).mkdir(parents=True)
    (tmp_path / "c" / slug / "index.html").write_text("<p>x</p>", encoding="utf-8")
    assert record_youtube_upload(tmp_path, slug, "7q-WFyj0WnA", "2026-10-08")
    assert not record_youtube_upload(tmp_path, slug, "iP6Zh87lE_8", "2026-10-09")
    saved = load_uploads(tmp_path)
    assert saved["videos"][0]["youtube_id"] == "7q-WFyj0WnA"
    assert saved["videos"][0]["uploaded_at"] == "2026-10-08"


def test_upload_pair_does_not_post_a_short_that_already_has_an_id(tmp_path, monkeypatch):
    slug = "independent-12458-11a"
    (tmp_path / "c" / slug).mkdir(parents=True)
    (tmp_path / "c" / slug / "index.html").write_text("<p>x</p>", encoding="utf-8")
    record_youtube_upload(tmp_path, slug, "7q-WFyj0WnA", "2026-10-08")
    monkeypatch.setattr("twodown.youtube.SITE_ROOT", tmp_path)
    called: list[str] = []
    monkeypatch.setattr("twodown.youtube.upload_short", lambda *_a, **_k: called.append("posted") or "NEWVIDEO111")
    pair = DailyPair(date="2026-10-08", voice="en-US-AvaNeural", clues=[SpokenClue(clue=_clue(), script="", voice="en-US-AvaNeural")])
    assert upload_pair(pair) == ["7q-WFyj0WnA"]
    assert called == []
    assert pair.clues[0].youtube_id == "7q-WFyj0WnA"


def test_published_kicker_keeps_a_clue_of_the_day_label(tmp_path):
    day = tmp_path / "d" / "2026-10-08"
    day.mkdir(parents=True)
    (day / "index.html").write_text(
        """
        <article class="clue" data-slug="guardian-30130-1a">
          <p class="kicker">Clue of the day · Guardian 30130 · Paul · 1 across · charade</p>
          <p class="clue-text">Fair surface hiding the real work inside (7)</p>
          <p class="answer">EXAMPLE</p>
          <p class="parse">A fair surface hiding the real work</p>
          <p class="credit">Parse via <a href="https://fifteensquared.net/2026/10/08/guardian-30130-by-paul/">blogger</a></p>
        </article>
        """,
        encoding="utf-8",
    )
    clue = published_clue("guardian-30130-1a", tmp_path)
    assert clue.paper == "Guardian"
    assert clue.theme == "Clue of the day"
    assert clue.answer == "EXAMPLE"
    assert "Clue of the day" in video_title(clue)
    assert "EXAMPLE" not in video_title(clue)


def test_feed_matches_the_uploaded_title(tmp_path):
    slug = "independent-12481-1a"
    (tmp_path / "c" / slug).mkdir(parents=True)
    (tmp_path / "c" / slug / "index.html").write_text("<p>x</p>", encoding="utf-8")
    title = "cryptic.fit · Clue of the day · Native Australian, reportedly, may fish with spectacles (8) #Shorts"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
      <entry>
        <yt:videoId>7q-WFyj0WnA</yt:videoId>
        <title>{title}</title>
        <published>2026-10-08T08:00:00+00:00</published>
      </entry>
    </feed>
    """
    applied = apply_feed_matches(tmp_path, parse_channel_feed(xml), [(slug, title)])
    assert applied[slug]["youtube_id"] == "7q-WFyj0WnA"
