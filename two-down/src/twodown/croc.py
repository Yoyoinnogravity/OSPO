"""Cryptic Croc, the crossword presenter.

A clay-shaded crocodile, lit like a small animated film: round forms,
glossy eyes, and a jaw that opens. She talks, blinks, and waves while a
Short is playing. The clue stays in the middle of the picture.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

# Talking beats move her mouth. The think beat is the quiet wait.
_TALKING = {"intro", "clue", "letters", "hint", "answer", "parse", "source", "outro"}
_BIG = {"intro", "outro"}

_BODY = np.array((0.36, 0.58, 0.30), dtype=np.float32)
_DARK = np.array((0.18, 0.36, 0.18), dtype=np.float32)
_SNOUT = np.array((0.48, 0.66, 0.36), dtype=np.float32)
_BELLY = np.array((0.93, 0.86, 0.70), dtype=np.float32)
_MOUTH = np.array((0.55, 0.16, 0.18), dtype=np.float32)
_TOOTH = np.array((0.97, 0.95, 0.88), dtype=np.float32)
_SCARF = np.array((0.74, 0.12, 0.16), dtype=np.float32)
_SCLERA = np.array((0.96, 0.95, 0.90), dtype=np.float32)
_IRIS = np.array((0.45, 0.28, 0.12), dtype=np.float32)
_PUPIL = np.array((0.06, 0.04, 0.03), dtype=np.float32)
_LIGHT = np.array((1.0, 0.98, 0.94), dtype=np.float32)

_KEY = np.array((-0.25, 0.82, 0.52), dtype=np.float32)
_KEY /= np.linalg.norm(_KEY)
_FILL = np.array((0.62, 0.15, 0.42), dtype=np.float32)
_FILL /= np.linalg.norm(_FILL)
_RIM = np.array((0.15, 0.35, -0.9), dtype=np.float32)
_RIM /= np.linalg.norm(_RIM)
_VIEW = np.array((0.0, 0.08, 1.0), dtype=np.float32)
_VIEW /= np.linalg.norm(_VIEW)
_HALF = _KEY + _VIEW
_HALF /= np.linalg.norm(_HALF)


def _mood(beat: str) -> str:
    if beat in {"intro", "outro"}:
        return "wave"
    if beat == "hint":
        return "point"
    if beat == "think":
        return "think"
    if beat == "answer":
        return "cheer"
    return "talk"


def croc_sprite(beat: str, frame: int) -> Image.Image:
    """One pose of Cryptic Croc, transparent around the edges."""
    mood = _mood(beat)
    talking = beat in _TALKING and mood != "think"
    blink = frame % 22 in {11, 12}
    mouth = (frame % 4) if talking else 0
    if mood == "cheer":
        mouth = max(mouth, 2)
    tail = math.sin(frame / 2.2)
    wave = math.sin(frame / 1.6)
    return _render(mood, blink, mouth, tail, wave, view="body")


def croc_portrait() -> Image.Image:
    """Head and snout for the channel picture. Eyes open, mouth closed."""
    return _render("talk", False, 0, 0.0, 0.0, view="head")


def croc_site_sprite() -> Image.Image:
    """The figure on the site: mouth shut, brows down, unimpressed."""
    return _render("think", False, 0, 0.0, 0.0, view="body", scowl=True)


def _render(
    mood: str,
    blink: bool,
    mouth: int,
    tail: float,
    wave: float,
    view: str,
    scowl: bool = False,
) -> Image.Image:
    if view == "head":
        width, height, scale = 760, 760, 250.0
        focus = (1.45, 0.78)
        origin = (width / 2 - focus[0] * scale, height / 2 + focus[1] * scale)
    else:
        width, height, scale = 640, 560, 108.0
        origin = (268.0, 300.0)
    color = np.zeros((height, width, 3), dtype=np.float32)
    alpha = np.zeros((height, width), dtype=np.float32)
    depth = np.full((height, width), -1.0e6, dtype=np.float32)
    open_jaw = mouth / 3.0

    def splat(center, radii, rgb, specular=0.1, shiny=18.0, emissive=False, rotation=None) -> None:
        _splat(
            color,
            depth,
            alpha,
            origin,
            scale,
            center,
            radii,
            rgb,
            specular,
            shiny,
            emissive,
            rotation,
        )

    if view != "head":
        splat((0.05, -1.28, -2.2), (1.45, 0.14, 0.01), np.zeros(3), specular=0.0, shiny=1.0, emissive=True)
        alpha_shadow = alpha.copy()
        alpha *= 0.0
        alpha += np.where(depth > -1.0e5, alpha_shadow * 0.34, 0)
        depth[:] = -1.0e6

        splat((-0.15, -0.05, 0.0), (1.05, 0.78, 0.7), _BODY, specular=0.08, shiny=16)
        splat((0.05, -0.22, 0.42), (0.62, 0.42, 0.22), _BELLY, specular=0.04, shiny=10)
        for step in range(4):
            splat(
                (-0.72 + step * 0.32, 0.62 - step * 0.04, 0.05),
                (0.16, 0.07, 0.1),
                _DARK,
                specular=0.04,
                shiny=8,
            )
        capsule = _capsule_fn(color, depth, alpha, origin, scale)
        _tail(capsule, tail)
        _leg(capsule, splat, -0.55, 0.08)
        _leg(capsule, splat, 0.28, 0.16)
        _arm(capsule, splat, mood, wave, near=True)
        _arm(capsule, splat, "rest", 0.0, near=False)

    _head(splat, open_jaw, blink, neck=view != "head", scowl=scowl)
    rgba = np.dstack((np.clip(color, 0, 1), np.clip(alpha, 0, 1)))
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


def _z_rot(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )


def _head(splat, open_jaw: float, blink: bool, neck: bool, scowl: bool = False) -> None:
    if neck:
        splat((0.78, 0.42, 0.02), (0.34, 0.28, 0.32), _BODY, specular=0.08, shiny=16)
    splat((1.15, 0.78, 0.08), (0.58, 0.5, 0.5), _BODY, specular=0.1, shiny=18)
    # Thick upper jaw. The lower jaw tucks into it when the mouth is shut.
    splat((1.82, 0.62, 0.12), (0.62, 0.24, 0.3), _SNOUT, specular=0.12, shiny=20)
    jaw_drop = open_jaw * 0.34
    splat((1.7, 0.46 - jaw_drop, 0.08), (0.52, 0.18, 0.26), _SNOUT, specular=0.1, shiny=16)
    if open_jaw > 0.05:
        splat(
            (1.78, 0.5 - jaw_drop * 0.35, 0.34),
            (0.36, 0.08 + open_jaw * 0.1, 0.1),
            _MOUTH,
            specular=0.02,
            shiny=4,
        )
        for tooth_x in (1.5, 1.68, 1.86, 2.02):
            splat((tooth_x, 0.5, 0.4), (0.035, 0.055, 0.03), _TOOTH, specular=0.45, shiny=40)
            splat((tooth_x, 0.36 - jaw_drop, 0.36), (0.03, 0.045, 0.025), _TOOTH, specular=0.45, shiny=40)
    else:
        splat((1.86, 0.5, 0.4), (0.38, 0.018, 0.035), _DARK, specular=0.0, shiny=2)
    splat((2.28, 0.74, 0.22), (0.045, 0.03, 0.035), _DARK, specular=0.0, shiny=2)
    splat((2.16, 0.76, 0.32), (0.04, 0.025, 0.03), _DARK, specular=0.0, shiny=2)
    for bump_x in (1.55, 1.82, 2.05):
        splat((bump_x, 0.8, 0.18), (0.07, 0.035, 0.05), _DARK, specular=0.04, shiny=8)

    # Scarf around the crown, with a short knot at the side.
    splat((1.18, 1.16, 0.12), (0.46, 0.055, 0.28), _SCARF, specular=0.35, shiny=36)
    splat((0.78, 1.08, 0.28), (0.1, 0.1, 0.1), _SCARF, specular=0.35, shiny=36)
    splat((0.68, 0.96, 0.26), (0.05, 0.08, 0.045), _SCARF, specular=0.25, shiny=24)

    eyes = (np.array((1.02, 0.98, 0.5)), np.array((1.42, 1.02, 0.54)))
    for eye in eyes:
        splat(eye, (0.145, 0.132, 0.11), _SCLERA, specular=0.5, shiny=64)
        splat(eye + (0.012, 0.0, 0.07), (0.06, 0.06, 0.032), _IRIS, specular=0.28, shiny=24)
        splat(eye + (0.016, -0.004, 0.1), (0.028, 0.028, 0.016), _PUPIL, specular=0.02, shiny=4)
        splat(eye + (-0.032, 0.036, 0.12), (0.02, 0.016, 0.01), _LIGHT, emissive=True)
        if scowl:
            # Brow down toward the snout, lid dropped into a glare.
            splat(
                eye + (0.02, 0.14, 0.05),
                (0.16, 0.028, 0.04),
                _DARK,
                specular=0.04,
                shiny=8,
                rotation=_z_rot(-18),
            )
            splat(eye + (0.0, 0.045, 0.09), (0.15, 0.075, 0.06), _BODY, specular=0.08, shiny=12)
        else:
            # A lid along the top of the eye, leaving most of the eye open.
            splat(eye + (0.0, 0.15, 0.02), (0.17, 0.035, 0.05), _BODY * 0.82, specular=0.05, shiny=8)
        if blink:
            splat(eye + (0.0, 0.0, 0.1), (0.18, 0.15, 0.08), _BODY, specular=0.08, shiny=14)


def _tail(capsule, sway: float) -> None:
    points = []
    for step in range(6):
        along = step / 5
        points.append(
            np.array(
                (
                    -1.0 - along * 1.2,
                    0.08 - along * 0.28 + sway * along * 0.45,
                    -0.06,
                ),
                dtype=np.float32,
            )
        )
    radii = (0.28, 0.22, 0.16, 0.12, 0.08, 0.045)
    for start, end, r0, r1 in zip(points, points[1:], radii, radii[1:]):
        capsule(start, end, r0, r1, _DARK, specular=0.05)


def _leg(capsule, splat, hip_x: float, hip_z: float) -> None:
    hip = np.array((hip_x, -0.5, hip_z), dtype=np.float32)
    foot = np.array((hip_x + 0.05, -1.08, hip_z + 0.1), dtype=np.float32)
    capsule(hip, foot, 0.22, 0.14, _DARK, specular=0.05)
    splat(foot + (0.1, -0.02, 0.08), (0.18, 0.07, 0.11), _BODY, specular=0.08, shiny=14)
    for claw in (-0.05, 0.05, 0.14):
        splat(foot + (0.18, -0.05, 0.16 + claw * 0.2), (0.04, 0.028, 0.028), _TOOTH, specular=0.3, shiny=30)


def _arm(capsule, splat, mood: str, wave: float, near: bool) -> None:
    if near:
        shoulder = np.array((0.2, 0.28, 0.52), dtype=np.float32)
        if mood == "wave":
            elbow = shoulder + np.array((-0.08, 0.52, 0.06), dtype=np.float32)
            hand = elbow + np.array((-0.22 + 0.16 * wave, 0.28 + 0.1 * wave, 0.08), dtype=np.float32)
        elif mood == "point":
            elbow = shoulder + np.array((0.34, 0.2, 0.06), dtype=np.float32)
            hand = elbow + np.array((0.4, 0.26, 0.08), dtype=np.float32)
        else:
            elbow = shoulder + np.array((0.08, -0.36, 0.05), dtype=np.float32)
            hand = elbow + np.array((0.14, -0.26, 0.04), dtype=np.float32)
        capsule(shoulder, elbow, 0.16, 0.12, _BODY, specular=0.07)
        capsule(elbow, hand, 0.12, 0.09, _BODY, specular=0.07)
        splat(hand, (0.11, 0.1, 0.09), _SNOUT, specular=0.1, shiny=16)
        return
    shoulder = np.array((-0.15, 0.18, -0.15), dtype=np.float32)
    hand = shoulder + np.array((0.04, -0.5, -0.02), dtype=np.float32)
    capsule(shoulder, hand, 0.13, 0.09, _DARK, specular=0.04)


def _capsule_fn(color, depth, alpha, origin, scale):
    def capsule(start, end, r0: float, r1: float, rgb, specular: float = 0.07) -> None:
        _capsule(color, depth, alpha, origin, scale, start, end, r0, r1, rgb, specular)

    return capsule


def _capsule(
    color: np.ndarray,
    depth: np.ndarray,
    alpha: np.ndarray,
    origin: tuple[float, float],
    scale: float,
    start,
    end,
    r0: float,
    r1: float,
    rgb: np.ndarray,
    specular: float,
) -> None:
    """A smooth tube. The normal follows the centre line, so the limb does not bead."""
    a = np.asarray(start, dtype=np.float32)
    b = np.asarray(end, dtype=np.float32)
    r0 = max(float(r0), 1e-3)
    r1 = max(float(r1), 1e-3)
    radius = max(r0, r1)
    ox, oy = origin
    height, width = depth.shape
    min_x = float(min(a[0], b[0]) - radius)
    max_x = float(max(a[0], b[0]) + radius)
    min_y = float(min(a[1], b[1]) - radius)
    max_y = float(max(a[1], b[1]) + radius)
    x0 = max(0, int(math.floor(ox + min_x * scale)))
    x1 = min(width, int(math.ceil(ox + max_x * scale)) + 1)
    y0 = max(0, int(math.floor(oy - max_y * scale)))
    y1 = min(height, int(math.ceil(oy - min_y * scale)) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    xs = (np.arange(x0, x1) + 0.5 - ox) / scale
    ys = (oy - (np.arange(y0, y1) + 0.5)) / scale
    xg, yg = np.meshgrid(xs, ys)
    seg = b - a
    span = float(seg[0] * seg[0] + seg[1] * seg[1]) + 1e-8
    along = ((xg - float(a[0])) * float(seg[0]) + (yg - float(a[1])) * float(seg[1])) / span
    along = np.clip(along, 0.0, 1.0)
    cx = float(a[0]) + along * float(seg[0])
    cy = float(a[1]) + along * float(seg[1])
    cz = float(a[2]) + along * float(seg[2])
    tube_r = r0 + along * (r1 - r0)
    disk = (xg - cx) ** 2 + (yg - cy) ** 2
    inside = disk <= tube_r * tube_r
    if not inside.any():
        return
    sz = cz + np.sqrt(np.clip(tube_r * tube_r - disk, 0, None))
    nearer = inside & (sz > depth[y0:y1, x0:x1])
    if not nearer.any():
        return
    nx = xg - cx
    ny = yg - cy
    nz = sz - cz
    length = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    normals = np.stack((nx / length, ny / length, nz / length), axis=-1)
    shaded = _shade(normals, rgb, specular, 16.0)
    edge = np.clip((tube_r - np.sqrt(np.clip(disk, 0, None))) * scale * 0.9, 0, 1)
    slab_depth = depth[y0:y1, x0:x1]
    slab_color = color[y0:y1, x0:x1]
    slab_alpha = alpha[y0:y1, x0:x1]
    slab_depth[nearer] = sz[nearer]
    slab_color[nearer] = shaded[nearer]
    slab_alpha[nearer] = np.maximum(slab_alpha[nearer], edge[nearer])


def _splat(
    color: np.ndarray,
    depth: np.ndarray,
    alpha: np.ndarray,
    origin: tuple[float, float],
    scale: float,
    center,
    radii,
    rgb: np.ndarray,
    specular: float,
    shiny: float,
    emissive: bool,
    rotation: np.ndarray | None = None,
) -> None:
    cx, cy, cz = (float(center[0]), float(center[1]), float(center[2]))
    rx, ry, rz = (max(float(radii[0]), 1e-3), max(float(radii[1]), 1e-3), max(float(radii[2]), 1e-3))
    if rotation is None:
        extent = (rx, ry, rz)
        matrix = None
    else:
        radii2 = np.array((rx * rx, ry * ry, rz * rz), dtype=np.float32)
        extent = tuple(float(v) for v in np.sqrt(np.sum(rotation**2 * radii2, axis=1)))
        inverse = np.array((1.0 / (rx * rx), 1.0 / (ry * ry), 1.0 / (rz * rz)), dtype=np.float32)
        matrix = (rotation * inverse) @ rotation.T
    ox, oy = origin
    height, width = depth.shape
    x0 = max(0, int(math.floor(ox + (cx - extent[0]) * scale)))
    x1 = min(width, int(math.ceil(ox + (cx + extent[0]) * scale)) + 1)
    y0 = max(0, int(math.floor(oy - (cy + extent[1]) * scale)))
    y1 = min(height, int(math.ceil(oy - (cy - extent[1]) * scale)) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    xs = (np.arange(x0, x1) + 0.5 - ox) / scale
    ys = (oy - (np.arange(y0, y1) + 0.5)) / scale
    xg, yg = np.meshgrid(xs, ys)
    if matrix is None:
        disk = ((xg - cx) / rx) ** 2 + ((yg - cy) / ry) ** 2
        inside = disk <= 1.0
        if not inside.any():
            return
        sz = cz + rz * np.sqrt(np.clip(1.0 - disk, 0, None))
        nearer = inside & (sz > depth[y0:y1, x0:x1])
        if not nearer.any():
            return
        nx = (xg - cx) / (rx * rx)
        ny = (yg - cy) / (ry * ry)
        nz = (sz - cz) / (rz * rz)
        edge = np.clip((1.0 - disk) * scale * min(rx, ry) * 0.85, 0, 1)
    else:
        dx = xg - cx
        dy = yg - cy
        quadratic_a = float(matrix[2, 2])
        quadratic_b = 2.0 * (matrix[0, 2] * dx + matrix[1, 2] * dy)
        quadratic_c = (
            matrix[0, 0] * dx * dx
            + matrix[1, 1] * dy * dy
            + 2.0 * matrix[0, 1] * dx * dy
            - 1.0
        )
        disc = quadratic_b * quadratic_b - 4.0 * quadratic_a * quadratic_c
        inside = disc >= 0.0
        if not inside.any():
            return
        root = np.sqrt(np.clip(disc, 0, None))
        sz = cz + (-quadratic_b + root) / (2.0 * quadratic_a)
        nearer = inside & (sz > depth[y0:y1, x0:x1])
        if not nearer.any():
            return
        local_z = sz - cz
        nx = matrix[0, 0] * dx + matrix[0, 1] * dy + matrix[0, 2] * local_z
        ny = matrix[1, 0] * dx + matrix[1, 1] * dy + matrix[1, 2] * local_z
        nz = matrix[2, 0] * dx + matrix[2, 1] * dy + matrix[2, 2] * local_z
        edge = np.clip(root * scale * min(rx, ry) * 0.35, 0, 1)
    length = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    normals = np.stack((nx / length, ny / length, nz / length), axis=-1)
    if emissive:
        shaded = np.empty(normals.shape, dtype=np.float32)
        shaded[...] = rgb
    else:
        shaded = _shade(normals, rgb, specular, shiny)
    slab_depth = depth[y0:y1, x0:x1]
    slab_color = color[y0:y1, x0:x1]
    slab_alpha = alpha[y0:y1, x0:x1]
    slab_depth[nearer] = sz[nearer]
    slab_color[nearer] = shaded[nearer]
    slab_alpha[nearer] = np.maximum(slab_alpha[nearer], edge[nearer])


def _shade(normals: np.ndarray, rgb: np.ndarray, specular: float, shiny: float) -> np.ndarray:
    ndk = np.clip(normals @ _KEY, 0, 1)
    ndf = np.clip(normals @ _FILL, 0, 1)
    ndr = np.clip(normals @ _RIM, 0, 1)
    spec = np.clip(normals @ _HALF, 0, 1) ** shiny
    light = 0.36 + 0.5 * ndk + 0.16 * ndf
    shaded = rgb * light[..., None]
    shaded += rgb * ((0.12 * (1.0 - ndk))[..., None])
    shaded += _LIGHT * (specular * spec)[..., None]
    shaded += np.array((0.72, 0.92, 0.6), dtype=np.float32) * (0.14 * ndr)[..., None]
    return np.clip(shaded, 0, 1)


def paste_croc(img: Image.Image, beat: str, frame: int) -> None:
    """Put Cryptic Croc on the card. She stays clear of the clue and the footer."""
    sprite = croc_sprite(beat, frame)
    bob = int(7 * math.sin(frame / 1.7))
    if beat in _BIG:
        sprite = sprite.resize((640, 560), Image.Resampling.LANCZOS)
        x = (img.width - sprite.width) // 2
        y = 1040 + bob
    else:
        sprite = sprite.resize((390, 341), Image.Resampling.LANCZOS)
        x = 28
        y = img.height - sprite.height - 70 + bob
    img.paste(sprite, (x, y), sprite)
