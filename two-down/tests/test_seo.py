from twodown.models import Clue
from twodown.seo import clue_description, clue_share_title, dumps_ld, video_ld, website_ld


def test_clue_seo_does_not_spoil_the_answer():
    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Independent",
        puzzle_id="12458",
        setter="Phi",
        blogger="duncanshiell",
        number="12",
        direction="across",
        clue="Rioting led unrest in the final analysis",
        enumeration="3,6",
        answer="END RESULT",
        parse="Anagram of LED UNREST",
        device="anagram",
        enumeration_ok=True,
    )
    assert "END RESULT" not in clue_description(clue)
    assert "END RESULT" not in clue_share_title(clue)
    assert "Rioting led unrest" in clue_description(clue)
    assert "Independent" in clue_description(clue)
    assert "Independent cryptic crossword by Phi" in clue_description(clue)
    assert "cryptic.fit" in clue_description(clue)
    video = video_ld(
        clue,
        canonical="https://cryptic.fit/c/independent-12458-12a/",
        published="2026-09-11",
        duration="PT59S",
    )
    assert video["@type"] == "VideoObject"
    assert video["duration"] == "PT59S"
    assert clue.answer not in video["description"]
    assert clue.answer not in video["name"]


def test_json_ld_escapes_script_breakers():
    blob = dumps_ld({"name": "</script><p>x"})
    assert "</script>" not in blob
    assert "\\u003c/script>" in blob
    assert website_ld()["url"] == "https://cryptic.fit/"
    assert website_ld()["name"] == "cryptic.fit"
    assert website_ld()["publisher"]["name"] == "cryptic.fit"
    assert "alternateName" not in website_ld()
    assert "https://www.youtube.com/@crypticfit" in website_ld()["publisher"]["sameAs"]
    assert "unique cryptic crossword clues and solutions" in website_ld()["description"]
    assert "We credit all" in website_ld()["description"]
    assert "Fifteen Squared" in website_ld()["description"]


def test_clue_page_json_ld_includes_video_object(tmp_path):
    from twodown.models import DailyPair, SpokenClue
    from twodown.site import publish_site

    clue = Clue(
        source_url="https://fifteensquared.net/example/",
        paper="Guardian",
        puzzle_id="30108",
        setter="Paul",
        blogger="manehi",
        number="27",
        direction="across",
        clue="Short continental break where plonk guzzled – and most bubbly?",
        enumeration="9",
        answer="SPARKIEST",
        parse="SIESTA cut + PARK inside",
        device="container",
        enumeration_ok=True,
    )
    item = SpokenClue(clue=clue, script="x", voice="en-GB-SoniaNeural")
    root = publish_site(DailyPair(date="2026-09-22", voice="en-GB-SoniaNeural", clues=[item]), tmp_path)
    page = (root / "c" / clue.slug / "index.html").read_text(encoding="utf-8")
    assert "VideoObject" in page
    assert "Guardian cryptic crossword by Paul" in page
    assert f"media/{clue.slug}-thumb.jpg" in page
    assert "SPARKIEST" not in page.split("<body", 1)[0]
