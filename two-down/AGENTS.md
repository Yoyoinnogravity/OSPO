# Daily cryptic.fit agent

This package publishes **one** cryptic clue a day. The crossword blog it reads is
[Fifteen Squared](https://fifteensquared.net/). Never use another crossword blog
as the source, and never invent an answer.

## Daily YouTube

The schedule is `.github/workflows/cryptic-fit-daily.yml`. After it is on `main`
it runs at 08:00 and 11:00 UTC, films the one clue, and uploads that Short to
https://www.youtube.com/@crypticfit. Each run also posts waiting downloads, at
most five a London day. YouTube's default quota accepts about six inserts;
the sixth slot is today's new film. The noon run shares that cap, so it does
not post a second backlog batch.

The remaining human step is the token. In the repo, **Settings → Secrets and
variables → Actions**, add `TWODOWN_YOUTUBE_TOKEN`. The value is the
authorized-user JSON for the cryptic.fit channel (`token`, `refresh_token`,
`token_uri`, `client_id`, `client_secret`, `scopes` including `youtube.upload`).
When Google asks which channel, pick cryptic.fit. Do not use @crypticfun.

Until that secret exists, the job still films the clue, commits the site, and
then fails the upload so the miss is visible. A second run the same day does
not upload again once `two-down/site/youtube-uploads.json` has the video id.

## What to create

1. Open [cursor.com/automations](https://cursor.com/automations) (or `/automate` in Cursor).
2. Trigger: scheduled, every day at **09:00 Europe/London**
   (`CRON_TZ=Europe/London 0 9 * * *`, or `0 8 * * *` UTC).
   Add a second trigger at **12:00 London** in case the 15² blogs are late.
3. Repository: **Yoyoinnogravity/OSPO**, branch `main` (or this feature branch until it merges).
4. Model: Grok (Cursor Models pool). This is the pick Aled locked. Do not pick Claude / Anthropic.
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

Do exactly one clue. Never invent an answer. Never scrape another crossword site.
The train picks the clue. You do not choose a second one.
Hint pictures may be auto / AI matched to the definition at about 80% closeness.
That is good enough. Do not ban AI matching. Do not build a cloud vision pipeline.

The London date rotates the source: Guardian, Times, Telegraph, your own clues,
then a Clue of the day. Guardian, Financial Times and Independent clues come
only from https://fifteensquared.net/ . Times and Telegraph are not on that blog.
Those days use two-down/own-clues.json, and only a row whose answer and parse
are already written. If that file has nothing for the slot, the train falls
through to a real clue it can film. Do not fetch timesforthetimes.co.uk or
the Telegraph.

1. Check two-down/site/d/{today's London date}/index.html.
   If that page already exists, today's clue is done. Do not regenerate, do not open a PR, stop.
2. From two-down/, run:
     python3 -m twodown today
   A fresh machine has nothing installed, so if that fails with
   "No module named twodown", run `pip install -e .` from two-down/ first and retry.
   If it exits 1 because nothing usable is ready yet, stop.
   Do not invent a clue. A later scheduled run can pick one up.
3. If it built a new clue:
   - The site poster and the YouTube thumbnail are the unsolved clue with empty lights.
     Do not upload a frame, card, or image that shows the answer or the filled grid.
   - The new film is presented by Cryptic Croc, in her own fun female voice.
     Leave the older study cuts and earlier daily films as they are.
   - Commit two-down/site/ (HTML, CSS, JS, media, scenes). Do not commit two-down/output/.
     If an own clue was filmed, also commit two-down/own-clues.json (it records used_on).
   - Open or update a PR onto main titled like: cryptic.fit · {date}
   - In the PR body list the clue, the paper, the rotation slot, the 15² URL or "own clue",
     the scene, and which social uploads happened or were skipped.
     Do not put the answer in the PR title.
4. Do not change the world-map / OSPO files. Stay under two-down/.
```

## Manual stand-in

```bash
twodown today          # skip if today's site page already exists
twodown today --force  # rebuild anyway
```

Own clues live in `two-down/own-clues.json`. A row needs `clue`, `answer`, and
`parse`. Set `paper` to `Times`, `Telegraph`, or your own name. Leave `clues`
empty until a real answer is written down.
