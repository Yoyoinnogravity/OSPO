cryptic.fun
===========

Two cryptic clues a day from [Fifteen Squared](https://fifteensquared.net/),
spoken by **Sonia** (`en-GB-SoniaNeural`), published to **cryptic.fun** and
YouTube Shorts.

The agent does not invent answers. It reads the 15² blog, checks the
enumeration, picks a contrasting pair, speaks the parse, then writes the
site and (when OAuth is present) uploads two unlisted Shorts.

```bash
pip install -e "./two-down[dev]"
twodown today
```

Layout: newsprint cream, crimson `.fun`, clue first, a long pause, then the breakdown.
Voices on the site: **Sonia**, **Ryan**, **Libby**, **Thomas** (picker in the header).
YouTube uses `--voice` (default Sonia).

```bash
twodown today --voice ryan
```

YouTube
-------

Uploads go out as **Cryptic Fun** (two Shorts a day). They need an authorized
user token for the Cryptic Fun channel — not an API key:

```bash
export TWODOWN_YOUTUBE_TOKEN=/path/to/token.json
twodown today
# or, once videos are already rendered:
twodown upload --youtube-privacy public
```

Without that file the pair still lands in `two-down/site/` for cryptic.fun.
Point the domain’s DNS at GitHub Pages or any static host serving that folder
(DNS can take 24–48 hours). The site `CNAME` is `cryptic.fun`.

