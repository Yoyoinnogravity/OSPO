from zipfile import ZipFile

from twodown.site import publish_films
from twodown.staging import (
    INTRO_YOUTUBE_ID,
    LEGACY_NEEDS_UPLOAD_ZIP,
    NEEDS_UPLOAD_ZIP_HELP,
    YOUTUBE_CONFIRMATIONS_ID,
    apply_feed_matches,
    ensure_uploads_json,
    is_uploaded,
    match_feed_to_films,
    needs_upload_zip_names,
    parse_channel_feed,
    parse_youtube_id,
    pending_slugs,
    slug_from_title,
    studio_confirmations_html,
    studio_description,
    uploaded_slugs,
    write_needs_upload_zips,
)
from twodown.youtube import video_insert_body, video_title, video_title_from_line


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
    assert 'download="Cryptic-Croc-cryptic.fit-financial-times-18494-5a.mp4"' in needs
    assert "Open YouTube Studio" in needs
    assert "https://www.youtube.com/shorts/7q-WFyj0WnA" in posted
    assert "#Shorts" in needs
    assert "PIN-UP" not in page
    assert "SILICON" not in page
    assert "Fifteen Squared" not in page
    assert "adsbygoogle" not in page
    title = "Cryptic Croc · cryptic.fit · Colin is buildinga semiconductor (7) #Shorts"
    assert title in needs
    assert "SILICON" not in title
    assert studio_description() in needs
    assert f'id="{YOUTUBE_CONFIRMATIONS_ID}"' in page
    assert "YouTube confirmations" in page
    assert "Made for kids" in page
    assert "Altered / synthetic / AI-generated" in page
    assert "Yes — disclose" in page
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
    dests = write_needs_upload_zips(tmp_path)
    assert [path.name for path in dests] == ["crypticfit-needs-upload-1.zip"]
    names = ZipFile(dests[0]).namelist()
    assert names == ["Cryptic-Croc-cryptic.fit-financial-times-18494-5a.mp4"]
    assert "Cryptic-Croc-cryptic.fit-independent-12462-6a.mp4" not in names
    assert dests[0].read_bytes()[:2] == b"PK"
    assert b"git-lfs.github.com" not in dests[0].read_bytes()[:200]
    publish_films(tmp_path)
    kit = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert "media/crypticfit-needs-upload-1.zip" in kit
    assert "Download zip 1" in kit
    assert "Do not drop the zip" in kit
    assert LEGACY_NEEDS_UPLOAD_ZIP not in kit
    assert NEEDS_UPLOAD_ZIP_HELP in kit


def test_zip_builder_splits_under_the_github_blob_limit(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    _day(tmp_path, "2026-10-01", "financial-times-18494-5a", "Colin is buildinga semiconductor (7)", "SILICON")
    _day(tmp_path, "2026-10-02", "guardian-30127-16a", "Standing of data science around university (6)", "STATUS")
    data = ensure_uploads_json(tmp_path)
    for row in data["videos"]:
        if row["slug"] == "independent-12462-6a":
            row["youtube_id"] = "7q-WFyj0WnA"
    from twodown.staging import save_uploads

    save_uploads(tmp_path, data)
    dests = write_needs_upload_zips(tmp_path, max_bytes=40)
    assert [path.name for path in dests] == [
        "crypticfit-needs-upload-1.zip",
        "crypticfit-needs-upload-2.zip",
    ]
    listed = [ZipFile(path).namelist() for path in dests]
    assert listed[0] == ["Cryptic-Croc-cryptic.fit-financial-times-18494-5a.mp4"]
    assert listed[1] == ["Cryptic-Croc-cryptic.fit-guardian-30127-16a.mp4"]
    for path in dests:
        assert path.read_bytes()[:2] == b"PK"
        assert path.stat().st_size < 90 * 1024 * 1024
        assert "PIN-UP" not in path.name
        assert "SILICON" not in path.name
        assert "STATUS" not in path.name
    assert "Cryptic-Croc-cryptic.fit-independent-12462-6a.mp4" not in {name for part in listed for name in part}
    assert "aimlessly-sonia.mp4" not in {name for part in listed for name in part}
    publish_films(tmp_path)
    # Tiny fixture mp4s fit in one part at the default 80MB cap.
    kit = (tmp_path / "upload.html").read_text(encoding="utf-8")
    assert "Download zip 1" in kit
    assert "media/crypticfit-needs-upload-1.zip" in kit
    assert LEGACY_NEEDS_UPLOAD_ZIP not in kit


def test_committed_upload_page_links_every_zip_part():
    from pathlib import Path

    from twodown.staging import pending_video_files, plan_needs_upload_parts

    site = Path(__file__).resolve().parents[1] / "site"
    names = needs_upload_zip_names(site)
    assert len(names) >= 2
    assert names[0] == "crypticfit-needs-upload-1.zip"
    videos = pending_video_files(site)
    stems = {video.stem for video in videos}
    assert "independent-12462-6a" not in stems
    assert "financial-times-18478-1a" not in stems
    assert "financial-times-18477-14a" not in stems
    assert "aimlessly-sonia" not in stems
    assert "rasta-study" not in stems
    for part in plan_needs_upload_parts(videos):
        assert sum(video.stat().st_size for video in part) < 90 * 1024 * 1024
    page = (site / "upload.html").read_text(encoding="utf-8")
    for name in names:
        assert f"media/{name}" in page
        assert f'download="{name}"' in page
    for index, _name in enumerate(names, start=1):
        assert f"Download zip {index}" in page
    assert "Do not drop the zip" in page
    assert 'download="crypticfit-needs-upload.zip"' not in page
    assert "PIN-UP" not in page
    assert "7q-WFyj0WnA" in page
    assert "iP6Zh87lE_8" in page
    assert "9WmM2srrHPU" in page
    needs = page.split('id="needs-upload"', 1)[1].split('id="on-youtube"', 1)[0]
    posted = page.split('id="on-youtube"', 1)[1]
    assert "financial-times-18478-1a" not in needs
    assert "financial-times-18477-14a" not in needs
    assert "https://www.youtube.com/shorts/iP6Zh87lE_8" in posted
    assert "https://www.youtube.com/shorts/9WmM2srrHPU" in posted
    assert "Download Short" in page
    assert f'id="{YOUTUBE_CONFIRMATIONS_ID}"' in page
    assert "YouTube confirmations" in page
    assert "Made for kids" in page
    assert ">No<" in page
    assert "Altered / synthetic / AI-generated" in page
    assert "Yes — disclose" in page
    assert "Education" in page
    assert "Solve it, I know you can." in page
    assert "Fifteen Squared" not in page


def test_studio_confirmations_are_honest_defaults():
    card = studio_confirmations_html()
    assert f'id="{YOUTUBE_CONFIRMATIONS_ID}"' in card
    assert "Made for kids" in card
    assert "Age-restricted" in card
    assert "Paid promotion" in card
    assert "Altered / synthetic / AI-generated" in card
    assert "Yes — disclose" in card
    assert "Language" in card
    assert "English" in card
    assert "Education" in card
    assert "Public" in card
    assert "never the answer" in card
    assert studio_description() in card
    assert "Fifteen Squared" not in card
    assert "<dt>Made for kids</dt><dd>No</dd>" in card
    assert "<dt>Altered / synthetic / AI-generated</dt><dd>Yes — disclose</dd>" in card


def test_pages_workflow_builds_pk_zip_parts_before_deploy():
    from pathlib import Path

    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "cryptic-fun-pages.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "write_needs_upload_zips" in text
    assert "refresh_upload_zip_bar" in text
    assert text.find("write_needs_upload_zips") < text.find("upload-pages-artifact")
    assert 'raw[:2] != b"PK"' in text


def test_site_media_zips_are_not_git_lfs():
    from pathlib import Path

    attrs = (Path(__file__).resolve().parents[1] / "site" / ".gitattributes").read_text(encoding="utf-8")
    assert "*.zip !filter !diff !merge -text" in attrs
    ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "crypticfit-needs-upload" in ignore


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
            "title": "Cryptic Croc · cryptic.fit · Model youngster eating in (3-2) #Shorts",
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


def test_slug_style_title_matches_only_when_it_is_a_published_slug():
    films = [
        ("financial-times-18478-1a", "Engineered space unit, life-supporting primarily (7)"),
        ("financial-times-18477-14a", "X Y and Z advancing initially with the other reversed (4)"),
        ("guardian-30113-9a", "Will the author flog incomplete bit of fiction? (4)"),
    ]
    slugs = {slug for slug, _clue in films}
    assert slug_from_title("crypticfit financial times 18478 1a", slugs) == "financial-times-18478-1a"
    assert slug_from_title("crypticfit financial times 18477 14a", slugs) == "financial-times-18477-14a"
    assert slug_from_title("crypticfit", slugs) is None
    assert slug_from_title("Aled’s intro", slugs) is None
    matched = match_feed_to_films(
        [
            {
                "youtube_id": "iP6Zh87lE_8",
                "title": "crypticfit financial times 18478 1a",
                "published": "2026-10-03T17:01:00+00:00",
                "description": "Cryptic clue",
                "link": "https://www.youtube.com/shorts/iP6Zh87lE_8",
            },
            {
                "youtube_id": "9WmM2srrHPU",
                "title": "crypticfit financial times 18477 14a",
                "published": "2026-10-03T16:56:03+00:00",
                "description": "Cryptic crossword fun",
                "link": "https://www.youtube.com/shorts/9WmM2srrHPU",
            },
            {
                "youtube_id": "Gk1KOS_23M8",
                "title": "crypticfit",
                "published": "2026-10-03T17:10:02+00:00",
                "description": "Cryptic clues",
                "link": "https://www.youtube.com/shorts/Gk1KOS_23M8",
            },
        ],
        films,
    )
    assert matched["financial-times-18478-1a"]["youtube_id"] == "iP6Zh87lE_8"
    assert matched["financial-times-18477-14a"]["youtube_id"] == "9WmM2srrHPU"
    assert "guardian-30113-9a" not in matched
    assert all(row["youtube_id"] != "Gk1KOS_23M8" for row in matched.values())


def test_apply_feed_matches_persists_only_safe_hits(tmp_path):
    _day(tmp_path, "2026-09-16", "independent-12462-6a", "Model youngster eating in (3-2)", "PIN-UP")
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/">
      <entry>
        <yt:videoId>7q-WFyj0WnA</yt:videoId>
        <title>Cryptic Croc · cryptic.fit · Model youngster eating in (3-2) #Shorts</title>
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
