from twodown.captions import youtube_description
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.site import publish_site
from twodown.youtube import YOUTUBE_CHANNEL, video_title


def _item(answer: str = "END RESULT", number: str = "12") -> SpokenClue:
    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12458",
        setter="Phi",
        blogger="duncanshiell",
        number=number,
        direction="across",
        clue="Rioting led unrest in the final analysis",
        enumeration="3,6",
        answer=answer,
        parse="Anagram of LED UNREST",
        device="anagram",
        enumeration_ok=True,
    )
    return SpokenClue(clue=clue, script="cryptic.fit. The answer is END RESULT.", voice="en-GB-SoniaNeural")


def test_publish_site_writes_spoiler_pages(tmp_path):
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[_item(), _item(answer="AXES", number="14")])
    root = publish_site(pair, tmp_path)
    index = (root / "index.html").read_text(encoding="utf-8")
    assert "cryptic.fit" in index
    assert "cryptic<span>.fit</span>" in index
    assert "cryptic<span>.fun</span>" not in index
    assert "Rioting led unrest" in index
    assert "Solve" in index
    assert "Fifteen Squared" in index
    assert (root / "about.html").exists()
    assert "data-voice-btn" in index
    assert "Sonia" in index
    assert "Ryan" in index
    assert "Libby" in index
    assert "Thomas" in index
    assert "parse-voice" in index
    assert "data-scene-btn" in index
    assert "Machu Picchu" in index
    assert "Newsprint" in index
    assert "data-scene-prefix" in index
    assert (tmp_path / "media" / "scenes" / "machu-picchu.webp").exists()
    assert (tmp_path / "suggest.html").exists()
    suggest = (tmp_path / "suggest.html").read_text(encoding="utf-8")
    assert "aledmorgan@gmail.com" in suggest
    assert "data-suggest-form" in suggest
    assert "data-subscribe-form" in suggest
    assert "Suggest" in index
    about = (tmp_path / "about.html").read_text(encoding="utf-8")
    assert "Wikimedia Commons" in about
    assert "Pedro Szekely" in about
    assert "TikTok" in about
    assert "Instagram" in about
    assert "Facebook" in about
    assert "aledmorgan@gmail.com" in about
    assert "https://fifteensquared.net/" in about
    assert "only source" in about
    assert "unique cryptic crossword clues and solutions" in about
    assert "We credit all" in about
    assert "the photograph" in about
    assert (tmp_path / "c" / "independent-12458-12a" / "index.html").exists()
    assert (tmp_path / "support.html").exists()
    assert (tmp_path / "privacy.html").exists()
    assert "Keep the pair coming" in index
    assert index.find("Keep the pair coming") < index.find("When the hits come")
    assert "data-follow-toggle" in index
    assert "Following" in index
    assert (tmp_path / "follow.html").exists()
    follow = (tmp_path / "follow.html").read_text(encoding="utf-8")
    assert "data-subscribe-form" in follow
    assert "feed.xml" in follow
    assert "youtube.com/@crypticfit" in follow
    assert "https://cryptic.fit/follow.html" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "How we pay for this" in index
    assert "adsbygoogle" not in index
    assert not (tmp_path / "ads.txt").exists()
    support = (tmp_path / "support.html").read_text(encoding="utf-8")
    assert "YouTube" in support
    assert "Sponsor" in support
    assert "never sit on the answer" in support
    clue_page = (tmp_path / "c" / "independent-12458-12a" / "index.html").read_text(encoding="utf-8")
    assert "adsbygoogle" not in clue_page
    assert (tmp_path / "robots.txt").exists()
    css = (tmp_path / "assets" / "style.css").read_text(encoding="utf-8")
    assert "body.scene-photo header a" in css
    assert 'rel="canonical"' in index
    assert 'property="og:title"' in index
    assert "application/ld+json" in index
    assert "END RESULT" not in index.split('name="description"', 1)[1].split(">", 1)[0]
    assert 'data-nosnippet' in clue_page
    assert "END RESULT" not in clue_page.split('name="description"', 1)[1].split(">", 1)[0]
    assert "Rioting led unrest" in clue_page.split("<h1>", 1)[1].split("</h1>", 1)[0]
    robots = (tmp_path / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://cryptic.fit/sitemap.xml" in robots
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://cryptic.fit/" in sitemap
    assert "https://cryptic.fit/c/independent-12458-12a/" in sitemap
    feed = (tmp_path / "feed.xml").read_text(encoding="utf-8")
    assert "END RESULT" not in feed
    assert "Rioting led unrest" in feed
    assert (tmp_path / "media" / "og.webp").exists()
    assert (tmp_path / "CNAME").read_text(encoding="utf-8") == "cryptic.fit\n"
    assert (tmp_path / ".nojekyll").exists()
    assert (tmp_path / "assets" / "favicon.svg").exists()
    assert "application/rss+xml" in index


def test_youtube_titles_use_cryptic_fun_channel():
    clue = _item().clue
    title = video_title(clue)
    assert title.startswith("cryptic.fit · ")
    assert title.endswith("#Shorts")
    assert YOUTUBE_CHANNEL == "cryptic.fit"
    assert len(title) <= 100
    assert "https://cryptic.fit/support.html" in youtube_description(_item())
    assert "unique cryptic crossword clues and solutions" in youtube_description(_item())
    assert "We credit all" in youtube_description(_item())
    assert "Fifteen Squared" in youtube_description(_item())


def test_ads_on_writes_ads_txt_and_unit(tmp_path, monkeypatch):
    monkeypatch.setenv("TWODOWN_ADSENSE_CLIENT", "ca-pub-1234567890123456")
    monkeypatch.setenv("TWODOWN_ADSENSE_SLOT", "1234567890")
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[_item(), _item(answer="AXES", number="14")])
    root = publish_site(pair, tmp_path)
    ads = (root / "ads.txt").read_text(encoding="utf-8")
    assert ads.strip() == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"
    index = (root / "index.html").read_text(encoding="utf-8")
    assert "adsbygoogle" in index
    assert "Advertisement" in index
    assert "ca-pub-1234567890123456" in index
    assert "How we pay for this" not in index
    clue_page = (root / "c" / "independent-12458-12a" / "index.html").read_text(encoding="utf-8")
    assert "adsbygoogle" not in clue_page
    assert "pagead2.googlesyndication.com" not in clue_page

