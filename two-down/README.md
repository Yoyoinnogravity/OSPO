Cryptic AI for Fun
==================

We provide unique cryptic crossword clues and solutions.
We credit all — the setter, the paper, Fifteen Squared, and the photograph.
The only source is [Fifteen Squared](https://fifteensquared.net/),
cut as newsprint Shorts. **Ryan** opens and offers the picture clue,
**Sonia** solves, **Thomas** credits the setter and Fifteen Squared.
The name is **Cryptic AI for Fun**. The site stays **cryptic.fit**.
YouTube is **@crypticaiforfun**. Ryan’s last line is
**We are here to help then dominate.**

Do not invent answers. Do not scrape other crossword blogs.

Make one video (uses the locked beat; does not rebuild the other films):

```bash
cd two-down
python3 -m twodown short              # current study clue
python3 -m twodown short smiles
python3 -m twodown short cole
```

Send the next Fifteen Squared clue as: answer, surface, letter count, parse.
One clue at a time.

Daily pair from today’s 15² blogs:

```bash
pip install -e "./two-down[dev]"
twodown today
twodown status
```

Studio of the films we already cut: `two-down/site/studio.html`.

Study Shorts are **newsprint**. Older daily pages still have place photos.
Voices on the film: **Ryan** opens and offers the picture clue, **Sonia** solves, **Thomas** credits. Libby stays as the clearer optional read.

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
GitHub Actions (`.github/workflows/cryptic-ai-daily.yml`) runs `twodown today`
every morning once `TWODOWN_YOUTUBE_TOKEN` is a repo secret.

```bash
export TWODOWN_YOUTUBE_TOKEN=/path/to/youtube-token.json
export TWODOWN_TIKTOK_TOKEN=/path/to/tiktok-token.json
export TWODOWN_META_TOKEN=/path/to/meta-token.json
twodown today
# or, once videos are already rendered:
twodown upload
twodown upload --no-youtube          # TikTok + Instagram + Facebook only
```

`twodown connect` prints the exact steps and links for each app.

Token files:

* **YouTube** — authorized desktop OAuth user JSON for **Cryptic AI for Fun**
  (`youtube.com/@crypticaiforfun`). The site stays cryptic.fit. Do not use
  `@crypticfun` — that handle is someone else's channel, and we do not own `.fun`.
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

Without tokens the pair still lands in `two-down/site/` for cryptic.fit.
That folder is a complete static site. Upload its contents to any host
(`public_html`, Netlify, Cloudflare Pages). The site `CNAME` is `cryptic.fit`.
DNS only works after the name is actually registered (see Go live).

Daily agent
-----------

Yes — pay Cursor to run this every morning.

**How to pay**

1. Sign in as Aled at [cursor.com/dashboard/billing](https://cursor.com/dashboard/billing).
2. You need a **paid plan**. Pro+ ($60/month) is the sensible budget for one
   Grok-run Short a day. Click **Adjust plan** if you are still on Hobby or Pro.
3. Click **Manage Subscription** to add or update a card in Stripe.
4. On the **Spending** tab, turn on **on-demand usage** and set a monthly cap
   around $40 (Cloud Agents and Automations bill from this after included usage).
5. Create the daily job at [cursor.com/automations](https://cursor.com/automations)
   using the prompt in `two-down/AGENTS.md`.
   Pick **Grok**. Do not pick Claude / Anthropic.

That is the only thing you pay Cursor for. GitHub Pages and YouTube upload are free.

**Go live on cryptic.fit**

Aled owns **cryptic.fit**. The brand is cryptic.fit on the site and YouTube.

1. In Namecheap, switch nameservers from **Web Hosting DNS** to
   **Namecheap BasicDNS**. Leave paid hosting unused.
2. Advanced DNS: `A` records for `@` to `185.199.108.153`,
   `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
3. Merge the cryptic.fit PR.
4. Repo **Settings → Pages → Source: GitHub Actions**.
5. GitHub Pages custom domain: `cryptic.fit`.

Do **not** upload with cPanel File Manager, FileZilla, or `scp` to
`public_html`. GitHub Actions publishes `two-down/site/`.

`twodown live` prints this same order (registry first, then Pages, then DNS).

YouTube still needs `TWODOWN_YOUTUBE_TOKEN` (OAuth for Cryptic AI for Fun),
not a payment.

Money
-----

Ads stay **off** until the domain is live and AdSense is approved. The layout
already has a labelled slot **under** today’s pair, never inside Solve.

When hits arrive, the stack is:

1. **YouTube Shorts** — real money once cryptic.fit is in the Partner Program
   (1,000 subscribers and 10 million Shorts views in 90 days, or 4,000
   long-form hours). Same AdSense account can later cover the website.
2. **One Google display unit on cryptic.fit** — after
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

SEO
---

Every page gets a canonical `https://cryptic.fit/…` URL, a spoiler-safe
description, Open Graph / Twitter cards, and JSON-LD. Answers are kept out of
titles, descriptions and the RSS feed, and wrapped in `data-nosnippet` so
Google should not print them in search results.

Published with the site: `sitemap.xml`, `feed.xml`, `robots.txt`, `media/og.webp`.

After the domain resolves:

1. [Google Search Console](https://search.google.com/search-console) — add
   `https://cryptic.fit`, then either paste the verification code as
   `TWODOWN_GSC_VERIFY` and rebuild, or upload the HTML file Google gives you.
2. Submit `https://cryptic.fit/sitemap.xml`.
3. Same sitemap in [Bing Webmaster Tools](https://www.bing.com/webmasters).

```bash
twodown live    # which public URLs actually respond
```

