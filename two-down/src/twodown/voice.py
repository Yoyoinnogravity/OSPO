from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts

from twodown.config import (
    ANSWER_PAUSE_SECONDS,
    ANSWER_PITCH,
    ANSWER_RATE,
    BRAND_STING_SECONDS,
    PACKAGE_ROOT,
    CLUE_LETTERS_GAP_SECONDS,
    CLUE_PITCH,
    CLUE_RATE,
    DEFAULT_VOICE_ALIAS,
    HINT_HOLD_SECONDS,
    HINT_PAUSE_SECONDS,
    HINT_PITCH,
    HINT_RATE,
    HINT_VOICE_ALIAS,
    HINT_VOLUME,
    INTRO_GAP_SECONDS,
    INTRO_LOOK_BEFORE_SECONDS,
    INTRO_PITCH,
    INTRO_RATE,
    INTRO_VOICE_ALIAS,
    INTRO_VOLUME,
    LETTERS_PAUSE_SECONDS,
    LETTERS_PITCH,
    LETTERS_RATE,
    OUTRO_GAP_SECONDS,
    PARSE_ASIDE_PAUSE_SECONDS,
    PARSE_PITCH,
    PARSE_RATE,
    SOURCE_GAP_SECONDS,
    SOURCE_PITCH,
    SOURCE_RATE,
    SOURCE_VOICE_ALIAS,
    SOURCE_VOLUME,
    THINK_PAUSE_SECONDS,
    THINK_PITCH,
    THINK_RATE,
    VOICE_PITCH,
    VOICE_RATE,
    VOICE_VOLUME,
    VOICES,
)
from twodown.render import AUDIO_LOUDNESS, ShortTimings, audio_seconds
from twodown.script import ScriptParts, to_ssml

BRAND_STING_ASSET = PACKAGE_ROOT / "assets" / "brand-sting.mp3"
# F major then C major — a small IV–I pair. Same set opens and closes.
_BRAND_STING_IV = (174.61, 220.00, 261.63, 349.23)
_BRAND_STING_I = (130.81, 164.81, 196.00, 261.63)


def _sine_mix(freqs: tuple[float, ...], label: str, duration: float) -> str:
    parts: list[str] = []
    names: list[str] = []
    for i, freq in enumerate(freqs):
        name = f"{label}{i}"
        parts.append(f"sine=frequency={freq}:sample_rate=44100:duration={duration:.2f}[{name}]")
        names.append(f"[{name}]")
    fade_out = max(0.08, duration - 0.16)
    parts.append(
        "".join(names)
        + f"amix=inputs={len(freqs)}:duration=first:dropout_transition=0,"
        + f"afade=t=in:st=0:d=0.05,afade=t=out:st={fade_out:.2f}:d=0.14[{label}]"
    )
    return ";".join(parts)


def bake_brand_sting(dest: Path | None = None) -> Path:
    """One sympathetic two-chord sting. Built once; every film reuses it."""
    dest = Path(dest or BRAND_STING_ASSET)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the brand sting")
    first = _sine_mix(_BRAND_STING_IV, "iv", 0.78)
    second = _sine_mix(_BRAND_STING_I, "i", 0.88)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo:d=0.1",
            "-filter_complex",
            (
                f"{first};{second};"
                "[iv][i]acrossfade=d=0.12:c1=tri:c2=tri,"
                "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                "volume=0.55,alimiter=limit=0.89[a]"
            ),
            "-map",
            "[a]",
            "-c:a",
            "mp3",
            "-b:a",
            "192k",
            "-t",
            f"{BRAND_STING_SECONDS:.2f}",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-800:])
    return dest


def ensure_brand_sting() -> Path:
    """Return the shared sting. Bake it once if the asset is missing."""
    if BRAND_STING_ASSET.exists() and BRAND_STING_ASSET.stat().st_size > 800:
        return BRAND_STING_ASSET
    return bake_brand_sting(BRAND_STING_ASSET)


def resolve_voice(name: str | None) -> str:
    if not name:
        return VOICES[DEFAULT_VOICE_ALIAS]
    key = name.strip().lower()
    if key in VOICES:
        return VOICES[key]
    return name


def list_voices() -> dict[str, str]:
    return dict(VOICES)


async def _synth(
    script: str,
    dest: Path,
    voice: str,
    rate: str = VOICE_RATE,
    pitch: str = "+0Hz",
    volume: str = VOICE_VOLUME,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Plain speech only. Full <speak> documents get escaped by edge-tts and
    # the voice starts reading the markup.
    communicate = edge_tts.Communicate(
        script, voice=voice, rate=rate, pitch=pitch, volume=volume
    )
    await communicate.save(str(dest))


def synthesise(
    script: str,
    dest: Path,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    volume: str | None = None,
) -> Path:
    resolved = resolve_voice(voice)
    asyncio.run(
        _synth(
            script,
            dest,
            resolved,
            rate=rate or VOICE_RATE,
            pitch=pitch or VOICE_PITCH,
            volume=volume or VOICE_VOLUME,
        )
    )
    return dest


def synthesise_parts(
    parts: ScriptParts,
    dest: Path,
    voice: str | None = None,
    pause_seconds: float | None = None,
) -> Path:
    ssml = to_ssml(parts, pause_seconds) if pause_seconds is not None else to_ssml(parts)
    return synthesise(ssml, dest, voice)


def _speech_sentences(text: str) -> list[str]:
    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]
    return pieces or [text]


def synthesise_spoken_paragraph(
    text: str,
    dest: Path,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    pause_seconds: float = PARSE_ASIDE_PAUSE_SECONDS,
) -> Path:
    """Speak each sentence on its own so the parse does not run as one machine line."""
    sentences = _speech_sentences(text)
    if len(sentences) == 1:
        return synthesise(sentences[0], dest, voice, rate=rate, pitch=pitch)
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = dest.parent / f"{dest.stem}-lines"
    work.mkdir(parents=True, exist_ok=True)
    clips = [
        synthesise(sentence, work / f"{i:02d}.mp3", voice, rate=rate, pitch=pitch)
        for i, sentence in enumerate(sentences)
    ]
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short soundtrack")
    cmd = [ffmpeg, "-y"]
    for clip in clips:
        cmd.extend(["-i", str(clip)])
    parts = []
    for i in range(len(clips)):
        parts.append(f"[{i}:a]aformat=sample_rates=24000:channel_layouts=mono[s{i}]")
    concat = "".join(f"[s{i}]" if i == 0 else f"[g{i}][s{i}]" for i in range(len(clips)))
    # n = sentences + gaps between them
    n = len(clips) * 2 - 1
    gaps = "".join(
        f"anullsrc=r=24000:cl=mono:d={pause_seconds:.2f}[g{i}];" for i in range(1, len(clips))
    )
    cmd.extend(
        [
            "-filter_complex",
            f"{';'.join(parts)};{gaps}{concat}concat=n={n}:v=0:a=1[a]",
            "-map",
            "[a]",
            "-c:a",
            "mp3",
            "-b:a",
            "192k",
            str(dest),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


def build_short_soundtrack(parts: ScriptParts, dest: Path, voice: str | None = None) -> ShortTimings:
    """Speak each beat, then stitch the pauses so the picture can follow the voice."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/twodown-beats") / dest.stem
    work.mkdir(parents=True, exist_ok=True)
    clips = {
        "intro": synthesise(
            parts.intro_speech,
            work / "intro.mp3",
            INTRO_VOICE_ALIAS,
            rate=INTRO_RATE,
            pitch=INTRO_PITCH,
            volume=INTRO_VOLUME,
        ),
        "clue": synthesise(
            parts.clue_speech, work / "clue.mp3", voice, rate=CLUE_RATE, pitch=CLUE_PITCH
        ),
        "letters": synthesise(
            parts.letters_speech, work / "letters.mp3", voice, rate=LETTERS_RATE, pitch=LETTERS_PITCH
        ),
        "think": synthesise(
            parts.think_speech, work / "think.mp3", voice, rate=THINK_RATE, pitch=THINK_PITCH
        ),
        "hint": synthesise(
            parts.hint_speech,
            work / "hint.mp3",
            HINT_VOICE_ALIAS,
            rate=HINT_RATE,
            pitch=HINT_PITCH,
            volume=HINT_VOLUME,
        ),
        "answer": synthesise(
            parts.answer_speech, work / "answer.mp3", voice, rate=ANSWER_RATE, pitch=ANSWER_PITCH
        ),
        "parse": synthesise_spoken_paragraph(
            parts.parse_speech,
            work / "parse.mp3",
            voice,
            rate=PARSE_RATE,
            pitch=PARSE_PITCH,
        ),
        "source": synthesise(
            parts.source_speech,
            work / "source.mp3",
            SOURCE_VOICE_ALIAS,
            rate=SOURCE_RATE,
            pitch=SOURCE_PITCH,
            volume=SOURCE_VOLUME,
        ),
        "outro": synthesise(
            parts.outro_speech,
            work / "outro.mp3",
            INTRO_VOICE_ALIAS,
            rate=INTRO_RATE,
            pitch=INTRO_PITCH,
            volume=INTRO_VOLUME,
        ),
    }
    intro_d = audio_seconds(clips["intro"])
    clue_d = audio_seconds(clips["clue"])
    letters_d = audio_seconds(clips["letters"])
    think_d = audio_seconds(clips["think"])
    hint_d = audio_seconds(clips["hint"])
    answer_d = audio_seconds(clips["answer"])
    parse_d = audio_seconds(clips["parse"])
    source_d = audio_seconds(clips["source"])
    outro_d = audio_seconds(clips["outro"])
    sting = ensure_brand_sting()
    sting_d = audio_seconds(sting)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short soundtrack")
    cmd = [ffmpeg, "-y", "-i", str(sting)]
    for key in ("intro", "clue", "letters", "think", "hint", "answer", "parse", "source", "outro"):
        cmd.extend(["-i", str(clips[key])])
    cmd.extend(["-i", str(sting)])
    cmd.extend(
        [
            "-filter_complex",
            (
                "[0:a]aformat=sample_rates=24000:channel_layouts=mono[s0];"
                "[1:a]aformat=sample_rates=24000:channel_layouts=mono[c0];"
                "[2:a]aformat=sample_rates=24000:channel_layouts=mono[c1];"
                "[3:a]aformat=sample_rates=24000:channel_layouts=mono[c2];"
                "[4:a]aformat=sample_rates=24000:channel_layouts=mono[c3];"
                "[5:a]aformat=sample_rates=24000:channel_layouts=mono[c4];"
                "[6:a]aformat=sample_rates=24000:channel_layouts=mono[c5];"
                "[7:a]aformat=sample_rates=24000:channel_layouts=mono[c6];"
                "[8:a]aformat=sample_rates=24000:channel_layouts=mono[c7];"
                "[9:a]aformat=sample_rates=24000:channel_layouts=mono[c8];"
                "[10:a]aformat=sample_rates=24000:channel_layouts=mono[s1];"
                f"anullsrc=r=24000:cl=mono:d={INTRO_LOOK_BEFORE_SECONDS:.2f}[look];"
                f"anullsrc=r=24000:cl=mono:d={INTRO_GAP_SECONDS:.2f}[g0];"
                f"anullsrc=r=24000:cl=mono:d={CLUE_LETTERS_GAP_SECONDS:.2f}[g];"
                f"anullsrc=r=24000:cl=mono:d={LETTERS_PAUSE_SECONDS:.2f}[p1];"
                f"anullsrc=r=24000:cl=mono:d={THINK_PAUSE_SECONDS:.2f}[p2];"
                f"anullsrc=r=24000:cl=mono:d={HINT_HOLD_SECONDS:.2f}[h1];"
                f"anullsrc=r=24000:cl=mono:d={HINT_PAUSE_SECONDS:.2f}[h2];"
                f"anullsrc=r=24000:cl=mono:d={ANSWER_PAUSE_SECONDS:.2f}[p3];"
                f"anullsrc=r=24000:cl=mono:d={SOURCE_GAP_SECONDS:.2f}[g2];"
                f"anullsrc=r=24000:cl=mono:d={OUTRO_GAP_SECONDS:.2f}[g1];"
                "[s0][look][c0][g0][c1][g][c2][p1][c3][p2][c4][h1][h2][c5][p3][c6][g2][c7][g1][c8][s1]"
                "concat=n=21:v=0:a=1[raw];"
                f"[raw]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,{AUDIO_LOUDNESS}[a]"
            ),
            "-map",
            "[a]",
            "-c:a",
            "mp3",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(dest),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)
    return ShortTimings(
        intro=sting_d + INTRO_LOOK_BEFORE_SECONDS + intro_d + INTRO_GAP_SECONDS,
        clue=clue_d + CLUE_LETTERS_GAP_SECONDS,
        letters=letters_d + LETTERS_PAUSE_SECONDS,
        think=think_d + THINK_PAUSE_SECONDS,
        hint=hint_d + HINT_HOLD_SECONDS + HINT_PAUSE_SECONDS,
        answer=answer_d + ANSWER_PAUSE_SECONDS,
        parse=parse_d + SOURCE_GAP_SECONDS,
        source=source_d + OUTRO_GAP_SECONDS,
        outro=outro_d + sting_d + 0.35,
    )
