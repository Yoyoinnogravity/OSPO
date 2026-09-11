cryptic.fun
===========

Two cryptic clues a day from [Fifteen Squared](https://fifteensquared.net/),
spoken by **Sonia** (`en-GB-SoniaNeural`), published to **cryptic.fun** and
sent out as **Cryptic Fun** Shorts / Reels on YouTube, TikTok, Instagram and
Facebook.

The agent does not invent answers. It reads the 15² blog, checks the
enumeration, picks a contrasting pair, speaks the parse, then writes the
site and uploads to every connected account.

```bash
pip install -e "./two-down[dev]"
twodown today
twodown status
```

Layout: cream clue cards on photographs of real places (Machu Picchu,
Matterhorn, Santorini, Grand Canyon, Kyoto, aurora, Petra, Ha Long Bay),
with newsprint still available. Visitors pick **Place** in the header.
Daily Shorts rotate two different scenes unless you pass `--scene`.
Voices on the site: **Sonia**, **Ryan**, **Libby**, **Thomas**.
YouTube and the other apps use `--voice` (default Sonia).

Visitors can **suggest one homemade clue a day**, or ask for a daily clue by
email. Both open a message to **aledmorgan@gmail.com**.

```bash
twodown today --voice ryan
twodown today --scene newsprint
twodown scenes
```

Photographs are Wikimedia Commons crops, credited on the About page and in
the YouTube description. TikTok / Instagram / Facebook captions keep the
answer in the video, not the caption.

Social
------

`twodown today` and `twodown upload` send the same two vertical videos to
every platform that has a token. Missing tokens are skipped, not fatal.

```bash
export TWODOWN_YOUTUBE_TOKEN=/path/to/youtube-token.json
export TWODOWN_TIKTOK_TOKEN=/path/to/tiktok-token.json
export TWODOWN_META_TOKEN=/path/to/meta-token.json
twodown today
# or, once videos are already rendered:
twodown upload
twodown upload --no-youtube          # TikTok + Instagram + Facebook only
```

Token files:

* **YouTube** — authorized desktop OAuth user JSON for the Cryptic Fun channel.
* **TikTok** — `{"access_token": "..."}` from a TikTok app with `video.publish`
  (Content Posting API, FILE_UPLOAD). Unaudited apps are limited to private /
  self-only until TikTok reviews the app.
* **Instagram + Facebook** — one Meta Page token JSON:

  ```json
  {
    "access_token": "PAGE_ACCESS_TOKEN",
    "page_id": "FACEBOOK_PAGE_ID",
    "ig_user_id": "INSTAGRAM_PROFESSIONAL_ID"
  }
  ```

  The Instagram account must be professional and linked to that Page.
  Permissions: `pages_manage_posts`, `pages_show_list`, `pages_read_engagement`,
  `instagram_content_publish`.

Defaults if the env vars are unset: `~/.config/twodown/youtube-token.json`,
`tiktok-token.json`, `meta-token.json`.

Without tokens the pair still lands in `two-down/site/` for cryptic.fun.
Point the domain’s DNS at GitHub Pages or any static host serving that folder
(DNS can take 24–48 hours). The site `CNAME` is `cryptic.fun`.

Daily agent
-----------

Yes — pay Cursor to run this every morning. Create a Cloud Agent automation at
[cursor.com/automations](https://cursor.com/automations):

* Trigger: every day 09:00 Europe/London (optional second run at 12:00 if 15² is late)
* Repo: this one, so it can commit `two-down/site/`
* Prompt: copy the block in `two-down/AGENTS.md`
* Secrets on the environment: the YouTube / TikTok / Meta token files above

That is billed as Cloud Agent usage on Pro and above. The pipeline will not
invent answers, and it will skip if today’s pair is already on the site
(`twodown today --force` rebuilds).

A cheaper non-agent option is a machine cron of `twodown today` with those
same tokens. The paid agent is the one that can recover when 15² changes layout.

