from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from shutil import copy2

from twodown.config import BRAND, SITE_ORIGIN, SITE_ROOT, VOICE_LABELS
from twodown.models import DailyPair, SpokenClue

CSS = """
:root {
  --news: #f3ead6;
  --ink: #1a1510;
  --crimson: #b81c29;
  --muted: #5c4e40;
  --cream: #fcf7ec;
  --rule: rgba(184, 28, 41, 0.35);
}
* { box-sizing: border-box; }
html { background: var(--news); }
body {
  margin: 0;
  color: var(--ink);
  font-family: "Liberation Serif", "Georgia", serif;
  background:
    linear-gradient(transparent 53px, rgba(184,28,41,0.06) 54px),
    linear-gradient(90deg, transparent 53px, rgba(26,21,16,0.05) 54px),
    var(--news);
  background-size: 54px 54px, 54px 54px, auto;
  min-height: 100vh;
}
a { color: var(--crimson); }
header, main, footer { width: min(1100px, calc(100% - 40px)); margin: 0 auto; }
header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 28px 0 18px;
  border-bottom: 4px solid var(--crimson);
}
.wordmark { font-family: "Liberation Sans", "Helvetica Neue", sans-serif; font-weight: 700; font-size: 1.6rem; letter-spacing: 0.02em; color: var(--ink); text-decoration: none; }
.wordmark span { color: var(--crimson); }
nav a { margin-left: 18px; font-family: "Liberation Sans", sans-serif; font-size: 0.9rem; text-decoration: none; color: var(--muted); }
.voices { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.voices span { font-family: "Liberation Sans", sans-serif; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-right: 4px; }
.voices button {
  font-family: "Liberation Sans", sans-serif;
  background: transparent;
  border: 1px solid var(--rule);
  color: var(--ink);
  padding: 6px 10px;
  cursor: pointer;
  font-size: 0.85rem;
}
.voices button.on { background: var(--crimson); color: var(--cream); border-color: var(--crimson); }
header { flex-wrap: wrap; gap: 12px; }
h1 { font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05; margin: 28px 0 8px; }
.lede { font-size: 1.15rem; color: var(--muted); max-width: 40rem; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin: 36px 0 64px; }
@media (max-width: 800px) { .pair { grid-template-columns: 1fr; } }
article.clue {
  background: var(--cream);
  border: 1px solid var(--rule);
  padding: 22px 22px 18px;
  box-shadow: 6px 6px 0 rgba(184, 28, 41, 0.12);
}
.kicker { font-family: "Liberation Sans", sans-serif; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--crimson); margin: 0 0 12px; }
.clue-text { font-size: 1.55rem; line-height: 1.25; margin: 0 0 18px; }
button.reveal {
  font-family: "Liberation Sans", sans-serif;
  background: var(--crimson);
  color: var(--cream);
  border: 0;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 0.95rem;
}
.spoiler { display: none; margin-top: 16px; }
article.clue.is-open .spoiler { display: block; }
article.clue.is-open button.reveal { display: none; }
video { width: 100%; background: #111; }
audio.parse-voice { width: 100%; margin-top: 8px; }
.answer { font-size: 2rem; color: var(--crimson); margin: 12px 0 6px; }
.parse { color: var(--muted); font-size: 0.98rem; }
.credit { font-family: "Liberation Sans", sans-serif; font-size: 0.85rem; }
footer { border-top: 2px solid var(--crimson); padding: 24px 0 48px; color: var(--muted); font-family: "Liberation Sans", sans-serif; font-size: 0.85rem; }
"""

JS = """
const VOICE_KEY = "cryptic-fun-voice";

function currentVoice() {
  return localStorage.getItem(VOICE_KEY) || "sonia";
}

function applyVoice(alias) {
  localStorage.setItem(VOICE_KEY, alias);
  document.querySelectorAll("[data-voice-btn]").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.voice === alias);
    btn.setAttribute("aria-pressed", btn.dataset.voice === alias ? "true" : "false");
  });
  document.querySelectorAll("article.clue").forEach((article) => {
    const audio = article.querySelector("audio.parse-voice");
    if (!audio) return;
    const prefix = audio.dataset.prefix;
    const slug = article.dataset.slug;
    const t = audio.currentTime || 0;
    const wasPlaying = !audio.paused && !audio.ended;
    audio.src = prefix + slug + "-" + alias + ".mp3";
    audio.dataset.voice = alias;
    const resume = () => {
      audio.currentTime = t;
      if (wasPlaying) audio.play();
    };
    audio.addEventListener("loadedmetadata", resume, { once: true });
  });
}

document.querySelectorAll("[data-voice-btn]").forEach((btn) => {
  btn.addEventListener("click", () => applyVoice(btn.dataset.voice));
});
applyVoice(currentVoice());

document.querySelectorAll("button.reveal").forEach((btn) => {
  btn.addEventListener("click", () => btn.closest("article").classList.add("is-open"));
});

document.querySelectorAll("article.clue").forEach((article) => {
  const video = article.querySelector("video");
  const audio = article.querySelector("audio.parse-voice");
  if (!video || !audio) return;
  video.muted = true;
  video.addEventListener("play", () => {
    audio.currentTime = video.currentTime;
    audio.play();
  });
  video.addEventListener("pause", () => audio.pause());
  video.addEventListener("seeked", () => {
    audio.currentTime = video.currentTime;
  });
});
"""


def _e(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def _voice_bar() -> str:
    buttons = []
    for alias, label in VOICE_LABELS.items():
        buttons.append(
            f'<button type="button" data-voice-btn data-voice="{_e(alias)}" aria-pressed="false">{_e(label)}</button>'
        )
    return '<div class="voices" role="group" aria-label="Choose a voice"><span>Voice</span>' + "".join(buttons) + "</div>"


def _page(title: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <header>
    <a class="wordmark" href="{prefix}index.html">cryptic<span>.fun</span></a>
    {_voice_bar()}
    <nav>
      <a href="{prefix}index.html">Today</a>
      <a href="{prefix}about.html">About</a>
    </nav>
  </header>
  <main>
    {body}
  </main>
  <footer>
    Two clues a day from the Independent, Guardian and FT blogs on
    <a href="https://fifteensquared.net/">Fifteen Squared</a>.
    Not affiliated with those papers. Pick Sonia, Ryan, Libby or Thomas.
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def _article(item: SpokenClue, media_prefix: str, open_by_default: bool = False) -> str:
    clue = item.clue
    opened = " is-open" if open_by_default else ""
    video = ""
    if item.video_path:
        video = f'<video controls playsinline muted src="{_e(media_prefix + clue.slug + ".mp4")}"></video>'
    audio = (
        f'<audio class="parse-voice" controls preload="none" data-prefix="{_e(media_prefix)}" '
        f'src="{_e(media_prefix + clue.slug)}-sonia.mp3"></audio>'
    )
    enum = f" ({_e(clue.enumeration)})" if clue.enumeration else ""
    return f"""
    <article class="clue{opened}" data-slug="{_e(clue.slug)}">
      <p class="kicker">{_e(clue.paper)} {_e(clue.puzzle_id)} · {_e(clue.setter)} · {_e(clue.number)} {_e(clue.direction)} · {_e(clue.device)}</p>
      <p class="clue-text">{_e(clue.clue)}{enum}</p>
      <button class="reveal" type="button">Solve</button>
      <div class="spoiler">
        {video}
        {audio}
        <p class="answer">{_e(clue.answer)}</p>
        <p class="parse">{_e(clue.parse)}</p>
        <p class="credit">Parse via <a href="{_e(clue.source_url)}">Fifteen Squared · {_e(clue.blogger)}</a></p>
      </div>
    </article>
    """


def _copy_media(pair: DailyPair, dest: Path) -> None:
    media = dest / "media"
    media.mkdir(parents=True, exist_ok=True)
    for item in pair.clues:
        if item.video_path:
            copy2(item.video_path, media / f"{item.clue.slug}.mp4")
        for alias, path in item.voice_paths.items():
            copy2(path, media / f"{item.clue.slug}-{alias}.mp3")


def publish_site(pair: DailyPair, dest: Path | None = None) -> Path:
    root = Path(dest or SITE_ROOT)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (root / "assets" / "app.js").write_text(JS, encoding="utf-8")
    (root / "CNAME").write_text("cryptic.fun\n", encoding="utf-8")
    _copy_media(pair, root)

    pretty = datetime.strptime(pair.date, "%Y-%m-%d").strftime("%A %-d %B %Y")
    articles = "\n".join(_article(item, "media/") for item in pair.clues)
    index_body = f"""
    <p class="kicker">Two clues · {_e(pretty)}</p>
    <h1>Today’s pair.</h1>
    <p class="lede">Have a go before you tap solve. Parses follow Fifteen Squared — we speak them, we don’t nick the grid.</p>
    <section class="pair">
      {articles}
    </section>
    """
    (root / "index.html").write_text(_page(f"{BRAND} — {pretty}", index_body), encoding="utf-8")

    day_dir = root / "d" / pair.date
    day_dir.mkdir(parents=True, exist_ok=True)
    day_articles = "\n".join(_article(item, "../../media/") for item in pair.clues)
    (day_dir / "index.html").write_text(
        _page(f"{BRAND} — {pretty}", f"<h1>{_e(pretty)}</h1><section class='pair'>{day_articles}</section>", depth=2),
        encoding="utf-8",
    )

    for item in pair.clues:
        page_dir = root / "c" / item.clue.slug
        page_dir.mkdir(parents=True, exist_ok=True)
        body = f"<h1>One clue.</h1>{_article(item, '../../media/', open_by_default=False)}"
        path = page_dir / "index.html"
        path.write_text(_page(f"{item.clue.clue} — {BRAND}", body, depth=2), encoding="utf-8")
        item.site_path = f"{SITE_ORIGIN}/c/{item.clue.slug}/"

    about = """
    <h1>About.</h1>
    <p class="lede">cryptic.fun publishes two cryptic clues a day, taken from the Fifteen Squared blogs of the Independent, Guardian and Financial Times. Choose Sonia, Ryan, Libby or Thomas. YouTube gets the Short. The site is the spoiler-safe home.</p>
    <p>Answers and wordplay belong to the setters and the 15² bloggers. We rewrite for speech and always link the original post.</p>
    """
    (root / "about.html").write_text(_page(f"About — {BRAND}", about), encoding="utf-8")
    pair.site_index = f"{SITE_ORIGIN}/"
    return root
