Two Down
========

Two cryptic clues a day, pulled from [Fifteen Squared](https://fifteensquared.net/),
spoken for a YouTube Short. Channel voice: **Sonia** (`en-GB-SoniaNeural`) —
clear southern British, slowed slightly so the wordplay lands.

This does not invent answers. It reads the 15² blog, checks the enumeration,
picks a contrasting pair, rewrites a short spoken parse, then renders audio
and a 9:16 card.

Run
---

```bash
cd two-down
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/twodown voices
.venv/bin/twodown today
```

Output lands in `two-down/output/YYYY-MM-DD/<clue>/`:

- `voice.mp3` — Sonia reading the parse
- `card.png` / `short.mp4` — vertical still + audio
- `script.txt` — what she says
- `pair.json` — the day's pair

Voices: `sonia` (default), `libby`, `ryan`, `thomas`.

```bash
.venv/bin/twodown today --voice ryan
```

Do not auto-upload. Each video must name the setter, the paper, the 15²
blogger, and link the post. `cryptic.fit` is the redirect, not a second blog.
