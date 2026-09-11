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

Layout: newsprint cream, crimson `.fun`, clue first then reveal.
Voice: Sonia. Swap with `--voice ryan`.

YouTube
-------

Uploads need an authorized user token (not an API key):

```bash
export TWODOWN_YOUTUBE_TOKEN=/path/to/token.json
twodown today --youtube-privacy unlisted
```

Without that file the pair still lands in `two-down/site/` for cryptic.fun.
Point the domain’s DNS at GitHub Pages or any static host serving that folder.
The site `CNAME` is `cryptic.fun`.
