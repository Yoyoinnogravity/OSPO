from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from twodown.config import DEFAULT_VOICE_ALIAS, VOICE_RATE, VOICES
from twodown.script import ScriptParts, to_ssml


def resolve_voice(name: str | None) -> str:
    if not name:
        return VOICES[DEFAULT_VOICE_ALIAS]
    key = name.strip().lower()
    if key in VOICES:
        return VOICES[key]
    return name


def list_voices() -> dict[str, str]:
    return dict(VOICES)


async def _synth(script: str, dest: Path, voice: str, rate: str = VOICE_RATE) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(script, voice=voice, rate=rate)
    await communicate.save(str(dest))


def synthesise(script: str, dest: Path, voice: str | None = None) -> Path:
    resolved = resolve_voice(voice)
    asyncio.run(_synth(script, dest, resolved))
    return dest


def synthesise_parts(
    parts: ScriptParts,
    dest: Path,
    voice: str | None = None,
    pause_seconds: float | None = None,
) -> Path:
    ssml = to_ssml(parts, pause_seconds) if pause_seconds is not None else to_ssml(parts)
    return synthesise(ssml, dest, voice)
