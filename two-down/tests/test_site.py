from twodown.captions import youtube_description
from twodown.models import Clue, DailyPair, SpokenClue
from twodown.staging import STUDIO_DROP_HELP, short_download_name, studio_description
from twodown.config import SITE_ROOT
from twodown.site import (
    _ensure_download_shorts_chrome,
    _ensure_profile,
    _playable_daily,
    _solved_shelf,
    attach_play_anchor,
    attach_video_posters,
    attach_youtube_upload,
    earlier_days,
    legacy_videos,
    publish_extra_items,
    publish_films,
    publish_site,
    retarget_cdn,
    retarget_play_links,
    solved_films,
)
from twodown.youtube import (
    YOUTUBE_CHANNEL,
    YOUTUBE_CHANNEL_URL,
    YOUTUBE_STUDIO,
    short_mp4_url,
    thumbnail_file,
    upload_short,
    video_title,
    video_title_from_line,
)


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


def test_old_pages_gain_download_shorts_chrome():
    old = (
        "<header>\n"
        '      <nav>\n        <a href="../../index.html">Today</a>\n'
        '        <a href="../../films.html">Films</a>\n'
        '        <a href="../../follow.html">Follow</a>\n      </nav>\n'
        '<div class="follow" role="group" aria-label="Follow cryptic.fit">'
        '<a href="https://www.youtube.com/@crypticfit" data-follow-link '
        'rel="me noopener" target="_blank">YouTube</a></div>\n'
        "</header>\n<main></main>"
    )
    once = _ensure_download_shorts_chrome(old)
    header = once.split("</header>", 1)[0]
    assert header.count('href="../../upload.html">Download Shorts</a>') == 2
    follow = header.split('class="follow"', 1)[1]
    assert follow.find("YouTube") < follow.find("Download Shorts")
    assert _ensure_download_shorts_chrome(once) == once


def test_homepage_html_has_download_shorts_link():
    homepage = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
    header = homepage.split("</header>", 1)[0]
    assert 'href="upload.html">Download Shorts</a>' in header
    follow = header.split('class="follow"', 1)[1]
    assert follow.find("YouTube") < follow.find("Download Shorts")
    assert "Download Shorts for YouTube is on the" in homepage
    assert 'href="upload.html">upload page</a>' in homepage


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
    assert "Andrew" in index
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
    assert "https://cryptic.fit/upload.html" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert (tmp_path / "upload.html").exists()
    assert 'href="films.html">Films</a>' in index
    header = index.split("</header>", 1)[0]
    assert 'href="upload.html">Download Shorts</a>' in header
    follow = header.split('class="follow"', 1)[1]
    assert follow.find("YouTube") < follow.find("Download Shorts")
    assert "Download Shorts for YouTube is on the" in index
    assert 'href="upload.html">upload page</a>' in index
    films_page = (tmp_path / "films.html").read_text(encoding="utf-8")
    assert "Download Short" in films_page
    assert 'href="media/independent-12458-12a.mp4"' in films_page
    assert 'download="crypticfit-independent-12458-12a.mp4"' in films_page
    assert STUDIO_DROP_HELP in films_page
    assert "Download Short" in index
    assert 'href="media/independent-12458-12a.mp4"' in index
    assert 'download="crypticfit-independent-12458-12a.mp4"' in index
    assert STUDIO_DROP_HELP in index
    assert "https://www.youtube.com/upload" in index
    assert "@crypticfun" not in index
    pair_html = index.split("Today’s pair.", 1)[1].split("Keep the pair coming", 1)[0]
    assert pair_html.find("Solve") < pair_html.find("Download Short")
    first_before_spoiler = pair_html.split('class="spoiler"', 1)[0]
    assert "END RESULT" not in first_before_spoiler
    assert "Download Short" not in first_before_spoiler
    upload_page = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert "Download Short" in upload_page
    assert "Open YouTube Studio" in upload_page
    assert STUDIO_DROP_HELP in upload_page
    assert "cannot drag from this page" in upload_page
    assert "Copy title" in upload_page
    assert "Solve it, I know you can." in upload_page
    assert "Answer: END RESULT" not in upload_page
    assert "Fifteen Squared" not in upload_page
    assert "adsbygoogle" not in upload_page
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
    assert "Download Short" in clue_page
    assert 'href="../../media/independent-12458-12a.mp4"' in clue_page
    assert 'download="crypticfit-independent-12458-12a.mp4"' in clue_page
    assert "https://www.youtube.com/upload" in clue_page
    assert STUDIO_DROP_HELP in clue_page
    assert "Copy title" in clue_page
    assert "cryptic.fit · Rioting led unrest" in clue_page
    assert (tmp_path / "robots.txt").exists()
    css = (tmp_path / "assets" / "style.css").read_text(encoding="utf-8")
    assert "body.scene-photo header a" in css
    assert ".spoiler .answer, .spoiler .parse { display: none; }" in css
    assert "article.clue.is-solved .answer" in css
    app = (tmp_path / "assets" / "app.js").read_text(encoding="utf-8")
    assert "is-solved" in app
    assert "playFromHash" in app
    assert "wantsPlay" in app
    assert "sidecarTried" in app
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


def test_publish_extra_items_leaves_todays_pair(tmp_path):
    pair = DailyPair(date="2026-10-01", voice="en-GB-SoniaNeural", clues=[_item(), _item(answer="AXES", number="14")])
    root = publish_site(pair, tmp_path)
    extra = _item(answer="MARTINI", number="1")
    extra.clue.puzzle_id = "18494"
    extra.clue.paper = "Financial Times"
    extra.clue.clue = "Cocktail skirt full of style"
    extra.clue.enumeration = "7"
    extra.clue.definition = "Cocktail"
    extra.clue.parse = "MINI full of ART"
    publish_extra_items([extra], "2026-10-01", dest=root)
    homepage = (root / "index.html").read_text(encoding="utf-8")
    pair_html = homepage.split("Today’s pair.", 1)[1].split("Keep the pair coming", 1)[0]
    assert 'data-slug="independent-12458-12a"' in pair_html
    assert 'data-slug="independent-12458-14a"' in pair_html
    assert "financial-times-18494-1a" not in pair_html
    day = (root / "d" / "2026-10-01" / "index.html").read_text(encoding="utf-8")
    assert 'data-slug="financial-times-18494-1a"' in day
    assert (root / "c" / "financial-times-18494-1a" / "index.html").exists()
    assert "https://cryptic.fit/c/financial-times-18494-1a/" in (root / "sitemap.xml").read_text(encoding="utf-8")
    assert extra.clue.answer not in (root / "c" / "financial-times-18494-1a" / "index.html").read_text(encoding="utf-8").split('class="spoiler"', 1)[0]
    earlier = _item(answer="CASSAVA", number="1")
    earlier.clue.paper = "Guardian"
    earlier.clue.puzzle_id = "30125"
    earlier.clue.clue = "Starch silly person dropped into sparkling wine"
    earlier.clue.enumeration = "7"
    earlier.clue.definition = "Starch"
    earlier.clue.parse = "ASS in CAVA"
    publish_extra_items([earlier], "2026-09-30", dest=root)
    homepage = (root / "index.html").read_text(encoding="utf-8")
    pair_html = homepage.split("Today’s pair.", 1)[1].split("Keep the pair coming", 1)[0]
    assert "financial-times-18494-1a" not in pair_html
    assert "guardian-30125-1a" not in pair_html
    assert "guardian-30125-1a" in homepage
    assert "Starch silly person dropped into sparkling wine" in homepage


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
    assert 'href="c/independent-12462-6a/#play"' in shelf
    assert "independent-12462-6a-poster.webp" in shelf
    played = _playable_daily(tmp_path)
    assert "PIN-UP" not in played
    assert 'src="media/independent-12462-6a.mp4"' in played
    assert 'poster="media/independent-12462-6a-poster.webp"' in played
    assert 'href="c/independent-12462-6a/#play"' in played
    assert 'id="independent-12462-6a"' in played
    assert 'data-slug="independent-12462-6a"' in played
    assert 'href="media/independent-12462-6a.mp4"' in played
    assert 'download="crypticfit-independent-12462-6a.mp4"' in played
    assert "Download Short" in played
    assert "Open YouTube Studio" in played
    assert STUDIO_DROP_HELP in played
    assert "youtube.com/@crypticfit" in played
    publish_films(tmp_path)
    films_html = (tmp_path / "films.html").read_text(encoding="utf-8")
    assert 'href="media/independent-12462-6a.mp4"' in films_html
    assert "Download Short" in films_html
    assert STUDIO_DROP_HELP in films_html
    assert "PIN-UP" not in films_html
    kit = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert "Download Short" in kit
    assert "Open YouTube Studio" in kit
    assert STUDIO_DROP_HELP in kit
    assert "cannot drag from this page" in kit
    assert ".youtube-upload" in (tmp_path / "assets" / "style.css").read_text(encoding="utf-8")
    day_html = (day / "index.html").read_text(encoding="utf-8")
    assert "Download Short" in day_html
    assert 'href="../../media/independent-12462-6a.mp4"' in day_html
    assert STUDIO_DROP_HELP in day_html


def test_thumbnail_links_skip_the_solve_gate():
    shelf = (
        '<a class="film-card" href="c/independent-12462-6a/">'
        '<img src="media/independent-12462-6a-poster.webp" alt="">'
        "</a>"
    )
    linked = retarget_play_links(shelf)
    assert 'href="c/independent-12462-6a/#play"' in linked
    assert retarget_play_links(linked) == linked
    assert 'href="c/guardian-30113-9a/#play"' in retarget_play_links(
        '<p class="credit"><a href="c/guardian-30113-9a/">Open this clue</a></p>'
    )
    anchored = attach_play_anchor(
        '<video class="short" controls playsinline src="../../media/independent-12462-6a.mp4">'
    )
    assert 'id="play"' in anchored
    assert attach_play_anchor(anchored) == anchored


def test_publish_site_opens_a_clue_page_at_the_player(tmp_path):
    item = _item()
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"film")
    poster = tmp_path / "clip.webp"
    poster.write_bytes(b"RIFF")
    item.video_path = str(video)
    item.thumbnail_path = str(poster)
    other = _item(answer="AXES", number="14")
    pair = DailyPair(date="2026-09-11", voice="en-GB-SoniaNeural", clues=[item, other])
    root = publish_site(pair, tmp_path / "site")
    clue_page = (root / "c" / "independent-12458-12a" / "index.html").read_text(encoding="utf-8")
    assert 'id="play"' in clue_page
    assert ">Solve<" in clue_page
    assert "is-open" not in clue_page
    assert "Download Short" in clue_page
    assert 'href="../../media/independent-12458-12a.mp4"' in clue_page
    assert 'download="crypticfit-independent-12458-12a.mp4"' in clue_page
    assert STUDIO_DROP_HELP in clue_page
    index = (root / "index.html").read_text(encoding="utf-8")
    pair_html = index.split("Today’s pair.", 1)[1].split("Keep the pair coming", 1)[0]
    assert ">Solve<" in pair_html
    assert "is-open" not in pair_html
    assert 'id="play"' not in pair_html


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
    app = (tmp_path / "assets" / "app.js").read_text(encoding="utf-8")
    assert "playFromHash" in app
    assert "Study cuts" not in films
    assert "rasta-libby" not in films
    assert "jsdelivr" not in films
    assert 'href="d/2026-09-11/#play"' in films
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
    assert "END RESULT" not in title
    assert YOUTUBE_CHANNEL == "cryptic.fit"
    assert YOUTUBE_CHANNEL_URL == "https://www.youtube.com/@crypticfit"
    assert YOUTUBE_STUDIO == "https://www.youtube.com/upload"
    assert short_mp4_url("guardian-30124-9a") == "https://cryptic.fit/media/guardian-30124-9a.mp4"
    assert video_title_from_line("Bring out client I fancy with no end of distinction (6)").startswith("cryptic.fit · ")
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

def test_attach_youtube_upload_is_idempotent_and_lands_on_the_mp4():
    page = """
    <h1>Bring out client I fancy with no end of distinction (6)</h1>
    <article class="clue" data-slug="guardian-30124-9a">
      <p class="clue-text">Bring out client I fancy with no end of distinction (6)</p>
      <button class="reveal" type="button">Solve</button>
      <div class="spoiler" data-nosnippet>
        <video class="short" src="../../media/guardian-30124-9a.mp4"></video>
        <p class="answer">ELICIT</p>
      </div>
    </article>
    """
    once = attach_youtube_upload(page, kit_prefix="../../")
    assert once.count("data-youtube-upload") == 1
    assert 'href="../../media/guardian-30124-9a.mp4"' in once
    assert 'download="crypticfit-guardian-30124-9a.mp4"' in once
    assert STUDIO_DROP_HELP in once
    assert "Copy title" in once
    assert "https://www.youtube.com/upload" in once
    assert "upload.html#guardian-30124-9a" in once
    assert once.find("Solve") < once.find("Download Short")
    spoiler = once.split('class="spoiler"', 1)[1].split("</article>", 1)[0]
    assert "Download Short" in spoiler
    assert attach_youtube_upload(once, kit_prefix="../../") == once
    films = """
    <article class="clue" data-slug="guardian-30124-9a" id="guardian-30124-9a">
      <p class="clue-text">Bring out client I fancy with no end of distinction (6)</p>
      <video class="short" src="media/guardian-30124-9a.mp4"></video>
    </article>
    """
    filmed = attach_youtube_upload(films)
    assert 'href="media/guardian-30124-9a.mp4"' in filmed
    assert "Download Short" in filmed
    assert "Open YouTube Studio" in filmed
    assert STUDIO_DROP_HELP in filmed
    assert "ELICIT" not in filmed
    assert short_download_name("guardian-30124-9a") == "crypticfit-guardian-30124-9a.mp4"
    assert "Solve it, I know you can." in studio_description()
    assert "Answer" not in studio_description()

