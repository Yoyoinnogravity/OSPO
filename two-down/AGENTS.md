# Daily Cryptic AI for Fun agent

This package publishes **two** cryptic clues a day from
[Fifteen Squared](https://fifteensquared.net/). GitHub Actions runs it
unattended once `TWODOWN_YOUTUBE_TOKEN` is a repo secret. Never use
another crossword blog as the source.

## What is already set up

`.github/workflows/cryptic-ai-daily.yml` runs `twodown today` at 08:00
and 11:00 UTC (09:00 and 12:00 London in BST). It uploads to YouTube when
the secret exists. It opens a site PR when the pair is new.

1. Create the YouTube channel **Cryptic AI for Fun** and claim `@crypticaiforfun`.
2. Paste tokens as GitHub Actions secrets on Yoyoinnogravity/OSPO:
   `TWODOWN_YOUTUBE_TOKEN` and, for Facebook + Instagram, `TWODOWN_META_TOKEN`.
3. Merge this workflow onto `main`, then **Actions → Cryptic AI for Fun daily → Run workflow**.
   First manual run can be **unlisted**. The schedule posts **public**.

A Cursor Automation at [cursor.com/automations](https://cursor.com/automations)
is optional. If you add one: 09:00 Europe/London, Grok, prompt below,
and the same token on the Cloud Agent environment.

Automations are billed as Cloud Agent usage on your Cursor plan (Pro and up).
Private automations bill the person who created them.

## Prompt (paste this)

```
You are the daily Cryptic AI for Fun agent. The site is cryptic.fit.

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
   - Open or update a PR onto main titled like: Cryptic AI for Fun · {date}
   - In the PR body list both clues, papers, 15² URLs, scenes, and which social uploads happened or were skipped.
4. Do not change the world-map / OSPO files. Stay under two-down/.
```

## Manual stand-in

```bash
twodown today          # skip if today's site page already exists
twodown today --force  # rebuild anyway
```
