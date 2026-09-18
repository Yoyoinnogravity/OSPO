from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from twodown.ads import ads_status
from twodown.config import DEFAULT_OUTPUT, DEFAULT_VOICE_ALIAS, SITE_ORIGIN, SOURCE_SITE, STUDY_SLUG, VOICES
from twodown.ingest import LONDON
from twodown.live import (
    PRODUCT_CHECK_NAMES,
    dns_addresses,
    go_live_next_steps,
    probe,
    public_checks,
    registry_status,
)
from twodown.models import DailyPair
from twodown.pipeline import render_one_short, run_today
from twodown.scenes import DEFAULT_SCENE, list_scenes
from twodown.social import (
    PLATFORMS,
    connect_instructions,
    platform_status,
    publish_pair,
    setup_hints,
)
from twodown.voice import list_voices, resolve_voice
from twodown.youtube import YOUTUBE_CHANNEL


def _print_pair(pair) -> None:
    print(f"source {getattr(pair, 'source_site', None) or SOURCE_SITE}")
    print(f"date  {pair.date}")
    print(f"voice {pair.voice}")
    print(f"posts {len(pair.source_posts)}")
    if pair.site_index:
        print(f"site  {pair.site_index}")
    print(f"yt    {', '.join(pair.youtube_ids) if pair.youtube_ids else 'skipped'}")
    print(f"tiktok {', '.join(pair.tiktok_ids) if pair.tiktok_ids else 'skipped'}")
    print(f"ig    {', '.join(pair.instagram_ids) if pair.instagram_ids else 'skipped'}")
    print(f"fb    {', '.join(pair.facebook_ids) if pair.facebook_ids else 'skipped'}")
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
        if item.scene:
            print(f"    scene {item.scene}")
        if item.youtube_id:
            print(f"    yt    https://youtu.be/{item.youtube_id}")
        if item.tiktok_id:
            print(f"    tiktok {item.tiktok_id}")
        if item.instagram_id:
            print(f"    ig    {item.instagram_id}")
        if item.facebook_id:
            print(f"    fb    {item.facebook_id}")


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


def _pair_path(out: Path, date: str | None) -> Path:
    if date:
        return out / date / "pair.json"
    return sorted((p for p in out.iterdir() if p.is_dir()), reverse=True)[0] / "pair.json"


def _add_social_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-youtube", action="store_true")
    parser.add_argument("--no-tiktok", action="store_true")
    parser.add_argument("--no-instagram", action="store_true")
    parser.add_argument("--no-facebook", action="store_true")
    parser.add_argument("--no-social", action="store_true", help="Skip TikTok, Instagram and Facebook")


def _wanted(args) -> dict[str, bool]:
    social = not getattr(args, "no_social", False)
    return {
        "youtube": not args.no_youtube,
        "tiktok": social and not args.no_tiktok,
        "instagram": social and not args.no_instagram,
        "facebook": social and not args.no_facebook,
    }


def _print_status() -> None:
    status = platform_status()
    hints = setup_hints()
    print(f"source  {SOURCE_SITE}")
    print(f"channel {YOUTUBE_CHANNEL}")
    ads_state, ads_hint = ads_status()
    print(f"  ads        {ads_state}")
    if ads_state != "ready":
        print(f"             {ads_hint}")
    for name in PLATFORMS:
        state = "ready" if status[name] else "needs token"
        print(f"  {name:10} {state}")
        if not status[name]:
            print(f"             {hints[name]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="twodown",
        description="Two cryptic clues a day from https://fifteensquared.net/.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    today = sub.add_parser("today", help="Ingest https://fifteensquared.net/, pick two clues, speak, publish")
    today.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    today.add_argument("--voice", default=DEFAULT_VOICE_ALIAS, help="YouTube/social voice: sonia, libby, ryan, thomas. Site visitors can pick any of these.")
    today.add_argument(
        "--scene",
        choices=[scene.slug for scene in list_scenes()],
        help="Pin both Shorts to one background. Default: two different places.",
    )
    today.add_argument("--date", help="London calendar date YYYY-MM-DD (default: today, else latest)")
    today.add_argument("--quiet", action="store_true", help="Skip TTS, video, site and social uploads")
    today.add_argument("--no-video", action="store_true")
    today.add_argument("--no-site", action="store_true")
    today.add_argument("--force", action="store_true", help="Rebuild even if today's pair is already on the site")
    today.add_argument("--youtube-privacy", default="public", choices=["unlisted", "private", "public"])
    _add_social_flags(today)

    upload = sub.add_parser("upload", help="Upload today's two Shorts to YouTube, TikTok, Instagram and Facebook")
    upload.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    upload.add_argument("--date", help="London calendar date YYYY-MM-DD")
    upload.add_argument("--youtube-privacy", default="public", choices=["unlisted", "private", "public"])
    _add_social_flags(upload)

    short = sub.add_parser("short", help="Rebuild one Short while we lock the beat")
    short.add_argument(
        "slug",
        nargs="?",
        default=STUDY_SLUG,
        help=f"Study or published clue slug (default: {STUDY_SLUG}, RASTA)",
    )
    short.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    short.add_argument("--all-voices", action="store_true", help="Speak all four voices. Default: Sonia only.")
    short.add_argument("--no-site", action="store_true", help="Write the film under --out only")

    voices = sub.add_parser("voices", help="List built-in British voices")
    voices.add_argument("--json", action="store_true")

    scenes = sub.add_parser("scenes", help="List background scenes")
    scenes.add_argument("--json", action="store_true")

    sub.add_parser("status", help="Show which social accounts are connected")
    sub.add_parser("connect", help="Show the token JSON the upload agent needs")
    sub.add_parser("live", help="Check which public URLs actually respond")

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

    if args.cmd == "scenes":
        catalog = [
            {
                "slug": scene.slug,
                "label": scene.label,
                "place": scene.place,
                "license": scene.license,
                "photographer": scene.photographer,
                "commons": scene.commons_url,
            }
            for scene in list_scenes()
        ]
        if args.json:
            print(json.dumps(catalog, indent=2))
        else:
            print(f"default site scene: {DEFAULT_SCENE}")
            print("daily pair: two different places, unless --scene pins one")
            for scene in list_scenes():
                extra = f"  {scene.license}" if scene.license else ""
                print(f"  {scene.slug:14} {scene.label}{extra}")
        return 0

    if args.cmd == "status":
        _print_status()
        return 0

    if args.cmd == "connect":
        print(connect_instructions(), end="")
        _print_status()
        return 0

    if args.cmd == "live":
        print("Public URLs (live = HTTP 2xx/3xx from here right now)")
        seen: dict[str, str] = {}
        for name, url in public_checks():
            state, detail = probe(url)
            mark = "LIVE" if state == "live" else "down"
            print(f"  {mark:4}  {name:16}  {url}  ({detail})")
            seen[name] = state
        registry, reg_detail = registry_status()
        dns_state, dns_detail = dns_addresses()
        print()
        print(f"registry  {registry}  ({reg_detail})")
        print(f"dns       {dns_state}  ({dns_detail})")
        domain_live = seen.get("cryptic.fun") == "live"
        pages_live = seen.get("GitHub Pages") == "live"
        steps = go_live_next_steps(
            registry=registry,
            pages_live=pages_live,
            domain_live=domain_live,
        )
        if steps:
            print()
            print("cryptic.fun is not on the public internet yet.")
            if registry == "absent":
                print("Chrome's DNS_PROBE_FINISHED_NXDOMAIN is this: the name is not registered.")
            print("Next:")
            for i, step in enumerate(steps, start=1):
                print(f"  {i}. {step}")
            print(f"Then: {SITE_ORIGIN}/")
        elif not any(seen.get(name) == "live" for name in PRODUCT_CHECK_NAMES):
            print()
            print("cryptic.fun is not on the public internet yet.")
        return 0

    if args.cmd == "short":
        voices = list(VOICES) if args.all_voices else [DEFAULT_VOICE_ALIAS]
        item = render_one_short(
            args.slug,
            dest=args.out,
            voices=voices,
            publish=not args.no_site,
        )
        clue = item.clue
        print(f"study {clue.slug}")
        print(f"{clue.paper} {clue.puzzle_id} · {clue.setter} · {clue.number} {clue.direction}")
        print(f"{clue.clue} ({clue.enumeration})")
        print(item.script)
        if item.video_path:
            print(f"video {item.video_path}")
        return 0

    if args.cmd == "upload":
        wanted = _wanted(args)
        status = platform_status()
        ready = [name for name in PLATFORMS if wanted[name] and status[name]]
        if not ready:
            print("No connected social accounts for the requested platforms.", file=sys.stderr)
            _print_status()
            return 2
        try:
            pair = _latest_pair(args.out, args.date)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        notes = publish_pair(
            pair,
            youtube=wanted["youtube"],
            tiktok=wanted["tiktok"],
            instagram=wanted["instagram"],
            facebook=wanted["facebook"],
            youtube_privacy=args.youtube_privacy,
        )
        dest = _pair_path(args.out, args.date)
        dest.write_text(pair.model_dump_json(indent=2), encoding="utf-8")
        uploaded = False
        for name in ready:
            values = [v for v in notes.get(name, []) if not str(v).startswith("error:")]
            if values:
                uploaded = True
            print(f"{name}: {', '.join(notes.get(name, []) or ['nothing uploaded'])}")
        if not uploaded:
            print("Upload returned no video ids.", file=sys.stderr)
            return 1
        return 0

    day = None
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=LONDON)
    wanted = _wanted(args)
    social = not args.quiet
    pair = run_today(
        out_dir=args.out,
        voice=args.voice,
        day=day,
        speak=not args.quiet,
        video=not args.quiet and not args.no_video,
        publish=not args.quiet and not args.no_site,
        youtube=social and wanted["youtube"],
        youtube_privacy=args.youtube_privacy,
        scene=args.scene,
        tiktok=social and wanted["tiktok"],
        instagram=social and wanted["instagram"],
        facebook=social and wanted["facebook"],
        force=args.force,
    )
    if pair.already_published and not pair.clues:
        print(f"already published {pair.date} — skip (use --force to rebuild)")
        return 0
    if not pair.clues:
        print(f"No usable clues found on {SOURCE_SITE} for that date.", file=sys.stderr)
        return 1
    if pair.already_published:
        print(f"already published {pair.date}")
    _print_pair(pair)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
