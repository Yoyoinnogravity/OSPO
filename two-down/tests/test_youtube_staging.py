from zipfile import ZipFile

from twodown.site import publish_films
from twodown.staging import (
    INTRO_YOUTUBE_ID,
    NEEDS_UPLOAD_ZIP,
    apply_feed_matches,
    ensure_uploads_json,
    is_uploaded,
    match_feed_to_films,
    parse_channel_feed,
    parse_youtube_id,
    pending_slugs,
    studio_description,
    uploaded_slugs,
    write_needs_upload_zip,
)
from twodown.youtube import video_title, video_title_from_line


def _day(root, date, slug, clue, answer="SECRET"):
    folder = root / "d" / date
    folder.mkdir(parents=True)
    (folder / "index.html").write_text(
        f"""
        <article class="clue" data-slug="{slug}">
          <p class="kicker">Independent 12462 · Eccles · 6 across · hidden</p>
          <p class="clue-text">{clue}</p>
          <p class="answer">{answer}</p>
          <p class="parse">Hidden word</p>
          <p class="credit"><a href="https://example.test/{slug}">Quirister</a></p>
          <video src="../../media/{slug}.mp4" poster="../../media/{slug}-poster.webp"></video>
        </article>
        """,
        encoding="utf-8",
    )
    page = root / "c" / slug
    page.mkdir(parents=True)
    (page / "index.html").write_text(f"<h1>{clue}</h1>", encoding="utf-8")
    media = root / "media"
    media.mkdir(exist_ok=True)
    (media / f"{slug}.mp4").write_bytes(b"film-" + slug.encode())
    (media / f"{slug}-poster.webp").write_bytes(b"RIFF")


def test_parse_youtube_id_reads_shorts_and_watch_urls():
    assert parse_youtube_id("7q-WFyj0WnA") == "7q-WFyj0WnA"
    assert parse_youtube_id("https://www.youtube.com/shorts/7q-WFyj0WnA") == "7q-WFyj0WnA"
    assert parse_youtube_id("https://youtu.be/7q-WFyj0WnA") == "7q-WFyj0WnA"
    assert parse_youtube_id("https://www.youtube.com/watch?v=7q-WFyj0WnA") == "7q-WFyj0WnA"
    assert parse_youtube_id("https://example.test/not-youtube") is None
    assert parse_youtube_id("") is None


def test_slug_without_id_is_needs_upload_slug_with_id_is_on_youtube(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    _day(tmp_path, "2026-10-01", "financial-times-18494-5a", "Colin is buildinga semiconductor (7)", "SILICON")
    ensure_uploads_json(tmp_path)
    data = ensure_uploads_json(tmp_path)
    by_slug = {row["slug"]: row for row in data["videos"]}
    by_slug["independent-12462-6a"]["youtube_id"] = "7q-WFyj0WnA"
    by_slug["independent-12462-6a"]["uploaded_at"] = "2026-09-21"
    from twodown.staging import save_uploads

    save_uploads(tmp_path, data)
    assert "financial-times-18494-5a" in pending_slugs(tmp_path)
    assert "independent-12462-6a" in uploaded_slugs(tmp_path)
    assert is_uploaded(by_slug["independent-12462-6a"])
    assert not is_uploaded(by_slug["financial-times-18494-5a"])


def test_publish_films_writes_two_staging_sections(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    _day(tmp_path, "2026-10-01", "financial-times-18494-5a", "Colin is buildinga semiconductor (7)", "SILICON")
    data = ensure_uploads_json(tmp_path)
    for row in data["videos"]:
        if row["slug"] == "independent-12462-6a":
            row["youtube_id"] = "7q-WFyj0WnA"
            row["uploaded_at"] = "2026-09-21"
    from twodown.staging import save_uploads

    save_uploads(tmp_path, data)
    publish_films(tmp_path)
    page = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert 'id="needs-upload"' in page
    assert 'id="on-youtube"' in page
    assert ">Needs upload<" in page
    assert ">On YouTube<" in page
    needs = page.split('id="needs-upload"', 1)[1].split('id="on-youtube"', 1)[0]
    posted = page.split('id="on-youtube"', 1)[1]
    assert "financial-times-18494-5a" in needs
    assert "independent-12462-6a" not in needs
    assert "independent-12462-6a" in posted
    assert "financial-times-18494-5a" not in posted.split("</section>", 1)[0]
    assert "Download Short" in needs
    assert 'download="crypticfit-financial-times-18494-5a.mp4"' in needs
    assert "Open YouTube Studio" in needs
    assert "https://www.youtube.com/shorts/7q-WFyj0WnA" in posted
    assert "#Shorts" in needs
    assert "PIN-UP" not in page
    assert "SILICON" not in page
    assert "Fifteen Squared" not in page
    assert "adsbygoogle" not in page
    title = "cryptic.fit · Colin is buildinga semiconductor (7) #Shorts"
    assert title in needs
    assert "SILICON" not in title
    assert studio_description() in needs
    assert "Mark as uploaded" in needs
    assert "cryptic-fit-youtube-uploads" in (tmp_path / "assets" / "app.js").read_text(encoding="utf-8")
    assert (tmp_path / "youtube-uploads.json").is_file()


def test_zip_builder_excludes_uploaded(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    _day(tmp_path, "2026-10-01", "financial-times-18494-5a", "Colin is buildinga semiconductor (7)", "SILICON")
    data = ensure_uploads_json(tmp_path)
    for row in data["videos"]:
        if row["slug"] == "independent-12462-6a":
            row["youtube_id"] = "7q-WFyj0WnA"
    from twodown.staging import save_uploads

    save_uploads(tmp_path, data)
    dest = write_needs_upload_zip(tmp_path)
    assert dest is not None
    assert dest.name == NEEDS_UPLOAD_ZIP
    names = ZipFile(dest).namelist()
    assert names == ["crypticfit-financial-times-18494-5a.mp4"]
    assert "crypticfit-independent-12462-6a.mp4" not in names
    publish_films(tmp_path)
    kit = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert f"media/{NEEDS_UPLOAD_ZIP}" in kit


def test_titles_have_shorts_not_answers():
    from twodown.models import Clue

    clue = Clue(
        source_url="https://example.test/",
        paper="Independent",
        puzzle_id="12462",
        setter="Eccles",
        blogger="Quirister",
        number="6",
        direction="across",
        clue="Model youngster eating in",
        enumeration="3-2",
        answer="PIN-UP",
        parse="Hidden",
        device="hidden",
    )
    title = video_title(clue)
    assert title.endswith("#Shorts")
    assert "PIN-UP" not in title
    assert "Fifteen Squared" not in title
    line_title = video_title_from_line("Model youngster eating in (3-2)")
    assert line_title.endswith("#Shorts")
    assert "PIN-UP" not in line_title
    assert "Answer:" not in studio_description()


def test_intro_id_is_not_a_daily_slug_without_a_proven_match():
    films = [("independent-12462-6a", "Model youngster eating in (3-2)")]
    entries = [
        {
            "youtube_id": INTRO_YOUTUBE_ID,
            "title": "Aled’s intro",
            "published": "2026-09-21T16:48:36+00:00",
            "description": "Dictionary ident. Not a daily clue.",
            "link": f"https://www.youtube.com/shorts/{INTRO_YOUTUBE_ID}",
        }
    ]
    assert match_feed_to_films(entries, films) == {}


def test_feed_match_is_unique_or_left_pending():
    films = [
        ("independent-12462-6a", "Model youngster eating in (3-2)"),
        ("guardian-30113-9a", "Will the author flog incomplete bit of fiction? (4)"),
    ]
    unique = [
        {
            "youtube_id": "7q-WFyj0WnA",
            "title": "cryptic.fit · Model youngster eating in (3-2) #Shorts",
            "published": "2026-09-21T20:15:54+00:00",
            "description": "https://cryptic.fit/c/independent-12462-6a/",
            "link": "https://www.youtube.com/shorts/7q-WFyj0WnA",
        }
    ]
    matched = match_feed_to_films(unique, films)
    assert matched["independent-12462-6a"]["youtube_id"] == "7q-WFyj0WnA"
    assert "guardian-30113-9a" not in matched

    ambiguous = [
        {
            "youtube_id": "aaaaaaaaaaa",
            "title": "cryptic.fit #Shorts",
            "published": "2026-09-21T20:15:54+00:00",
            "description": "two clues https://cryptic.fit/c/independent-12462-6a/ and https://cryptic.fit/c/guardian-30113-9a/",
            "link": "https://www.youtube.com/shorts/aaaaaaaaaaa",
        }
    ]
    assert match_feed_to_films(ambiguous, films) == {}


def test_apply_feed_matches_persists_only_safe_hits(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/">
      <entry>
        <yt:videoId>7q-WFyj0WnA</yt:videoId>
        <title>cryptic.fit · Model youngster eating in (3-2) #Shorts</title>
        <published>2026-09-21T20:15:54+00:00</published>
        <media:group>
          <media:description>https://cryptic.fit/c/independent-12462-6a/</media:description>
        </media:group>
      </entry>
    </feed>
    """
    entries = parse_channel_feed(xml)
    applied = apply_feed_matches(
        tmp_path,
        entries,
        [("independent-12462-6a", "Model youngster eating in (3-2)")],
    )
    assert applied["independent-12462-6a"]["youtube_id"] == "7q-WFyj0WnA"
    assert uploaded_slugs(tmp_path) == ["independent-12462-6a"]
