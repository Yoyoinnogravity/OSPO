from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import edge_tts

from twodown.config import (
    ANSWER_PAUSE_SECONDS,
    CLUE_LETTERS_GAP_SECONDS,
    DEFAULT_VOICE_ALIAS,
    HINT_HOLD_SECONDS,
    HINT_PAUSE_SECONDS,
    INTRO_GAP_SECONDS,
    INTRO_PITCH,
    INTRO_RATE,
    INTRO_VOICE_ALIAS,
    LETTERS_PAUSE_SECONDS,
    OUTRO_GAP_SECONDS,
    PARSE_ASIDE_PAUSE_SECONDS,
    PARSE_PITCH,
    PARSE_RATE,
    SOURCE_GAP_SECONDS,
    SOURCE_PITCH,
    SOURCE_RATE,
    SOURCE_VOICE_ALIAS,
    THINK_PAUSE_SECONDS,
    VOICE_PITCH,
    VOICE_RATE,
    VOICES,
)
from twodown.render import AUDIO_LOUDNESS, ShortTimings, audio_seconds
from twodown.script import ScriptParts, parse_to_ssml, to_ssml


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
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(script, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(dest))


def synthesise(
    script: str,
    dest: Path,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
) -> Path:
    resolved = resolve_voice(voice)
    asyncio.run(_synth(script, dest, resolved, rate=rate or VOICE_RATE, pitch=pitch or VOICE_PITCH))
    return dest


def synthesise_parts(
    parts: ScriptParts,
    dest: Path,
    voice: str | None = None,
    pause_seconds: float | None = None,
) -> Path:
    ssml = to_ssml(parts, pause_seconds) if pause_seconds is not None else to_ssml(parts)
    return synthesise(ssml, dest, voice)


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
        ),
        "clue": synthesise(parts.clue_speech, work / "clue.mp3", voice),
        "letters": synthesise(parts.letters_speech, work / "letters.mp3", voice),
        "think": synthesise(parts.think_speech, work / "think.mp3", voice),
        "hint": synthesise(parts.hint_speech, work / "hint.mp3", voice),
        "answer": synthesise(parts.answer_speech, work / "answer.mp3", voice),
        "parse": synthesise(
            parse_to_ssml(parts.parse_speech),
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
        ),
        "outro": synthesise(
            parts.outro_speech,
            work / "outro.mp3",
            INTRO_VOICE_ALIAS,
            rate=INTRO_RATE,
            pitch=INTRO_PITCH,
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
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short soundtrack")
    cmd = [ffmpeg, "-y"]
    for key in ("intro", "clue", "letters", "think", "hint", "answer", "parse", "source", "outro"):
        cmd.extend(["-i", str(clips[key])])
    cmd.extend(
        [
            "-filter_complex",
            (
                "[0:a]aformat=sample_rates=24000:channel_layouts=mono[c0];"
                "[1:a]aformat=sample_rates=24000:channel_layouts=mono[c1];"
                "[2:a]aformat=sample_rates=24000:channel_layouts=mono[c2];"
                "[3:a]aformat=sample_rates=24000:channel_layouts=mono[c3];"
                "[4:a]aformat=sample_rates=24000:channel_layouts=mono[c4];"
                "[5:a]aformat=sample_rates=24000:channel_layouts=mono[c5];"
                "[6:a]aformat=sample_rates=24000:channel_layouts=mono[c6];"
                "[7:a]aformat=sample_rates=24000:channel_layouts=mono[c7];"
                "[8:a]aformat=sample_rates=24000:channel_layouts=mono[c8];"
                f"anullsrc=r=24000:cl=mono:d={INTRO_GAP_SECONDS:.2f}[g0];"
                f"anullsrc=r=24000:cl=mono:d={CLUE_LETTERS_GAP_SECONDS:.2f}[g];"
                f"anullsrc=r=24000:cl=mono:d={LETTERS_PAUSE_SECONDS:.2f}[p1];"
                f"anullsrc=r=24000:cl=mono:d={THINK_PAUSE_SECONDS:.2f}[p2];"
                f"anullsrc=r=24000:cl=mono:d={HINT_HOLD_SECONDS:.2f}[h1];"
                f"anullsrc=r=24000:cl=mono:d={HINT_PAUSE_SECONDS:.2f}[h2];"
                f"anullsrc=r=24000:cl=mono:d={ANSWER_PAUSE_SECONDS:.2f}[p3];"
                f"anullsrc=r=24000:cl=mono:d={SOURCE_GAP_SECONDS:.2f}[g2];"
                f"anullsrc=r=24000:cl=mono:d={OUTRO_GAP_SECONDS:.2f}[g1];"
                "[c0][g0][c1][g][c2][p1][c3][p2][c4][h1][h2][c5][p3][c6][g2][c7][g1][c8]concat=n=18:v=0:a=1[raw];"
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
        intro=intro_d + INTRO_GAP_SECONDS,
        clue=clue_d + CLUE_LETTERS_GAP_SECONDS,
        letters=letters_d + LETTERS_PAUSE_SECONDS,
        think=think_d + THINK_PAUSE_SECONDS,
        hint=hint_d + HINT_HOLD_SECONDS + HINT_PAUSE_SECONDS,
        answer=answer_d + ANSWER_PAUSE_SECONDS,
        parse=parse_d + SOURCE_GAP_SECONDS,
        source=source_d + OUTRO_GAP_SECONDS,
        outro=outro_d + 0.4,
    )
