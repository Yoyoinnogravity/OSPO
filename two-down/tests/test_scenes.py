from pathlib import Path

from twodown.models import Clue
from twodown.render import draw_clue_card, draw_reveal_card
from twodown.scenes import DEFAULT_SCENE, get_scene, list_scenes, pick_scenes, scenic_slugs
from twodown.youtube import video_description
from twodown.models import SpokenClue


def _clue() -> Clue:
    return Clue(
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


def test_catalog_has_authentic_photos_and_newsprint():
    slugs = [scene.slug for scene in list_scenes()]
    assert slugs[-1] == "newsprint"
    assert DEFAULT_SCENE == "machu-picchu"
    assert "petra" in slugs
    assert "santorini" in slugs
    for scene in list_scenes():
        if scene.is_photo:
            assert scene.path is not None
            assert scene.path.exists()
            assert scene.commons_url
            assert scene.license


def test_pick_scenes_rotates_two_real_places():
    pair = pick_scenes("2026-09-11", 2)
    assert len(pair) == 2
    assert pair[0] != pair[1]
    assert set(pair) <= set(scenic_slugs())
    assert pick_scenes("2026-09-11", 2) == pair
    assert pick_scenes("2026-09-11", 2, scene="newsprint") == ["newsprint", "newsprint"]


def test_draw_photo_card_is_not_newsprint(tmp_path: Path):
    from PIL import Image

    from twodown.config import NEWS_BG
    from twodown.render import write_share_card

    clue = _clue()
    film = Image.open(draw_clue_card(clue, tmp_path / "film.png", scene="machu-picchu"))
    assert film.getpixel((24, 40)) == NEWS_BG
    reveal = Image.open(draw_reveal_card(clue, tmp_path / "reveal.png", scene="petra"))
    assert reveal.size == (1080, 1920)
    share = Image.open(write_share_card(tmp_path / "og.webp", scene="machu-picchu"))
    assert share.size == (1200, 630)
    assert share.getpixel((20, 80)) != NEWS_BG


def test_hint_photo_is_a_definition_still_not_travel_aurora():
    from twodown.hints import DEFAULT_HINT, FATS, LION, MOONLIT, RASTA, TRANCE, WELLINGTON, ensure_hint_photo

    photo = ensure_hint_photo()
    assert photo.exists()
    assert DEFAULT_HINT.slug == TRANCE.slug
    assert DEFAULT_HINT.source == "generated still"
    assert "DREAMLIKE" not in DEFAULT_HINT.credit_line
    assert "aurora" not in DEFAULT_HINT.slug
    assert MOONLIT.commons_file == "Moonlit Moments (Unsplash).jpg"
    assert MOONLIT.source == "Linda Xu"
    assert ensure_hint_photo(RASTA).exists()
    assert "RASTA" not in RASTA.credit_line
    assert ensure_hint_photo(FATS).exists()
    assert "FATS" not in FATS.credit_line
    assert ensure_hint_photo(WELLINGTON).exists()
    assert "WELLINGTON" not in WELLINGTON.credit_line
    assert LION.commons_file == "Flag of Ethiopia (1897–1974).svg"
    assert "Wikimedia Commons" in LION.credit_line


def test_youtube_description_credits_the_photograph():
    item = SpokenClue(
        clue=_clue(),
        script="x",
        voice="en-GB-SoniaNeural",
        scene="kyoto",
        site_path="https://cryptic.fun/c/independent-12458-11a/",
    )
    text = video_description(item)
    scene = get_scene("kyoto")
    assert scene.photographer in text
    assert scene.license in text
    assert "Wikimedia" in text
