from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Chat (and some browsers) drop AAC in mp4. Site media is MP3-in-mp4.
SITE_AUDIO_CODEC = "libmp3lame"
SITE_AUDIO_BITRATE = "192k"
SITE_AUDIO_RATE = 44100
SITE_AUDIO_CHANNELS = 2
SITE_AUDIO_ENCODE = (
    "-c:a",
    SITE_AUDIO_CODEC,
    "-b:a",
    SITE_AUDIO_BITRATE,
    "-ar",
    str(SITE_AUDIO_RATE),
    "-ac",
    str(SITE_AUDIO_CHANNELS),
)
SITE_MOVFLAGS = ("-movflags", "+faststart")
MEAN_VOLUME_MIN_DB = -50.0
DURATION_SLACK_SECONDS = 0.75
_MEAN_VOLUME = re.compile(r"mean_volume:\s+(-inf|-?\d+(?:\.\d+)?)\s+dB")
_MAX_VOLUME = re.compile(r"max_volume:\s+(-inf|-?\d+(?:\.\d+)?)\s+dB")


class AudioCheckError(RuntimeError):
    """A Short failed the default audio check. Do not copy it to the site."""


@dataclass(frozen=True)
class AudioReport:
    path: Path
    codec: str
    sample_rate: int
    channels: int
    audio_seconds: float
    video_seconds: float | None
    mean_volume_db: float
    max_volume_db: float


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg is required to check Short audio")
    return path


def _ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError("ffprobe is required to check Short audio")
    return path


def _run(cmd: list[str], what: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip().splitlines()
        tail = " ".join(err[-6:]) if err else "unknown ffmpeg error"
        raise AudioCheckError(f"{what}: {tail}")
    return result


def probe_media(path: Path) -> dict:
    result = subprocess.run(
        [
            _ffprobe(),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise AudioCheckError(f"ffprobe failed on {path}: {err or 'not media'}")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AudioCheckError(f"ffprobe returned no JSON for {path}") from exc


def looks_like_media(path: Path) -> bool:
    try:
        data = probe_media(path)
    except (AudioCheckError, OSError, RuntimeError):
        return False
    return bool(data.get("streams"))


def _seconds(payload: dict | None) -> float | None:
    if not payload:
        return None
    raw = payload.get("duration")
    if raw in (None, "", "N/A"):
        tags = payload.get("tags") or {}
        raw = tags.get("DURATION") or tags.get("duration")
    if raw in (None, "", "N/A"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _db(value: str) -> float:
    if value == "-inf":
        return float("-inf")
    return float(value)


def measure_volume(path: Path) -> tuple[float, float]:
    result = _run(
        [_ffmpeg(), "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        f"volumedetect failed on {path}",
    )
    text = result.stderr or ""
    mean_match = _MEAN_VOLUME.search(text)
    max_match = _MAX_VOLUME.search(text)
    if not mean_match or not max_match:
        raise AudioCheckError(f"volumedetect did not report levels for {path}")
    return _db(mean_match.group(1)), _db(max_match.group(1))


def verify_short_audio(path: Path) -> AudioReport:
    """Fail if the file is mute, silent, or not a chat-safe MP3 soundtrack."""
    path = Path(path)
    if not path.exists():
        raise AudioCheckError(f"missing file {path}; refuse to publish a mute Short")
    data = probe_media(path)
    streams = data.get("streams") or []
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if audio is None:
        raise AudioCheckError(f"no audio stream in {path}; refuse to publish a mute Short")
    codec = str(audio.get("codec_name") or "")
    if codec != "mp3":
        raise AudioCheckError(
            f"audio codec is {codec or 'unknown'}, need mp3 (libmp3lame) for chat-safe files: {path}"
        )
    try:
        sample_rate = int(audio.get("sample_rate") or 0)
    except (TypeError, ValueError):
        sample_rate = 0
    if sample_rate != SITE_AUDIO_RATE:
        raise AudioCheckError(f"audio is {sample_rate} Hz, need {SITE_AUDIO_RATE}: {path}")
    try:
        channels = int(audio.get("channels") or 0)
    except (TypeError, ValueError):
        channels = 0
    if channels != SITE_AUDIO_CHANNELS:
        raise AudioCheckError(f"audio has {channels} channel(s), need stereo: {path}")
    audio_seconds = _seconds(audio) or _seconds(data.get("format")) or 0.0
    video_seconds = _seconds(video)
    if video is not None:
        if video_seconds is None:
            video_seconds = _seconds(data.get("format"))
        if not audio_seconds or audio_seconds <= 0:
            raise AudioCheckError(f"audio duration is missing in {path}; refuse to publish a mute Short")
        if video_seconds and abs(audio_seconds - video_seconds) > DURATION_SLACK_SECONDS:
            raise AudioCheckError(
                f"audio is {audio_seconds:.2f}s but video is {video_seconds:.2f}s; "
                f"mute picture padded with nothing: {path}"
            )
    mean_db, max_db = measure_volume(path)
    if max_db == float("-inf") or mean_db <= MEAN_VOLUME_MIN_DB:
        raise AudioCheckError(
            f"audio is silent (mean {mean_db} dB, max {max_db} dB); refuse to publish a mute Short: {path}"
        )
    return AudioReport(
        path=path,
        codec=codec,
        sample_rate=sample_rate,
        channels=channels,
        audio_seconds=audio_seconds,
        video_seconds=video_seconds,
        mean_volume_db=mean_db,
        max_volume_db=max_db,
    )


def remux_site_media(src: Path, dest: Path) -> Path:
    """Encode chat-safe MP3 audio into the mp4. Picture is copied, never recut."""
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = probe_media(src)
    if not any(stream.get("codec_type") == "audio" for stream in data.get("streams") or []):
        raise AudioCheckError(f"no audio stream in {src}; refuse to publish a mute Short")
    tmp = dest.with_name(f".{dest.stem}.audio-remux.mp4")
    try:
        _run(
            [
                _ffmpeg(),
                "-y",
                "-i",
                str(src),
                "-c:v",
                "copy",
                *SITE_AUDIO_ENCODE,
                *SITE_MOVFLAGS,
                str(tmp),
            ],
            f"site remux failed for {src}",
        )
        verify_short_audio(tmp)
        tmp.replace(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return dest


def write_sidecar_soundtrack(video: Path, dest: Path | None = None) -> Path:
    """Write `{slug}.mp3` next to the mp4 so chat can play sound if the player drops it."""
    video = Path(video)
    dest = Path(dest) if dest is not None else video.with_suffix(".mp3")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [_ffmpeg(), "-y", "-i", str(video), "-vn", *SITE_AUDIO_ENCODE, str(dest)],
        f"could not write sidecar soundtrack for {video}",
    )
    verify_short_audio(dest)
    return dest


def finish_short_audio(video: Path, sidecar: Path | None = None) -> AudioReport:
    """Remux, verify, and write the sidecar. Call after every Short render."""
    video = Path(video)
    remux_site_media(video, video)
    write_sidecar_soundtrack(video, sidecar)
    return verify_short_audio(video)


def publish_short_to_media(src: Path, dest_mp4: Path) -> Path:
    """Copy a Short onto the site only after the audio check passes."""
    src = Path(src)
    dest_mp4 = Path(dest_mp4)
    if not src.exists():
        raise AudioCheckError(f"missing Short {src}; refuse to publish a mute file")
    remux_site_media(src, dest_mp4)
    write_sidecar_soundtrack(dest_mp4, dest_mp4.with_suffix(".mp3"))
    return dest_mp4
