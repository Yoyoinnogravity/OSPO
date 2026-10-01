"""One listen-along trial with unused Ava / Andrew aliases.

Does not change the published films or the site voice bar.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from twodown.config import (
    TRIAL_INTRO_VOICE_ALIAS,
    TRIAL_PRESENTER_VOICE_ALIAS,
    TRIAL_VOICE_LABELS,
    TRIAL_VOICES,
)
from twodown.pipeline import published_clue
from twodown.render import draw_beat, draw_clue_card, draw_reveal_card, render_video
from twodown.script import write_parts
from twodown.voice import build_short_soundtrack, list_trial_voices, resolve_voice

ELICIT_SLUG = "guardian-30124-9a"
ELICIT_ANSWER = "ELICIT"


def export_chat_sample(video: Path, audio: Path, dest_video: Path, dest_audio: Path) -> None:
    """H.264 + MP3. The chat player drops AAC."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to export the chat sample")
    dest_video.parent.mkdir(parents=True, exist_ok=True)
    dest_audio.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audio, dest_audio)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-shortest",
            str(dest_video),
        ],
        check=True,
        capture_output=True,
    )


def render_elicit_trial(
    dest: Path,
    *,
    intro_alias: str = TRIAL_INTRO_VOICE_ALIAS,
    presenter_alias: str = TRIAL_PRESENTER_VOICE_ALIAS,
) -> dict[str, Path]:
    clue = published_clue(ELICIT_SLUG)
    if clue.answer != ELICIT_ANSWER:
        raise ValueError(f"refusing to invent an answer; published clue is {clue.answer}")
    dest.mkdir(parents=True, exist_ok=True)
    parts = write_parts(clue)
    (dest / "script.txt").write_text(parts.full + "\n", encoding="utf-8")
    audio = dest / "voice-trial.mp3"
    timings = build_short_soundtrack(
        parts,
        audio,
        presenter_alias,
        intro_alias=intro_alias,
        presenter_alias=presenter_alias,
    )
    clue_card = draw_clue_card(clue, dest / "clue.png")
    draw_beat(clue, dest / "hint.png", "hint")
    reveal = draw_reveal_card(clue, dest / "card.png")
    movie = render_video(
        clue_card,
        reveal,
        audio,
        dest / "short.mp4",
        clue_hold=timings.until_answer,
        clue=clue,
        timings=timings,
    )
    return {
        "audio": audio,
        "video": movie,
        "script": dest / "script.txt",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One unused Ava + Andrew listen-along trial.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/twodown-natural-voices"),
        help="Working folder for the trial cut",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("/opt/cursor/artifacts"),
        help="Chat-playable mp4/mp3 destination",
    )
    args = parser.parse_args(argv)
    paths = render_elicit_trial(args.out)
    export_chat_sample(
        paths["video"],
        paths["audio"],
        args.artifacts / "elicit_natural_voices.mp4",
        args.artifacts / "elicit_natural_voices.mp3",
    )
    print(f"invite {TRIAL_VOICE_LABELS[TRIAL_INTRO_VOICE_ALIAS]} → {resolve_voice(TRIAL_INTRO_VOICE_ALIAS)}")
    print(
        f"croc   {TRIAL_VOICE_LABELS[TRIAL_PRESENTER_VOICE_ALIAS]} → "
        f"{resolve_voice(TRIAL_PRESENTER_VOICE_ALIAS)}"
    )
    for alias, neural in list_trial_voices().items():
        print(f"trial  {alias:8} {neural}")
    print(f"video  {args.artifacts / 'elicit_natural_voices.mp4'}")
    print(f"audio  {args.artifacts / 'elicit_natural_voices.mp3'}")
    unused = ", ".join(sorted(TRIAL_VOICES))
    print(f"unused aliases: {unused} (not on the site until a pick)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
