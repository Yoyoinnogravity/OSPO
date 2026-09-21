# Daily cryptic.fit agent

This package publishes **two** cryptic clues a day from
[Fifteen Squared](https://fifteensquared.net/). A paid Cursor Automation can
run it unattended. Never use another crossword blog as the source.

## What to create

1. Open [cursor.com/automations](https://cursor.com/automations) (or `/automate` in Cursor).
2. Trigger: scheduled, every day at **09:00 Europe/London**
   (`CRON_TZ=Europe/London 0 9 * * *`, or `0 8 * * *` UTC).
   Add a second trigger at **12:00 London** in case the 15² blogs are late.
3. Repository: **Yoyoinnogravity/OSPO**, branch `main` (or this feature branch until it merges).
4. Model: Claude (Cursor Models pool). This is the pick Aled locked. Do not pick Grok.
5. Tools: pull request creation on. Memories optional.
6. Paste the prompt below.
7. Put social tokens on the Cloud Agent environment so uploads actually leave the machine:
   `TWODOWN_YOUTUBE_TOKEN`, `TWODOWN_TIKTOK_TOKEN`, `TWODOWN_META_TOKEN`.
   Ads stay off unless `TWODOWN_ADSENSE_CLIENT` and `TWODOWN_ADSENSE_SLOT` are set.

Automations are billed as Cloud Agent usage on your Cursor plan (Pro and up).
Private automations bill the person who created them.

## Prompt (paste this)

```
You are the daily cryptic.fit agent.

Do exactly two clues from https://fifteensquared.net/ . Never invent an answer.
Never scrape another crossword site.
Hint pictures may be auto / AI matched to the definition at about 80% closeness.
That is good enough. Do not ban AI matching. Do not build a cloud vision pipeline.

1. Check two-down/site/d/{today's London date}/index.html.
   If that page already exists, today's pair is done. Do not regenerate, do not open a PR, stop.
2. From two-down/, run:
     python3 -m twodown today
   A fresh machine has nothing installed, so if that fails with
   "No module named twodown", run `pip install -e .` from two-down/ first and retry.
   If it exits 1 because 15² has no usable Independent / FT / Guardian clues yet, stop.
   Do not invent clues. A later scheduled run can pick them up.
3. If it built a new pair:
   - Commit only two-down/site/ (HTML, CSS, JS, media, scenes). Do not commit two-down/output/.
   - Open or update a PR onto main titled like: cryptic.fit · {date}
   - In the PR body list both clues, papers, 15² URLs, scenes, and which social uploads happened or were skipped.
4. Do not change the world-map / OSPO files. Stay under two-down/.
```

## Manual stand-in

```bash
twodown today          # skip if today's site page already exists
twodown today --force  # rebuild anyway
```
