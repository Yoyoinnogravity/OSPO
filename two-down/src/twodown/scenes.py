from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from twodown.config import PACKAGE_ROOT

SCENES_DIR = PACKAGE_ROOT / "assets" / "scenes"
NEWSPRINT = "newsprint"
DEFAULT_SCENE = "machu-picchu"


@dataclass(frozen=True)
class Scene:
    slug: str
    label: str
    place: str
    photographer: str
    license: str
    commons_file: str | None = None
    filename: str | None = None

    @property
    def is_photo(self) -> bool:
        return self.filename is not None

    @property
    def path(self) -> Path | None:
        if not self.filename:
            return None
        return SCENES_DIR / self.filename

    @property
    def commons_url(self) -> str | None:
        if not self.commons_file:
            return None
        name = self.commons_file.replace(" ", "_")
        return "https://commons.wikimedia.org/wiki/File:" + quote(name, safe="_,()'-")

    @property
    def credit_line(self) -> str:
        if not self.is_photo:
            return "Newsprint"
        return f"{self.place} · {self.photographer} / Wikimedia Commons ({self.license})"

    @property
    def youtube_credit(self) -> str:
        if not self.is_photo:
            return "Background: newsprint."
        url = self.commons_url or "https://commons.wikimedia.org/"
        return (
            f"Background: {self.place}. Photo: {self.photographer}, {self.license}, Wikimedia Commons. {url}"
        )


_SCENES: tuple[Scene, ...] = (
    Scene(
        slug="machu-picchu",
        label="Machu Picchu",
        place="Machu Picchu, Peru",
        photographer="Pedro Szekely",
        license="CC BY-SA 2.0",
        commons_file="Machu Picchu, Peru.jpg",
        filename="machu-picchu.webp",
    ),
    Scene(
        slug="matterhorn",
        label="Matterhorn",
        place="Matterhorn, Swiss Alps",
        photographer="chil / Zacharie Grossen",
        license="CC BY-SA 3.0",
        commons_file="Matterhorn from Domhütte - 2.jpg",
        filename="matterhorn.webp",
    ),
    Scene(
        slug="santorini",
        label="Santorini",
        place="Oia, Santorini",
        photographer="Danbu14",
        license="CC BY-SA 3.0",
        commons_file="Santorini Oia.jpg",
        filename="santorini.webp",
    ),
    Scene(
        slug="grand-canyon",
        label="Grand Canyon",
        place="Grand Canyon South Rim",
        photographer="Mgimelfarb",
        license="CC0",
        commons_file="Grand Canyon South Rim at Sunset.jpg",
        filename="grand-canyon.webp",
    ),
    Scene(
        slug="kyoto",
        label="Kyoto",
        place="Fushimi Inari, Kyoto",
        photographer="Basile Morin",
        license="CC BY-SA 4.0",
        commons_file="Torii path with lantern at Fushimi Inari Taisha Shrine, Kyoto, Japan.jpg",
        filename="kyoto.webp",
    ),
    Scene(
        slug="aurora",
        label="Aurora",
        place="Lyngen Alps, Norway",
        photographer="Ximonic (Simo Räsänen)",
        license="CC BY-SA 3.0",
        commons_file="Aurora borealis above Storfjorden and the Lyngen Alps in moonlight, 2012 March.jpg",
        filename="aurora.webp",
    ),
    Scene(
        slug="petra",
        label="Petra",
        place="Al Khazneh, Petra",
        photographer="Graham Racher",
        license="CC BY-SA 2.0",
        commons_file="Al Khazneh Petra edit 2.jpg",
        filename="petra.webp",
    ),
    Scene(
        slug="halong",
        label="Ha Long",
        place="Ha Long Bay, Vietnam",
        photographer="Thomas Hirsch",
        license="CC BY-SA 3.0",
        commons_file="Halong Bay in Vietnam.jpg",
        filename="halong.webp",
    ),
    Scene(
        slug=NEWSPRINT,
        label="Newsprint",
        place="Newsprint",
        photographer="",
        license="",
    ),
)

SCENES: dict[str, Scene] = {scene.slug: scene for scene in _SCENES}


def list_scenes() -> list[Scene]:
    return list(_SCENES)


def scenic_slugs() -> list[str]:
    return [scene.slug for scene in _SCENES if scene.is_photo]


def get_scene(slug: str | None) -> Scene:
    key = (slug or DEFAULT_SCENE).strip().lower()
    scene = SCENES.get(key)
    if scene is None:
        known = ", ".join(SCENES)
        raise ValueError(f"Unknown scene {slug!r}. Choose one of: {known}")
    return scene


def pick_scenes(date: str, n: int, scene: str | None = None) -> list[str]:
    """Two Shorts a day get two different real places, unless --scene pins one."""
    if n <= 0:
        return []
    if scene:
        return [get_scene(scene).slug] * n
    pool = scenic_slugs()
    start = int(hashlib.sha256(date.encode("utf-8")).hexdigest(), 16) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(n)]
