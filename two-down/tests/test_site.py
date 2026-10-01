from twodown.captions import youtube_description
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.site import (
    _ensure_profile,
    _playable_daily,
    _solved_shelf,
    attach_video_posters,
    earlier_days,
    legacy_videos,
    publish_films,
    publish_site,
    retarget_cdn,
    solved_films,
)
from twodown.youtube import YOUTUBE_CHANNEL, thumbnail_file, upload_short, video_title


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


def test_old_pages_gain_the_profile_picture():
    old = (
        '<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">\n'
        '<a class="wordmark" href="../../index.html">cryptic<span>.fit</span></a>\n'
        '<div class="suggest-forms">'
    )
    once = _ensure_profile(old, picture_panel=True)
    assert 'src="../../assets/profile.png"' in once
    assert 'rel="icon" href="../../assets/profile.png"' in once
    assert "favicon.svg" not in once
    assert once.count('id="picture"') == 1
    assert _ensure_profile(once, picture_panel=True) == once


def test_publish_site_writes_spoiler_pages(tmp_path):
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[_item(), _item(answer="AXES", number="14")])
    root = publish_site(pair, tmp_path)
    index = (root / "index.html").read_text(encoding="utf-8")
    assert "cryptic.fit" in index
    assert "cryptic<span>.fit</span>" in index
    assert "cryptic<span>.fun</span>" not in index
    assert "Rioting led unrest" in index
    assert "Solve" in index
    assert "Fifteen Squared" not in index
    assert (root / "about.html").exists()
    assert "data-voice-btn" in index
    assert "Cryptic Croc" in index
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
    assert "https://fifteensquared.net/" not in about
    assert "only source" in about
    assert "unique cryptic crossword clues and solutions" in about
    assert "We credit all" in about
    assert "the photograph" in about
    assert "the paper, and the photograph" in about
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
    assert "https://cryptic.fit/films.html" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert 'href="films.html">Films</a>' in index
    assert "All the Shorts" in index
    assert "Solve it, I know you can." in index
    assert "croc-hello" in index
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
    assert ".spoiler .answer, .spoiler .parse { display: none; }" in css
    assert "article.clue.is-solved .answer" in css
    app = (tmp_path / "assets" / "app.js").read_text(encoding="utf-8")
    assert "is-solved" in app
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
    assert (tmp_path / "assets" / "profile.png").stat().st_size > 1000
    assert 'class="profile"' in index
    assert 'src="assets/profile.png"' in index
    assert 'rel="icon" href="assets/profile.png"' in index
    assert 'id="picture"' in follow
    assert 'class="channel-picture"' in follow
    assert ".wordmark .profile" in css
    assert "application/rss+xml" in index


def test_solved_shelf_hides_the_answer(tmp_path):
    day = tmp_path / "d" / "2026-09-16"
    day.mkdir(parents=True)
    (day / "index.html").write_text(
        """
        <article class="clue" data-slug="independent-12462-6a">
          <p class="kicker">Independent 12462</p>
          <p class="clue-text">Model youngster eating in (3-2)</p>
          <p class="answer">PIN-UP</p>
          <video src="../../media/independent-12462-6a.mp4" poster="../../media/independent-12462-6a-poster.webp"></video>
        </article>
        """,
        encoding="utf-8",
    )
    media = tmp_path / "media"
    media.mkdir()
    (media / "independent-12462-6a.mp4").write_bytes(b"film")
    (media / "independent-12462-6a-poster.webp").write_bytes(b"RIFF")
    films = solved_films(tmp_path)
    assert films[0].slug == "independent-12462-6a"
    assert films[0].video == "independent-12462-6a.mp4"
    shelf = _solved_shelf(tmp_path)
    assert "PIN-UP" not in shelf
    assert 'href="c/independent-12462-6a/"' in shelf
    assert "independent-12462-6a-poster.webp" in shelf
    played = _playable_daily(tmp_path)
    assert "PIN-UP" not in played
    assert 'src="media/independent-12462-6a.mp4"' in played
    assert 'poster="media/independent-12462-6a-poster.webp"' in played


def test_films_page_serves_legacy_videos_from_the_site(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "rasta-libby.mp4").write_bytes(b"film")
    (media / "rasta-libby.mp3").write_bytes(b"audio")
    (media / "independent-12458-11a.mp4").write_bytes(b"daily")
    clue = tmp_path / "c" / "independent-12458-11a"
    clue.mkdir(parents=True)
    (clue / "index.html").write_text("<p>daily</p>", encoding="utf-8")
    day = tmp_path / "d" / "2026-09-11"
    day.mkdir(parents=True)
    (day / "index.html").write_text(
        '<p class="clue-text">Model youngster eating in (3-2)</p>',
        encoding="utf-8",
    )
    studio = tmp_path / "studio.html"
    studio.write_text(
        '<video src="https://cdn.jsdelivr.net/gh/Yoyoinnogravity/OSPO@cursor/fifteensquared-two-down-agent-42cd/two-down/site/media/rasta-libby.mp4"></video>',
        encoding="utf-8",
    )
    publish_films(tmp_path)
    films = (tmp_path / "films.html").read_text(encoding="utf-8")
    assert "Study cuts" not in films
    assert "rasta-libby" not in films
    assert "jsdelivr" not in films
    assert 'href="d/2026-09-11/"' in films
    assert "independent-12458-11a.mp4" not in films
    studio_html = studio.read_text(encoding="utf-8")
    assert "media/rasta-libby.mp4" in studio_html
    assert 'poster="media/rasta-libby-poster.webp"' in studio_html
    assert "jsdelivr" not in studio_html
    assert [path.name for path in legacy_videos(tmp_path)] == ["rasta-libby.mp4"]
    assert earlier_days(tmp_path)[0][0] == "2026-09-11"


def test_attach_video_posters_follows_the_film_not_an_old_card():
    html = """<video controls playsinline
      poster="media/rasta-study-poster.jpg">
      <source src="media/davis-cup-libby.mp4" type="video/mp4">
    </video>"""
    updated = attach_video_posters(html)
    assert 'poster="media/davis-cup-libby-poster.webp"' in updated
    assert "rasta-study-poster" not in updated
    direct = attach_video_posters('<video src="../../media/fats-libby.mp4"></video>')
    assert 'poster="../../media/fats-libby-poster.webp"' in direct


def test_youtube_thumbnail_is_set_without_dropping_the_video_id(tmp_path, monkeypatch):
    item = _item()
    video = tmp_path / "short.mp4"
    video.write_bytes(b"mp4")
    thumb = tmp_path / "thumb.jpg"
    thumb.write_bytes(b"jpeg")
    item.video_path = str(video)
    item.thumbnail_path = str(thumb)
    assert thumbnail_file(item) == thumb

    seen: dict[str, object] = {}

    class _Call:
        def __init__(self, result):
            self._result = result

        def execute(self):
            if isinstance(self._result, Exception):
                raise self._result
            return self._result

    class _Thumbnails:
        def set(self, **kwargs):
            seen["thumb"] = kwargs
            return _Call(seen.get("thumb_error", {}))

    class _Videos:
        def insert(self, **kwargs):
            seen["insert"] = kwargs
            return _Call({"id": "abc123"})

    class _YouTube:
        def thumbnails(self):
            return _Thumbnails()

        def videos(self):
            return _Videos()

    class _Media:
        def __init__(self, path, **kwargs):
            seen.setdefault("media", []).append((path, kwargs.get("mimetype")))

    monkeypatch.setattr("twodown.youtube._credentials", lambda: object())
    monkeypatch.setattr("googleapiclient.discovery.build", lambda *args, **kwargs: _YouTube())
    monkeypatch.setattr("googleapiclient.http.MediaFileUpload", _Media)

    assert upload_short(item) == "abc123"
    assert item.youtube_id == "abc123"
    assert seen["thumb"]["videoId"] == "abc123"
    assert ("thumb.jpg" in seen["media"][1][0]) or seen["media"][1][0].endswith("thumb.jpg")
    assert seen["media"][1][1] == "image/jpeg"

    item.youtube_id = None
    seen["thumb_error"] = RuntimeError("thumbnail forbidden")
    assert upload_short(item) == "abc123"
    assert item.youtube_id == "abc123"


def test_retarget_cdn_keeps_the_media_filename():
    html = (
        '<video src="https://cdn.jsdelivr.net/gh/Yoyoinnogravity/OSPO@cursor/'
        'fifteensquared-two-down-agent-42cd/two-down/site/media/fats-libby.mp4"></video>'
    )
    assert retarget_cdn(html) == '<video src="media/fats-libby.mp4"></video>'
    assert retarget_cdn(html, "../../") == '<video src="../../media/fats-libby.mp4"></video>'


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
    assert "Fifteen Squared" not in youtube_description(_item())
    assert "Blogged by" in youtube_description(_item())


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

