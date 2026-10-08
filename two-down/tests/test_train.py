import json
from datetime import date, timedelta

from twodown.models import Clue
from twodown.train import (
    CLUE_OF_THE_DAY,
    ROTATION,
    load_own_clues,
    mark_own_clue_used,
    pick_clue_of_the_day,
    rotation_slot,
)
from twodown.youtube import video_title


def _day(slot: str) -> date:
    base = date(2026, 1, 1)
    for offset in range(len(ROTATION)):
        day = base + timedelta(days=offset)
        if rotation_slot(day) == slot:
            return day
    raise AssertionError(slot)


def _clue(**kwargs) -> Clue:
    fields = dict(
        source_url="https://fifteensquared.net/2026/10/08/guardian-30130-by-paul/",
        paper="Guardian",
        puzzle_id="30130",
        setter="Paul",
        blogger="blogger",
        number="1",
        direction="across",
        clue="Fair surface hiding the real work inside",
        enumeration="7",
        answer="EXAMPLE",
        parse="A fair surface hiding the real work",
        device="charade",
        enumeration_ok=True,
    )
    fields.update(kwargs)
    return Clue(**fields)


def test_rotation_covers_each_source_once():
    start = date(2026, 10, 8)
    seen = [rotation_slot(start + timedelta(days=i)) for i in range(len(ROTATION))]
    assert seen == list(ROTATION[ROTATION.index(seen[0]) :]) + list(ROTATION[: ROTATION.index(seen[0])])
    assert set(seen) == set(ROTATION)
    assert rotation_slot(start) == rotation_slot(start)


def test_guardian_day_stays_on_the_guardian_clue():
    guardian = _clue()
    financial = _clue(
        paper="Financial Times",
        puzzle_id="18499",
        setter="Neo",
        clue="Mixed media covers the story",
        enumeration="4,5",
        answer="MASS MEDIA",
        parse="Anagram of media covers",
        device="anagram",
        source_url="https://fifteensquared.net/2026/10/08/financial-times-18499-by-neo/",
    )
    pick = pick_clue_of_the_day([financial, guardian], _day("guardian"))
    assert pick is not None
    assert pick.slot == "guardian"
    assert pick.source == "guardian"
    assert pick.clue.paper == "Guardian"
    assert pick.clue.theme is None


def test_times_day_without_a_written_clue_falls_through_to_the_theme(tmp_path):
    path = tmp_path / "own-clues.json"
    path.write_text('{"clues": []}\n', encoding="utf-8")
    blog = [_clue(device="anagram", answer="EXAMPLE")]
    pick = pick_clue_of_the_day(blog, _day("times"), own_path=path)
    assert pick is not None
    assert pick.slot == "times"
    assert pick.source == "clue-of-the-day"
    assert pick.clue.theme == CLUE_OF_THE_DAY
    assert pick.clue.paper == "Guardian"
    title = video_title(pick.clue)
    assert title.startswith("cryptic.fit · Clue of the day · ")
    assert pick.clue.answer not in title


def test_times_day_uses_a_written_times_clue_and_drops_other_hosts(tmp_path):
    path = tmp_path / "own-clues.json"
    path.write_text(
        json.dumps(
            {
                "clues": [
                    {
                        "paper": "Times",
                        "setter": "Aled",
                        "clue": "Writer's point about a short train",
                        "enumeration": "5",
                        "answer": "TRACK",
                        "parse": "A point about a short line",
                        "source_url": "https://timesforthetimes.co.uk/example/",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pick = pick_clue_of_the_day([_clue()], _day("times"), own_path=path)
    assert pick is not None
    assert pick.source == "times"
    assert pick.clue.paper == "Times"
    assert pick.clue.theme is None
    assert pick.clue.source_url == "https://cryptic.fit/suggest.html"
    assert "timesforthetimes" not in pick.clue.source_url
    assert mark_own_clue_used(pick.clue, _day("times").isoformat(), path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["clues"][0]["used_on"] == _day("times").isoformat()
    assert load_own_clues(path, _day("times") + timedelta(days=5)) == []
    again = load_own_clues(path, _day("times"))
    assert len(again) == 1


def test_telegraph_day_reads_only_the_written_file(tmp_path):
    path = tmp_path / "own-clues.json"
    path.write_text(
        json.dumps(
            {
                "clues": [
                    {
                        "paper": "The Daily Telegraph",
                        "clue": "Line that never fetched a blog",
                        "answer": "CABLE",
                        "enumeration": "5",
                        "parse": "A line you already solved",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pick = pick_clue_of_the_day([], _day("telegraph"), own_path=path)
    assert pick is not None
    assert pick.source == "telegraph"
    assert pick.clue.answer == "CABLE"


def test_own_day_prefers_a_homemade_clue_over_a_times_row(tmp_path):
    path = tmp_path / "own-clues.json"
    path.write_text(
        json.dumps(
            {
                "clues": [
                    {
                        "paper": "Times",
                        "clue": "Already solved Times row",
                        "answer": "TRACK",
                        "enumeration": "5",
                        "parse": "Kept for the Times slot",
                    },
                    {
                        "paper": "Aled",
                        "clue": "Homemade row for the own slot",
                        "answer": "LOCAL",
                        "enumeration": "5",
                        "parse": "Written before the train ran",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    pick = pick_clue_of_the_day([], _day("own"), own_path=path)
    assert pick is not None
    assert pick.source == "own"
    assert pick.clue.paper == "Aled"


def test_a_row_without_an_answer_is_ignored(tmp_path):
    path = tmp_path / "own-clues.json"
    path.write_text(
        json.dumps({"clues": [{"paper": "Times", "clue": "No solution written yet", "parse": "Nothing here"}]}),
        encoding="utf-8",
    )
    assert load_own_clues(path, _day("times")) == []
    assert pick_clue_of_the_day([], _day("times"), own_path=path) is None


def test_clue_of_the_day_labels_the_best_blog_clue():
    weak = _clue(device="unknown", enumeration_ok=False, answer="EXAMPLE")
    strong = _clue(
        paper="Financial Times",
        puzzle_id="18499",
        number="2",
        device="anagram",
        clue="Mixed media covers the story",
        enumeration="4,5",
        answer="MASS MEDIA",
        parse="Anagram of media covers",
        enumeration_ok=True,
    )
    pick = pick_clue_of_the_day([weak, strong], _day("clue-of-the-day"))
    assert pick is not None
    assert pick.source == "clue-of-the-day"
    assert pick.clue.answer == "MASS MEDIA"
    assert pick.clue.theme == CLUE_OF_THE_DAY
