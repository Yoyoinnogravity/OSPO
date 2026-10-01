from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

from twodown.audio import (
    SITE_AUDIO_ENCODE,
    SITE_MOVFLAGS,
    AudioCheckError,
    finish_short_audio,
    publish_short_to_media,
    remux_site_media,
    verify_short_audio,
    write_sidecar_soundtrack,
)
from twodown.pipeline import render_one_short, run_today
from twodown.render import render_video
from twodown.site import JS, _copy_media


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _tone_mp3(path: Path, seconds: float = 1.2) -> Path:
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            f"{seconds:.2f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(path),
        ]
    )
    return path


def _silence_mp3(path: Path, seconds: float = 1.2) -> Path:
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            f"{seconds:.2f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(path),
        ]
    )
    return path


def _colour_clip(dest: Path, seconds: float = 1.2) -> Path:
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s=160x160:r=25:d={seconds:.2f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            str(dest),
        ]
    )
    return dest


def _mux(dest: Path, audio: Path | None, *, audio_codec: str = "libmp3lame", seconds: float = 1.2) -> Path:
    if audio is None:
        return _colour_clip(dest, seconds)
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s=160x160:r=25:d={seconds:.2f}",
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-c:a",
            audio_codec,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    return dest


def test_site_remux_flags_are_the_chat_safe_default():
    assert SITE_AUDIO_ENCODE == ("-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "2")
    assert SITE_MOVFLAGS == ("-movflags", "+faststart")
    remux = inspect.getsource(remux_site_media)
    assert "SITE_AUDIO_ENCODE" in remux
    assert "SITE_MOVFLAGS" in remux
    assert "-c:v" in remux and "copy" in remux


def test_video_without_audio_fails_the_check(tmp_path: Path):
    mute = _mux(tmp_path / "mute.mp4", None)
    with pytest.raises(AudioCheckError, match="no audio stream"):
        verify_short_audio(mute)


def test_silent_soundtrack_fails_the_check(tmp_path: Path):
    silent = _silence_mp3(tmp_path / "silent.mp3")
    with pytest.raises(AudioCheckError, match="silent"):
        verify_short_audio(silent)
    dest = _mux(tmp_path / "site.mp4", silent)
    with pytest.raises(AudioCheckError, match="silent"):
        verify_short_audio(dest)


def test_valid_mp3_soundtrack_passes(tmp_path: Path):
    tone = _tone_mp3(tmp_path / "voice.mp3")
    report = verify_short_audio(tone)
    assert report.codec == "mp3"
    assert report.sample_rate == 44100
    assert report.channels == 2
    assert report.mean_volume_db > -50
    film = _mux(tmp_path / "short.mp4", tone)
    remuxed = remux_site_media(film, tmp_path / "site.mp4")
    checked = verify_short_audio(remuxed)
    assert checked.codec == "mp3"
    sidecar = write_sidecar_soundtrack(remuxed)
    assert sidecar == remuxed.with_suffix(".mp3")
    assert sidecar.exists()
    assert verify_short_audio(sidecar).codec == "mp3"


def test_aac_video_fails_until_site_remux(tmp_path: Path):
    tone = _tone_mp3(tmp_path / "voice.mp3")
    aac = _mux(tmp_path / "aac.mp4", tone, audio_codec="aac")
    with pytest.raises(AudioCheckError, match="need mp3"):
        verify_short_audio(aac)
    remuxed = remux_site_media(aac, tmp_path / "safe.mp4")
    assert verify_short_audio(remuxed).codec == "mp3"


def test_duration_mismatch_fails_the_check(tmp_path: Path):
    picture = _colour_clip(tmp_path / "picture.mp4", seconds=2.4)
    short_tone = _tone_mp3(tmp_path / "short.mp3", seconds=0.4)
    dest = tmp_path / "padded.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(picture),
            "-i",
            str(short_tone),
            "-c:v",
            "copy",
            "-c:a",
            "libmp3lame",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    with pytest.raises(AudioCheckError, match="padded with nothing"):
        verify_short_audio(dest)


def test_failed_check_does_not_replace_site_media(tmp_path: Path):
    dest = tmp_path / "live.mp4"
    dest.write_bytes(b"keep-me")
    mute = _mux(tmp_path / "mute.mp4", None)
    with pytest.raises(AudioCheckError, match="no audio stream"):
        remux_site_media(mute, dest)
    assert dest.read_bytes() == b"keep-me"
    assert not dest.with_name(f".{dest.stem}.audio-remux.mp4").exists()


def test_publish_short_to_media_writes_sidecar(tmp_path: Path):
    tone = _tone_mp3(tmp_path / "voice.mp3")
    film = _mux(tmp_path / "short.mp4", tone)
    dest = tmp_path / "media" / "guardian-30124-9a.mp4"
    publish_short_to_media(film, dest)
    assert dest.exists()
    sidecar = dest.with_suffix(".mp3")
    assert sidecar.exists()
    assert verify_short_audio(dest).codec == "mp3"
    assert verify_short_audio(sidecar).codec == "mp3"


def test_render_one_short_and_pipeline_invoke_the_check():
    render_src = inspect.getsource(render_video)
    assert "finish_short_audio" in render_src
    one = inspect.getsource(render_one_short)
    assert "publish_short_to_media" in one
    assert "copy2(movie" not in one
    today = inspect.getsource(run_today)
    assert "render_video" in today
    copy = inspect.getsource(_copy_media)
    assert "publish_short_to_media" in copy
    assert "looks_like_media" in copy
    finish = inspect.getsource(finish_short_audio)
    assert "remux_site_media" in finish
    assert "write_sidecar_soundtrack" in finish
    assert "verify_short_audio" in finish
    from twodown.render import _concat_motion, _encode_clips

    assert "SITE_AUDIO_ENCODE" in inspect.getsource(_encode_clips)
    assert "SITE_AUDIO_ENCODE" in inspect.getsource(_concat_motion)


def test_site_player_falls_back_to_sidecar_mp3():
    assert 'sidecar = prefix + slug + ".mp3"' in JS
    assert "sidecarTried" in JS
