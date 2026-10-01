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
    CLUE_LETTERS_GAP_SECONDS,
    CLUE_PITCH,
    CLUE_RATE,
    CLUE_VOLUME,
    DEFAULT_VOICE_ALIAS,
    HINT_HOLD_SECONDS,
    HINT_PAUSE_SECONDS,
    HINT_PITCH,
    HINT_RATE,
    HINT_VOICE_ALIAS,
    HINT_VOLUME,
    INTRO_GAP_SECONDS,
    LETTERS_PAUSE_SECONDS,
    LETTERS_PITCH,
    LETTERS_RATE,
    OUTRO_GAP_SECONDS,
    OUTRO_PITCH,
    OUTRO_RATE,
    OUTRO_VOICE_ALIAS,
    OUTRO_VOLUME,
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
from twodown.render import AUDIO_LOUDNESS, ShortTimings, audio_seconds, intro_bumper_path
from twodown.script import ScriptParts

_SSML_MARKUP = re.compile(r"<\s*speak\b|2001/10/synthesis", re.I)


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
    # Plain speech only. A full <speak> document is escaped by edge-tts and
    # the voice reads "speak version" plus the xmlns out loud.
    if _SSML_MARKUP.search(script or ""):
        raise ValueError("plain speech only; SSML is read aloud as markup")
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
    """Speak the beats as plain lines. Never send SSML to the voice."""
    del pause_seconds
    build_short_soundtrack(parts, dest, voice)
    return dest


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


def extract_intro_bumper_audio(dest: Path) -> Path:
    """Copy the recorded invite. Never send the bumper wording through TTS/SSML."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = intro_bumper_path()
    if not src.exists():
        raise FileNotFoundError(f"missing intro bumper {src}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to extract the intro bumper")
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-c:a",
            "mp3",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    del result
    if audio_seconds(dest) <= 0:
        raise RuntimeError(f"intro bumper has no audio: {src}")
    return dest


def build_short_soundtrack(parts: ScriptParts, dest: Path, voice: str | None = None) -> ShortTimings:
    """Speak each beat, then stitch the pauses so the picture can follow the voice."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/twodown-beats") / dest.parent.name / dest.stem
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    clips = {
        "intro": extract_intro_bumper_audio(work / "intro.mp3"),
        "clue": synthesise(
            parts.clue_speech,
            work / "clue.mp3",
            DEFAULT_VOICE_ALIAS,
            rate=CLUE_RATE,
            pitch=CLUE_PITCH,
            volume=CLUE_VOLUME,
        ),
        "letters": synthesise(
            parts.letters_speech, work / "letters.mp3", voice, rate=LETTERS_RATE, pitch=LETTERS_PITCH
        ),
        "think": synthesise(
            parts.think_speech, work / "think.mp3", voice, rate=THINK_RATE, pitch=THINK_PITCH
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
        "outro": synthesise(
            parts.outro_speech,
            work / "outro.mp3",
            OUTRO_VOICE_ALIAS,
            rate=OUTRO_RATE,
            pitch=OUTRO_PITCH,
            volume=OUTRO_VOLUME,
        ),
    }
    include_hint = bool((parts.hint_speech or "").strip())
    if include_hint:
        clips["hint"] = synthesise(
            parts.hint_speech,
            work / "hint.mp3",
            HINT_VOICE_ALIAS,
            rate=HINT_RATE,
            pitch=HINT_PITCH,
            volume=HINT_VOLUME,
        )
    credit_end = bool((parts.source_speech or "").strip())
    if credit_end:
        clips["source"] = synthesise(
            parts.source_speech,
            work / "source.mp3",
            SOURCE_VOICE_ALIAS,
            rate=SOURCE_RATE,
            pitch=SOURCE_PITCH,
            volume=SOURCE_VOLUME,
        )
    intro_d = audio_seconds(clips["intro"])
    clue_d = audio_seconds(clips["clue"])
    letters_d = audio_seconds(clips["letters"])
    think_d = audio_seconds(clips["think"])
    hint_d = audio_seconds(clips["hint"]) if include_hint else 0.0
    answer_d = audio_seconds(clips["answer"])
    parse_d = audio_seconds(clips["parse"])
    source_d = audio_seconds(clips["source"]) if credit_end else 0.0
    outro_d = audio_seconds(clips["outro"])
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to build the Short soundtrack")
    keys = ["intro", "clue", "letters", "think"]
    if include_hint:
        keys.append("hint")
    keys.extend(["answer", "parse"])
    if credit_end:
        keys.append("source")
    keys.append("outro")
    cmd = [ffmpeg, "-y"]
    for key in keys:
        cmd.extend(["-i", str(clips[key])])
    formats = "".join(
        f"[{i}:a]aformat=sample_rates=24000:channel_layouts=mono[c{i}];" for i in range(len(keys))
    )
    gaps = (
        f"anullsrc=r=24000:cl=mono:d={INTRO_GAP_SECONDS:.2f}[g0];"
        f"anullsrc=r=24000:cl=mono:d={CLUE_LETTERS_GAP_SECONDS:.2f}[g];"
        f"anullsrc=r=24000:cl=mono:d={LETTERS_PAUSE_SECONDS:.2f}[p1];"
        f"anullsrc=r=24000:cl=mono:d={THINK_PAUSE_SECONDS:.2f}[p2];"
    )
    if include_hint:
        gaps += (
            f"anullsrc=r=24000:cl=mono:d={HINT_HOLD_SECONDS:.2f}[h1];"
            f"anullsrc=r=24000:cl=mono:d={HINT_PAUSE_SECONDS:.2f}[h2];"
        )
    gaps += f"anullsrc=r=24000:cl=mono:d={ANSWER_PAUSE_SECONDS:.2f}[p3];"
    if credit_end:
        gaps += f"anullsrc=r=24000:cl=mono:d={SOURCE_GAP_SECONDS:.2f}[g2];"
    gaps += f"anullsrc=r=24000:cl=mono:d={OUTRO_GAP_SECONDS:.2f}[g1];"
    idx = 0
    chain = f"[c{idx}][g0]"
    idx += 1
    chain += f"[c{idx}][g]"
    idx += 1
    chain += f"[c{idx}][p1]"
    idx += 1
    chain += f"[c{idx}][p2]"
    idx += 1
    if include_hint:
        chain += f"[c{idx}][h1][h2]"
        idx += 1
    chain += f"[c{idx}][p3]"
    idx += 1
    chain += f"[c{idx}]"
    idx += 1
    if credit_end:
        chain += f"[g2][c{idx}]"
        idx += 1
        parse_hold = SOURCE_GAP_SECONDS
        source_hold = source_d + OUTRO_GAP_SECONDS
    else:
        parse_hold = OUTRO_GAP_SECONDS
        source_hold = 0.0
    chain += f"[g1][c{idx}]"
    n = chain.count("[")
    cmd.extend(
        [
            "-filter_complex",
            (
                f"{formats}{gaps}{chain}concat=n={n}:v=0:a=1[raw];"
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
        hint=(hint_d + HINT_HOLD_SECONDS + HINT_PAUSE_SECONDS) if include_hint else 0.0,
        answer=answer_d + ANSWER_PAUSE_SECONDS,
        parse=parse_d + parse_hold,
        source=source_hold,
        outro=outro_d + 0.4,
    )
