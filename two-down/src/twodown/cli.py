from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from twodown.config import DEFAULT_OUTPUT, DEFAULT_VOICE_ALIAS
from twodown.ingest import LONDON
from twodown.models import DailyPair
from twodown.pipeline import run_today
from twodown.voice import list_voices, resolve_voice
from twodown.youtube import YOUTUBE_CHANNEL, upload_pair, youtube_ready


def _print_pair(pair) -> None:
    print(f"date  {pair.date}")
    print(f"voice {pair.voice}")
    print(f"posts {len(pair.source_posts)}")
    if pair.site_index:
        print(f"site  {pair.site_index}")
    if pair.youtube_ids:
        print(f"yt    {', '.join(pair.youtube_ids)}")
    else:
        print("yt    skipped" if not youtube_ready() else "yt    upload failed")
    for i, item in enumerate(pair.clues, start=1):
        clue = item.clue
        print()
        print(f"[{i}] {clue.paper} {clue.puzzle_id} · {clue.setter} · {clue.number} {clue.direction}")
        print(f"    {clue.clue} ({clue.enumeration})")
        print(f"    {clue.answer}  [{clue.device}]")
        print(f"    {clue.source_url}")
        if item.audio_path:
            print(f"    audio {item.audio_path}")
        if item.video_path:
            print(f"    video {item.video_path}")
        if item.site_path:
            print(f"    page  {item.site_path}")
        if item.youtube_id:
            print(f"    yt    https://youtu.be/{item.youtube_id}")


def _latest_pair(out: Path, date: str | None) -> DailyPair:
    if date:
        path = out / date / "pair.json"
    else:
        dates = sorted((p for p in out.iterdir() if p.is_dir()), reverse=True)
        if not dates:
            raise FileNotFoundError(f"No daily output in {out}")
        path = dates[0] / "pair.json"
    if not path.exists():
        raise FileNotFoundError(f"No pair.json at {path}. Run twodown today first.")
    return DailyPair.model_validate_json(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="twodown", description="Two cryptic clues a day from Fifteen Squared.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    today = sub.add_parser("today", help="Ingest 15², pick two clues, speak, publish")
    today.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    today.add_argument("--voice", default=DEFAULT_VOICE_ALIAS, help="YouTube voice: sonia, libby, ryan, thomas. Site visitors can pick any of these.")
    today.add_argument("--date", help="London calendar date YYYY-MM-DD (default: today, else latest)")
    today.add_argument("--quiet", action="store_true", help="Skip TTS, video, site and YouTube")
    today.add_argument("--no-video", action="store_true")
    today.add_argument("--no-site", action="store_true")
    today.add_argument("--no-youtube", action="store_true")
    today.add_argument("--youtube-privacy", default="public", choices=["unlisted", "private", "public"])

    upload = sub.add_parser("upload", help="Upload today's two Shorts to YouTube as Cryptic Fun")
    upload.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    upload.add_argument("--date", help="London calendar date YYYY-MM-DD")
    upload.add_argument("--youtube-privacy", default="public", choices=["unlisted", "private", "public"])

    voices = sub.add_parser("voices", help="List built-in British voices")
    voices.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "voices":
        mapping = list_voices()
        if args.json:
            print(json.dumps(mapping, indent=2))
        else:
            print(f"default: {DEFAULT_VOICE_ALIAS} → {resolve_voice(DEFAULT_VOICE_ALIAS)}")
            for alias, name in mapping.items():
                mark = " (default)" if alias == DEFAULT_VOICE_ALIAS else ""
                print(f"  {alias:8} {name}{mark}")
        return 0

    if args.cmd == "upload":
        if not youtube_ready():
            print(
                f"Cannot upload as {YOUTUBE_CHANNEL}: no OAuth token.\n"
                "Create a YouTube Data API desktop OAuth client, authorize the Cryptic Fun channel,\n"
                "and set TWODOWN_YOUTUBE_TOKEN to the token JSON path.",
                file=sys.stderr,
            )
            return 2
        try:
            pair = _latest_pair(args.out, args.date)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        ids = upload_pair(pair, privacy=args.youtube_privacy)
        if args.date:
            dest = args.out / args.date / "pair.json"
        else:
            dest = sorted((p for p in args.out.iterdir() if p.is_dir()), reverse=True)[0] / "pair.json"
        dest.write_text(pair.model_dump_json(indent=2), encoding="utf-8")
        if not ids:
            print("Upload returned no video ids.", file=sys.stderr)
            return 1
        print(f"uploaded {len(ids)} as {YOUTUBE_CHANNEL}")
        for vid in ids:
            print(f"https://youtu.be/{vid}")
        return 0

    day = None
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=LONDON)
    pair = run_today(
        out_dir=args.out,
        voice=args.voice,
        day=day,
        speak=not args.quiet,
        video=not args.quiet and not args.no_video,
        publish=not args.quiet and not args.no_site,
        youtube=not args.quiet and not args.no_youtube,
        youtube_privacy=args.youtube_privacy,
    )
    if not pair.clues:
        print("No usable clues found on Fifteen Squared for that date.", file=sys.stderr)
        return 1
    _print_pair(pair)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
