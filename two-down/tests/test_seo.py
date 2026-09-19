from twodown.models import Clue
from twodown.seo import clue_description, clue_share_title, dumps_ld, website_ld


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


def test_json_ld_escapes_script_breakers():
    blob = dumps_ld({"name": "</script><p>x"})
    assert "</script>" not in blob
    assert "\\u003c/script>" in blob
    assert website_ld()["url"] == "https://cryptic.fit/"
    assert website_ld()["name"] == "cryptic.fun"
    assert website_ld()["publisher"]["name"] == "cryptic.fun"
    assert "alternateName" not in website_ld()
    assert "https://www.youtube.com/@crypticfun" in website_ld()["publisher"]["sameAs"]
    assert "unique cryptic crossword clues and solutions" in website_ld()["description"]
    assert "We credit all" in website_ld()["description"]
    assert "Fifteen Squared" in website_ld()["description"]
