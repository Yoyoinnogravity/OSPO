cryptic.fun
===========

Two cryptic clues a day from [Fifteen Squared](https://fifteensquared.net/),
spoken by **Sonia** (`en-GB-SoniaNeural`), published to **cryptic.fun** and
sent out as **Cryptic Fun** Shorts / Reels on YouTube, TikTok, Instagram and
Facebook.

The only source is **https://fifteensquared.net/**. The agent reads that
site’s homepage and WordPress API. It does not invent answers or scrape
other crossword blogs. It checks the enumeration, picks a contrasting pair,
speaks the parse, then writes the site and uploads to every connected account.

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

Yes — pay Cursor to run this every morning.

**How to pay**

1. Sign in as Aled at [cursor.com/dashboard/billing](https://cursor.com/dashboard/billing).
2. You need a **paid plan** (Pro is $20/month). Click **Adjust plan** if you are still on Hobby.
3. Click **Manage Subscription** to add or update a card in Stripe.
4. On the **Spending** tab, turn on **on-demand usage** and set a monthly cap
   (Cloud Agents and Automations bill from this after included usage).
5. Create the daily job at [cursor.com/automations](https://cursor.com/automations)
   using the prompt in `two-down/AGENTS.md`.
   Pick Composer 2.5 or Grok 4.6 so it spends the cheaper Cursor Models pool.

That is the only thing you pay Cursor for. GitHub Pages and YouTube upload are free.
The domain is already yours; it just needs DNS pointed at GitHub.

**Go live**

* Merge the Cryptic Fun PR.
* Repo **Settings → Pages → Source: GitHub Actions**.
* Point `cryptic.fun` at GitHub Pages (`A` records `185.199.108.153`,
  `185.199.109.153`, `185.199.110.153`, `185.199.111.153`).
* Custom domain: `cryptic.fun`.

YouTube still needs `TWODOWN_YOUTUBE_TOKEN` (OAuth for the Cryptic Fun channel),
not a payment.

Money
-----

Ads stay **off** until the domain is live and AdSense is approved. The layout
already has a labelled slot **under** today’s pair, never inside Solve.

When hits arrive, the stack is:

1. **YouTube Shorts** — real money once Cryptic Fun is in the Partner Program
   (1,000 subscribers and 10 million Shorts views in 90 days, or 4,000
   long-form hours). Same AdSense account can later cover the website.
2. **One Google display unit on cryptic.fun** — after
   [adsense.google.com](https://www.google.com/adsense/) approves the custom
   domain. Manual unit only; do not turn on Auto ads (they can cover the
   answer). UK visitors need a consent banner before any ad cookie.
3. **Sponsor a week** — quieter and better paid for a crossword audience.
   Mail [aledmorgan@gmail.com](mailto:aledmorgan@gmail.com).

AdSense may refuse a site that mostly reprints other people’s puzzles. If
that happens, skip site ads and keep YouTube + sponsors.

```bash
export TWODOWN_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX
export TWODOWN_ADSENSE_SLOT=0000000000
twodown today --force --no-youtube --no-social   # rebuild site + ads.txt
twodown status                                   # ads should read "ready"
```

`two-down/site/ads.txt` is written only when the publisher id is set.
The public copy is `two-down/site/support.html`.

