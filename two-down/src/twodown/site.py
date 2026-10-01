from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import NamedTuple

from bs4 import BeautifulSoup
from PIL import Image

from twodown.ads import ads_enabled, ads_txt, adsense_client, adsense_slot
from twodown.banner import write_site_croc, write_youtube_picture
from twodown.config import BRAND, BRAND_LINE, CREDIT_LINE, CREDIT_WHO, DEFAULT_VOICE_ALIAS, SITE_HOST, SITE_ORIGIN, SITE_ROOT, SPONSOR_EMAIL, SUGGEST_EMAIL, TAGLINE, VOICE_LABELS, VOICES, follow_profiles
from twodown.models import DailyPair, SpokenClue
from twodown.render import opening_frame_poster, write_share_card, write_thumbnail
from twodown.scenes import DEFAULT_SCENE, get_scene, list_scenes
from twodown.seo import (
    FAVICON_SVG,
    PageSeo,
    SHARE_IMAGE,
    article_ld,
    clue_description,
    clue_share_title,
    collect_sitemap_urls,
    dumps_ld,
    gsc_verification,
    homepage_description,
    item_list_ld,
    robots_txt,
    rss_xml,
    sitemap_xml,
    website_ld,
)

CSS = """
:root {
  --news: #f3ead6;
  --ink: #1a1510;
  --crimson: #b81c29;
  --muted: #5c4e40;
  --cream: #fcf7ec;
  --rule: rgba(26, 21, 16, 0.14);
}
* { box-sizing: border-box; }
html { background: #120f0c; }
body {
  margin: 0;
  color: var(--ink);
  font-family: "Liberation Serif", "Georgia", serif;
  min-height: 100vh;
}
body.scene-newsprint {
  background:
    linear-gradient(transparent 53px, rgba(184,28,41,0.06) 54px),
    linear-gradient(90deg, transparent 53px, rgba(26,21,16,0.05) 54px),
    var(--news);
  background-size: 54px 54px, 54px 54px, auto;
}
body.scene-photo {
  color: var(--cream);
  background-color: #120f0c;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
}
body.scene-photo::before {
  content: "";
  position: fixed;
  inset: 0;
  background: linear-gradient(180deg, rgba(12,10,8,0.58) 0%, rgba(12,10,8,0.4) 42%, rgba(12,10,8,0.66) 100%);
  pointer-events: none;
  z-index: 0;
}
body > * { position: relative; z-index: 1; }
a { color: var(--crimson); }
body.scene-photo a { color: #e7d2d4; }
header, main, footer { width: min(1100px, calc(100% - 40px)); margin: 0 auto; }
header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px 12px;
  margin-top: 18px;
  border-bottom: 1px solid var(--rule);
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  box-shadow: 0 8px 24px rgba(8,6,4,0.1);
}
header a { color: var(--muted); }
body.scene-photo header a { color: var(--muted); }
body.scene-photo header .wordmark { color: var(--ink); }
body.scene-photo header .follow a { color: var(--ink); }
body.scene-photo header .follow a.on { color: var(--cream); }
nav a:hover { color: var(--crimson); }
.chrome-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.wordmark { display: inline-flex; align-items: center; gap: 10px; font-family: "Liberation Sans", "Helvetica Neue", sans-serif; font-weight: 700; font-size: 1.6rem; letter-spacing: 0.02em; color: var(--ink); text-decoration: none; }
.wordmark .profile { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; background: var(--news); flex: none; }
.wordmark span { color: var(--crimson); }
.channel-picture { width: 128px; height: 128px; border-radius: 50%; object-fit: cover; background: var(--news); display: block; margin: 12px 0 16px; }
.croc-hello {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  padding: 18px 22px 0 12px;
  margin: 22px 0 8px;
  border: 1px solid var(--rule);
}
.croc-hello img {
  width: 168px;
  height: auto;
  border-radius: 0;
  object-fit: contain;
  background: transparent;
  flex: none;
}
.croc-hello h1 { margin: 0 0 8px; font-size: clamp(1.35rem, 2.2vw, 1.85rem); font-weight: 400; }
.croc-hello p { margin: 0; max-width: 38rem; }
.croc-hello h1, .croc-hello p, .croc-hello .kicker { text-shadow: none; }
.croc-hello p { color: var(--muted); }
.croc-hello div { padding-bottom: 18px; }
h2.day-title { font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05; margin: 28px 0 8px; font-weight: 400; }
section.solved { margin: 12px 0 36px; }
.shelf { display: grid; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); gap: 14px; margin: 16px 0 18px; }
a.film-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  text-decoration: none;
  padding: 8px;
  border: 1px solid var(--rule);
}
body.scene-photo a.film-card,
body.scene-photo a.film-card .clue-text,
a.film-card:hover { color: var(--ink); }
a.film-card img { width: 100%; aspect-ratio: 9 / 16; object-fit: cover; background: #111; border-radius: 8px; }
a.film-card .clue-text { font-size: 0.92rem; line-height: 1.25; margin: 0; color: var(--ink); }
a.film-card .when,
body.scene-photo a.film-card .when { font-family: "Liberation Sans", sans-serif; font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); margin: 0; }
@media (max-width: 700px) {
  .croc-hello { flex-direction: column; align-items: flex-start; padding-bottom: 8px; }
  .croc-hello img { width: 132px; }
  .croc-hello div { padding-bottom: 10px; }
}
nav a { margin-left: 18px; font-family: "Liberation Sans", sans-serif; font-size: 0.9rem; text-decoration: none; color: var(--muted); }
.voices, .places, .follow { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.voices span, .places span, .follow span { font-family: "Liberation Sans", sans-serif; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-right: 4px; }
.voices button, .places button, .follow button, .follow a {
  font-family: "Liberation Sans", sans-serif;
  background: transparent;
  border: 1px solid var(--rule);
  color: var(--ink);
  padding: 6px 10px;
  cursor: pointer;
  font-size: 0.85rem;
  text-decoration: none;
}
.voices button.on, .places button.on, .follow button.on, .follow a.on { background: var(--crimson); color: var(--cream); border-color: var(--crimson); }
h1 { font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05; margin: 28px 0 8px; }
body.scene-photo h1, body.scene-photo .lede { text-shadow: 0 2px 18px rgba(0,0,0,0.55); }
.lede { font-size: 1.15rem; color: var(--muted); max-width: 40rem; }
body.scene-photo .lede { color: #eadfd0; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin: 36px 0 64px; }
@media (max-width: 800px) {
  .pair { grid-template-columns: 1fr; }
  body.scene-photo { background-attachment: scroll; }
}
article.clue {
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  border: 1px solid var(--rule);
  padding: 22px 22px 18px;
}
article.clue a { color: var(--crimson); }
.kicker { font-family: "Liberation Sans", sans-serif; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--crimson); margin: 0 0 12px; }
body.scene-photo > main > .kicker { color: #f0d8d6; }
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
/* The film is the solve. The written answer stays off the page until it ends. */
.spoiler .answer, .spoiler .parse { display: none; }
article.clue.is-solved .answer, article.clue.is-solved .parse { display: block; }
video { width: 100%; background: #111; }
video.short {
  display: block;
  width: min(100%, 22rem);
  max-height: min(72vh, 38rem);
  height: auto;
  aspect-ratio: 9 / 16;
  margin: 0 auto;
  background: #111;
  border-radius: 12px;
}
audio.parse-voice { width: 100%; margin-top: 8px; }
.answer { font-size: 2rem; color: var(--crimson); margin: 12px 0 6px; }
.parse { color: var(--muted); font-size: 0.98rem; }
.credit { font-family: "Liberation Sans", sans-serif; font-size: 0.85rem; }
.scene-credits { list-style: none; padding: 0; }
.scene-credits li { margin: 0 0 8px; }
footer {
  border-top: 1px solid var(--rule);
  padding: 24px 18px 48px;
  margin-bottom: 24px;
  color: var(--muted);
  font-family: "Liberation Sans", sans-serif;
  font-size: 0.85rem;
  background: rgba(252, 247, 236, 0.92);
}
footer a { color: var(--crimson); }
.scene-credit { margin-top: 10px; }
body.scene-photo h2 { text-shadow: 0 2px 18px rgba(0,0,0,0.55); }
.panel, aside.teaser {
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  border: 1px solid var(--rule);
  padding: 22px 22px 18px;
  margin: 0 0 36px;
  max-width: 40rem;
}
.panel a, aside.teaser a { color: var(--crimson); }
.suggest-forms { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin: 28px 0 64px; }
@media (max-width: 800px) { .suggest-forms { grid-template-columns: 1fr; } }
.suggest-form { display: flex; flex-direction: column; gap: 12px; }
.suggest-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: "Liberation Sans", sans-serif;
  font-size: 0.85rem;
  color: var(--muted);
}
.suggest-form input, .suggest-form textarea {
  font-family: "Liberation Serif", Georgia, serif;
  font-size: 1.05rem;
  color: var(--ink);
  background: var(--cream);
  border: 1px solid var(--rule);
  padding: 8px 10px;
}
.suggest-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.suggest-form button:disabled { opacity: 0.5; cursor: not-allowed; }
.suggest-status { font-family: "Liberation Sans", sans-serif; font-size: 0.9rem; color: var(--muted); margin: 0; }
a.action {
  display: inline-block;
  font-family: "Liberation Sans", sans-serif;
  background: var(--crimson);
  color: var(--cream) !important;
  border: 0;
  padding: 10px 16px;
  text-decoration: none;
  font-size: 0.95rem;
}
ul.archive { list-style: none; padding: 0; margin: 0 0 16px; }
ul.archive li { margin: 0 0 8px; }
aside.ad {
  background: rgba(252, 247, 236, 0.94);
  color: var(--ink);
  border: 1px dashed var(--rule);
  padding: 14px 16px 16px;
  margin: 0 0 36px;
  min-height: 90px;
}
.ad-label {
  font-family: "Liberation Sans", sans-serif;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 8px;
}
.rules { max-width: 40rem; }
.rules li { margin: 0 0 8px; }
"""

JS = """
const VOICE_KEY = "cryptic-fun-voice";
const SCENE_KEY = "cryptic-fun-scene";

function filmVoice(video) {
  return (video && video.dataset.voice) || "sonia";
}

function currentVoice() {
  const saved = localStorage.getItem(VOICE_KEY);
  if (saved) return saved;
  return filmVoice(document.querySelector("video.short"));
}

function currentScene() {
  return localStorage.getItem(SCENE_KEY) || document.body.dataset.defaultScene || "machu-picchu";
}

function applyVoice(alias, persist) {
  if (persist !== false) localStorage.setItem(VOICE_KEY, alias);
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
    const video = article.querySelector("video");
    if (video) video.muted = alias !== filmVoice(video);
    audio.addEventListener("error", () => {
      const fallback = filmVoice(video);
      if (audio.dataset.voice !== fallback) applyVoice(fallback, false);
    }, { once: true });
  });
}

function applyScene(slug) {
  localStorage.setItem(SCENE_KEY, slug);
  const photo = slug !== "newsprint";
  document.body.classList.toggle("scene-photo", photo);
  document.body.classList.toggle("scene-newsprint", !photo);
  document.body.dataset.scene = slug;
  if (photo) {
    const prefix = document.body.dataset.scenePrefix || "media/scenes/";
    document.body.style.backgroundImage = "url('" + prefix + slug + ".webp')";
  } else {
    document.body.style.backgroundImage = "";
  }
  document.querySelectorAll("[data-scene-btn]").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.scene === slug);
    btn.setAttribute("aria-pressed", btn.dataset.scene === slug ? "true" : "false");
  });
  const credit = document.querySelector("[data-scene-credit]");
  const button = document.querySelector('[data-scene-btn][data-scene="' + slug + '"]');
  if (credit) {
    credit.textContent = button ? (button.dataset.credit || "") : "";
  }
}

document.querySelectorAll("[data-voice-btn]").forEach((btn) => {
  btn.addEventListener("click", () => applyVoice(btn.dataset.voice));
});
document.querySelectorAll("[data-scene-btn]").forEach((btn) => {
  btn.addEventListener("click", () => applyScene(btn.dataset.scene));
});
applyVoice(currentVoice(), false);
applyScene(currentScene());

const FOLLOW_KEY = "cryptic-fun-follow";

function isFollowing() {
  return localStorage.getItem(FOLLOW_KEY) !== "0";
}

function applyFollow() {
  const on = isFollowing();
  const btn = document.querySelector("[data-follow-toggle]");
  if (!btn) return;
  btn.classList.toggle("on", on);
  btn.setAttribute("aria-pressed", on ? "true" : "false");
  btn.textContent = on ? "Following" : "Follow";
}

document.querySelectorAll("[data-follow-link]").forEach((link) => {
  link.addEventListener("click", () => localStorage.setItem(FOLLOW_KEY, "1"));
});
const followToggle = document.querySelector("[data-follow-toggle]");
if (followToggle) {
  followToggle.addEventListener("click", () => {
    if (isFollowing()) {
      localStorage.setItem(FOLLOW_KEY, "0");
      applyFollow();
      return;
    }
    localStorage.setItem(FOLLOW_KEY, "1");
    applyFollow();
    const href = followToggle.dataset.followHref;
    if (href && location.pathname.indexOf("follow.html") === -1) {
      window.location.href = href;
    }
  });
}
applyFollow();

function showWrittenAnswer(article, video) {
  if (!article || article.classList.contains("is-solved")) return;
  if (!video || !video.duration || video.currentTime < video.duration - 0.4) return;
  article.classList.add("is-solved");
}

document.querySelectorAll("button.reveal").forEach((btn) => {
  btn.addEventListener("click", () => btn.closest("article").classList.add("is-open"));
});

function playHash() {
  return (location.hash || "").replace(/^#/, "");
}

function slugFromVideo(video) {
  const src = (video && video.getAttribute("src")) || "";
  const name = src.split("/").pop() || "";
  return name.replace(/\\.mp4$/i, "");
}

function wantsPlay(article) {
  const hash = playHash();
  if (!hash) return false;
  const slug = article.dataset.slug || slugFromVideo(article.querySelector("video"));
  if (hash === "play") return true;
  return Boolean(slug && (hash === slug || hash === "play-" + slug));
}

function playFilm(article) {
  article.classList.add("is-open");
  const video = article.querySelector("video");
  if (!video) return;
  try {
    video.focus({ preventScroll: true });
  } catch (err) {
    video.focus();
  }
  video.scrollIntoView({ block: "center" });
  const start = () => {
    const attempt = video.play();
    if (attempt && attempt.catch) attempt.catch(() => {});
  };
  if (video.readyState >= 2) start();
  else video.addEventListener("loadeddata", start, { once: true });
}

function playFromHash() {
  document.querySelectorAll("article.clue").forEach((article) => {
    if (wantsPlay(article)) playFilm(article);
  });
}

playFromHash();
window.addEventListener("hashchange", playFromHash);

document.querySelectorAll("article.clue").forEach((article) => {
  const video = article.querySelector("video");
  const audio = article.querySelector("audio.parse-voice");
  if (!video || !audio) return;
  const otherVoice = () => currentVoice() !== filmVoice(video);
  const applyMute = () => {
    video.muted = otherVoice();
  };
  applyMute();
  video.addEventListener("play", () => {
    applyMute();
    if (!otherVoice()) {
      audio.pause();
      return;
    }
    audio.currentTime = video.currentTime;
    audio.play();
  });
  video.addEventListener("pause", () => audio.pause());
  video.addEventListener("seeked", () => {
    audio.currentTime = video.currentTime;
    showWrittenAnswer(article, video);
  });
  video.addEventListener("timeupdate", () => showWrittenAnswer(article, video));
  video.addEventListener("ended", () => article.classList.add("is-solved"));
});

const SUGGEST_KEY = "cryptic-fun-suggest-day";
const SUBSCRIBE_KEY = "cryptic-fun-subscribe";

function londonDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Europe/London" });
}

function lockSuggest(form, message) {
  form.querySelectorAll("input, textarea, button").forEach((el) => {
    el.disabled = true;
  });
  const status = form.querySelector("[data-suggest-status]");
  if (status) status.textContent = message;
}

function mailtoUrl(address, subject, body) {
  return "mailto:" + address + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
}

const suggestForm = document.querySelector("[data-suggest-form]");
if (suggestForm) {
  const inbox = suggestForm.dataset.inbox;
  if (localStorage.getItem(SUGGEST_KEY) === londonDate()) {
    lockSuggest(suggestForm, "You’ve already sent today’s suggestion. One homemade clue a day — see you tomorrow.");
  }
  suggestForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (localStorage.getItem(SUGGEST_KEY) === londonDate()) {
      lockSuggest(suggestForm, "You’ve already sent today’s suggestion. One homemade clue a day — see you tomorrow.");
      return;
    }
    const data = new FormData(suggestForm);
    const clue = String(data.get("clue") || "").trim();
    const answer = String(data.get("answer") || "").trim();
    const enumeration = String(data.get("enumeration") || "").trim();
    const name = String(data.get("name") || "").trim();
    const email = String(data.get("email") || "").trim();
    if (!clue || !answer) {
      const status = suggestForm.querySelector("[data-suggest-status]");
      if (status) status.textContent = "Need a clue and an answer.";
      return;
    }
    const enumBit = enumeration ? " (" + enumeration + ")" : "";
    const body = [
      "Clue: " + clue + enumBit,
      "Answer: " + answer,
      name ? "Name: " + name : "",
      email ? "Email: " + email : "",
      "Date: " + londonDate(),
    ].filter(Boolean).join("\\n");
    localStorage.setItem(SUGGEST_KEY, londonDate());
    window.location.href = mailtoUrl(inbox, "Clue suggestion · " + londonDate(), body);
    lockSuggest(suggestForm, "Thanks. Your email app should open with today’s suggestion. One a day.");
  });
}

const subscribeForm = document.querySelector("[data-subscribe-form]");
if (subscribeForm) {
  const inbox = subscribeForm.dataset.inbox;
  if (localStorage.getItem(SUBSCRIBE_KEY) === "1") {
    lockSuggest(subscribeForm, "You’re on the list for one emailed clue a day.");
  }
  subscribeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const email = String(new FormData(subscribeForm).get("email") || "").trim();
    if (!email) {
      const status = subscribeForm.querySelector("[data-suggest-status]");
      if (status) status.textContent = "Need an email address.";
      return;
    }
    const body = "Please send me one cryptic clue a day.\\nEmail: " + email;
    localStorage.setItem(SUBSCRIBE_KEY, "1");
    window.location.href = mailtoUrl(inbox, "Daily clue by email", body);
    lockSuggest(subscribeForm, "Thanks. Your email app should open. We’ll send one clue a day.");
  });
}
"""


def _voice_alias(voice: str | None) -> str:
    for alias, neural in VOICES.items():
        if voice in {alias, neural}:
            return alias
    return DEFAULT_VOICE_ALIAS


def _e(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def _voice_bar() -> str:
    buttons = []
    for alias, label in VOICE_LABELS.items():
        buttons.append(
            f'<button type="button" data-voice-btn data-voice="{_e(alias)}" aria-pressed="false">{_e(label)}</button>'
        )
    return '<div class="voices" role="group" aria-label="Choose a voice"><span>Voice</span>' + "".join(buttons) + "</div>"


def _scene_bar() -> str:
    buttons = []
    for scene in list_scenes():
        buttons.append(
            f'<button type="button" data-scene-btn data-scene="{_e(scene.slug)}" '
            f'data-credit="{_e(scene.credit_line)}" aria-pressed="false">{_e(scene.label)}</button>'
        )
    return (
        '<div class="places" role="group" aria-label="Choose a background">'
        "<span>Place</span>" + "".join(buttons) + "</div>"
    )


def _follow_bar(prefix: str) -> str:
    links = [
        f'<a href="{prefix}follow.html#email" data-follow-link>Email</a>',
        f'<a href="{prefix}feed.xml" data-follow-link>RSS</a>',
    ]
    for _slug, label, url in follow_profiles():
        links.append(f'<a href="{_e(url)}" data-follow-link rel="me noopener" target="_blank">{_e(label)}</a>')
    return (
        f'<div class="follow" role="group" aria-label="Follow {BRAND}">'
        "<span>Follow</span>"
        f'<button type="button" data-follow-toggle data-follow-href="{prefix}follow.html" aria-pressed="true">Following</button>'
        + "".join(links)
        + "</div>"
    )


def _wordmark(prefix: str) -> str:
    return (
        f'<a class="wordmark" href="{prefix}index.html">'
        f'<img class="profile" src="{prefix}assets/profile.png" width="48" height="48" alt="Cryptic Croc">'
        f"cryptic<span>.fit</span></a>"
    )


def _picture_panel(prefix: str) -> str:
    return f"""<section class="panel" id="picture">
        <h2>Profile picture.</h2>
        <img class="channel-picture" src="{prefix}assets/profile.png" width="800" height="800" alt="Cryptic Croc">
        <p>Cryptic Croc is the face of {BRAND}, beside the name on every page and on the YouTube channel. The file is a still PNG, 800×800.</p>
        <p><a class="action" href="{prefix}assets/profile.png" download="cryptic-fit-profile.png">Save the picture</a></p>
      </section>"""


def _ensure_profile(html_text: str, *, picture_panel: bool = False) -> str:
    """Put Cryptic Croc in the header of pages written before she was the mark."""
    html_text = re.sub(
        r'<link rel="icon" href="((?:\.\./)*)assets/favicon\.svg" type="image/svg\+xml">',
        '<link rel="icon" href="\\1assets/profile.png" type="image/png">\n'
        '  <link rel="apple-touch-icon" href="\\1assets/profile.png">',
        html_text,
        count=1,
    )
    if 'class="profile"' not in html_text:
        html_text = re.sub(
            r'<a class="wordmark" href="((?:\.\./)*)index\.html">cryptic<span>\.fit</span></a>',
            r'<a class="wordmark" href="\1index.html">'
            r'<img class="profile" src="\1assets/profile.png" width="48" height="48" alt="Cryptic Croc">'
            r"cryptic<span>.fit</span></a>",
            html_text,
            count=1,
        )
    if picture_panel and 'id="picture"' not in html_text:
        found = re.search(r'src="((?:\.\./)*)assets/profile\.png"', html_text)
        prefix = found.group(1) if found else ""
        html_text = html_text.replace(
            '<div class="suggest-forms">',
            '<div class="suggest-forms">\n      ' + _picture_panel(prefix),
            1,
        )
    return html_text


def _nav(prefix: str) -> str:
    return f"""
      <nav>
        <a href="{prefix}index.html">Today</a>
        <a href="{prefix}films.html">Films</a>
        <a href="{prefix}follow.html">Follow</a>
        <a href="{prefix}suggest.html">Suggest</a>
        <a href="{prefix}support.html">Support</a>
        <a href="{prefix}about.html">About</a>
      </nav>
    """


def _ads_head() -> str:
    client = adsense_client()
    if not ads_enabled() or not client:
        return ""
    return (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
        f'?client={_e(client)}" crossorigin="anonymous"></script>\n'
    )


def _ad_unit() -> str:
    client = adsense_client()
    slot = adsense_slot()
    if not client or not slot:
        return ""
    return f"""
    <aside class="ad" aria-label="Advertisement">
      <p class="ad-label">Advertisement</p>
      <ins class="adsbygoogle" style="display:block"
        data-ad-client="{_e(client)}" data-ad-slot="{_e(slot)}"
        data-ad-format="horizontal" data-full-width-responsive="true"></ins>
      <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    </aside>
    """


def _keep_free_teaser(prefix: str) -> str:
    if ads_enabled():
        return _ad_unit()
    return f"""
    <aside class="teaser">
      <p class="kicker">Keep it free</p>
      <h2>When the hits come.</h2>
      <p>A small labelled ad will sit here — never on the answer, never over the pause. Until then YouTube is the main bet, and a crossword brand can sponsor a week.</p>
      <a class="action" href="{prefix}support.html">How we pay for this</a>
    </aside>
    """


def _page(body: str, seo: PageSeo, depth: int = 0, show_ads: bool = False) -> str:
    prefix = "../" * depth
    scene_prefix = f"{prefix}media/scenes/"
    default = get_scene(DEFAULT_SCENE)
    background = default.filename or "machu-picchu.webp"
    head_ads = _ads_head() if show_ads else ""
    image = canonical_share = f"{SITE_ORIGIN}{SHARE_IMAGE}"
    verify = gsc_verification()
    verify_tag = (
        f'<meta name="google-site-verification" content="{_e(verify)}">\n' if verify else ""
    )
    ld = ""
    if seo.json_ld is not None:
        ld = f'<script type="application/ld+json">{dumps_ld(seo.json_ld)}</script>\n'
    published = ""
    if seo.published:
        published = f'<meta property="article:published_time" content="{_e(seo.published)}">\n'
    extra = "\n".join(seo.extra)
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(seo.title)}</title>
  <meta name="description" content="{_e(seo.description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{_e(seo.canonical)}">
  <link rel="alternate" hreflang="en-GB" href="{_e(seo.canonical)}">
  <link rel="alternate" hreflang="x-default" href="{_e(seo.canonical)}">
  <link rel="alternate" type="application/rss+xml" title="{_e(BRAND)}" href="{SITE_ORIGIN}/feed.xml">
  <link rel="icon" href="{prefix}assets/profile.png" type="image/png">
  <link rel="apple-touch-icon" href="{prefix}assets/profile.png">
  <meta name="theme-color" content="#b81c29">
  <meta name="color-scheme" content="light">
  <meta property="og:site_name" content="{_e(BRAND)}">
  <meta property="og:type" content="{_e(seo.og_type)}">
  <meta property="og:locale" content="en_GB">
  <meta property="og:title" content="{_e(seo.title)}">
  <meta property="og:description" content="{_e(seo.description)}">
  <meta property="og:url" content="{_e(seo.canonical)}">
  <meta property="og:image" content="{_e(image)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_e(seo.title)}">
  <meta name="twitter:description" content="{_e(seo.description)}">
  <meta name="twitter:image" content="{_e(image)}">
  {published}{verify_tag}{ld}{extra}
  <link rel="stylesheet" href="{prefix}assets/style.css">
  {head_ads}
</head>
<body class="scene-photo" data-scene="{_e(default.slug)}" data-default-scene="{_e(default.slug)}" data-scene-prefix="{_e(scene_prefix)}" style="background-image: url('{_e(scene_prefix + background)}');">
  <header>
    <div class="chrome-top">
      {_wordmark(prefix)}
      {_nav(prefix)}
    </div>
    {_voice_bar()}
    {_scene_bar()}
    {_follow_bar(prefix)}
  </header>
  <main>
    {body}
  </main>
  <footer>
    Two clues a day from the Independent, the Guardian and the Financial Times.
    Not affiliated with those papers. Pick a voice and a place.
    One homemade clue a day via <a href="{prefix}suggest.html">Suggest</a>,
    or <a href="{prefix}follow.html">follow</a> by email, RSS or YouTube.
    <a href="{prefix}support.html">Support</a> ·
    <a href="{prefix}privacy.html">Privacy</a>
    <p class="scene-credit" data-scene-credit>{_e(default.credit_line)}</p>
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def _article(
    item: SpokenClue,
    media_prefix: str,
    open_by_default: bool = False,
    show_clue_text: bool = True,
    play_anchor: bool = False,
) -> str:
    clue = item.clue
    opened = " is-open" if open_by_default else ""
    alias = _voice_alias(item.voice)
    video = ""
    if item.video_path:
        poster = ""
        if item.thumbnail_path:
            poster = f' poster="{_e(media_prefix + clue.slug + "-poster.webp")}"'
        play_id = ' id="play"' if play_anchor else ""
        video = (
            f'<video class="short" controls playsinline preload="metadata" data-voice="{_e(alias)}"{poster}{play_id} '
            f'src="{_e(media_prefix + clue.slug + ".mp4")}"></video>'
        )
    audio = (
        f'<audio class="parse-voice" controls preload="none" data-prefix="{_e(media_prefix)}" '
        f'src="{_e(media_prefix + clue.slug)}-{_e(alias)}.mp3"></audio>'
    )
    enum = f" ({_e(clue.enumeration)})" if clue.enumeration else ""
    clue_block = f'<p class="clue-text">{_e(clue.clue)}{enum}</p>' if show_clue_text else ""
    return f"""
    <article class="clue{opened}" data-slug="{_e(clue.slug)}">
      <p class="kicker">{_e(clue.paper)} {_e(clue.puzzle_id)} · {_e(clue.setter)} · {_e(clue.number)} {_e(clue.direction)} · {_e(clue.device)}</p>
      {clue_block}
      <button class="reveal" type="button">Solve</button>
      <div class="spoiler" data-nosnippet>
        {video}
        {audio}
        <p class="answer">{_e(clue.answer)}</p>
        <p class="parse">{_e(clue.parse)}</p>
        <p class="credit">Parse via <a href="{_e(clue.source_url)}">{_e(clue.blogger)}</a></p>
      </div>
    </article>
    """


def _copy_poster(src: str | Path, dest: Path) -> None:
    """Site posters are WebP. A JPEG thumbnail is converted on the way in."""
    source = Path(src)
    if not source.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == dest.resolve():
        return
    if source.suffix.lower() == ".webp":
        copy2(source, dest)
        return
    Image.open(source).convert("RGB").save(dest, "WEBP", quality=82)


def _copy_file(src: str | Path, dest: Path) -> None:
    source = Path(src)
    if not source.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == dest.resolve():
        return
    copy2(source, dest)


def _copy_scenes(dest: Path) -> None:
    folder = dest / "media" / "scenes"
    folder.mkdir(parents=True, exist_ok=True)
    for scene in list_scenes():
        if scene.path and scene.path.exists():
            _copy_file(scene.path, folder / scene.filename)


def _copy_media(pair: DailyPair, dest: Path) -> None:
    media = dest / "media"
    media.mkdir(parents=True, exist_ok=True)
    for item in pair.clues:
        if item.video_path:
            _copy_file(item.video_path, media / f"{item.clue.slug}.mp4")
        if item.thumbnail_path:
            _copy_poster(item.thumbnail_path, media / f"{item.clue.slug}-poster.webp")
        for alias, path in item.voice_paths.items():
            _copy_file(path, media / f"{item.clue.slug}-{alias}.mp3")
    _copy_scenes(dest)


def _about_credits() -> str:
    items = []
    for scene in list_scenes():
        if not scene.is_photo:
            continue
        link = scene.commons_url or "#"
        items.append(
            f'<li><a href="{_e(link)}">{_e(scene.place)}</a> — {_e(scene.photographer)}, {_e(scene.license)}</li>'
        )
    return "<ul class='scene-credits'>" + "".join(items) + "</ul>"


# Study cuts that predate the daily pages. The filename is the file in site/media/.
_LEGACY_LABELS: dict[str, tuple[str, str]] = {
    "mass-media-if-you-need.mp4": (
        "Maid struggling with a mess — newspapers etc (4,5)",
        "Financial Times 18483 · Arrietty · studio cut",
    ),
    "mass-media-ryan-clue.mp4": (
        "Maid struggling with a mess — newspapers etc (4,5)",
        "Financial Times 18483 · Arrietty · Ryan offers the picture",
    ),
    "mass-media-sonia.mp4": (
        "Maid struggling with a mess — newspapers etc (4,5)",
        "Financial Times 18483 · Arrietty · Sonia",
    ),
    "aimlessly-sonia.mp4": (
        "Sly e-mails recycled without end (9)",
        "Guardian 30115 · Brendan · Sonia",
    ),
    "smiles-kind-sonia.mp4": (
        "First in school by a long way, is visibly pleased (6)",
        "Guardian 30115 · Brendan · Sonia",
    ),
    "smiles-acted-libby.mp4": (
        "First in school by a long way, is visibly pleased (6)",
        "Guardian 30115 · Brendan · Libby",
    ),
    "smiles-warm-libby.mp4": (
        "First in school by a long way, is visibly pleased (6)",
        "Guardian 30115 · Brendan · earlier Libby",
    ),
    "smiles-next-q-libby.mp4": (
        "First in school by a long way, is visibly pleased (6)",
        "Guardian 30115 · Brendan · earlier Libby",
    ),
    "smiles-libby.mp4": (
        "First in school by a long way, is visibly pleased (6)",
        "Guardian 30115 · Brendan · earlier Libby",
    ),
    "cole-king-libby.mp4": (
        "So-called King of jazz, or another one accompanied by string trio (4)",
        "Guardian 30115 · Brendan · Libby",
    ),
    "cole-libby.mp4": (
        "So-called King of jazz, or another one accompanied by string trio (4)",
        "Guardian 30115 · Brendan · earlier Libby",
    ),
    "wellington-libby.mp4": (
        "Duke is thoroughly acquainted with good style (10)",
        "Guardian 30115 · Brendan · Libby",
    ),
    "wellington-parse.mp4": (
        "Duke is thoroughly acquainted with good style (10)",
        "Guardian 30115 · Brendan · parse take",
    ),
    "fats-libby.mp4": (
        "Refrain from eating, with final twist, such unhealthy foods (4)",
        "Guardian 30115 · Brendan · Libby",
    ),
    "rasta-libby.mp4": (
        "One emperor backing follower of another (5)",
        "Guardian 30115 · Brendan · Libby",
    ),
    "rasta-study.mp4": (
        "One emperor backing follower of another (5)",
        "Guardian 30115 · Brendan · study take",
    ),
    "rasta-source.mp4": (
        "One emperor backing follower of another (5)",
        "Guardian 30115 · Brendan · source take",
    ),
    "davis-cup-libby.mp4": (
        "Frenzied divas caught up in international court event (5,3)",
        "Guardian 30115 · Brendan · Libby",
    ),
}
_LEGACY_ORDER = list(_LEGACY_LABELS)
_CDN_MEDIA = re.compile(
    r"https://cdn\.jsdelivr\.net/gh/Yoyoinnogravity/OSPO@[^\"']+/two-down/site/(media/[^\"']+)"
)


def retarget_cdn(html_text: str, prefix: str = "") -> str:
    """Point a page at the copy of the film that ships with the site."""
    return _CDN_MEDIA.sub(lambda match: prefix + match.group(1), html_text)


def retarget_play_links(html_text: str) -> str:
    """Shelf cards and 'Open this clue' skip the Solve gate and land on the player."""
    html_text = re.sub(
        r'(<a class="film-card" href="(?:\.\./)*(?:c|d)/[^"/]+/)(?!#play")(")',
        r"\1#play\2",
        html_text,
    )
    html_text = re.sub(
        r'(<a href="(?:\.\./)*c/[^"/]+/)(?!#play")(">Open this clue</a>)',
        r"\1#play\2",
        html_text,
    )
    html_text = re.sub(
        r'(<a href="(?:\.\./)*d/[^"/]+/)(?!#play")(">Open this day</a>)',
        r"\1#play\2",
        html_text,
    )
    return html_text


def attach_play_anchor(html_text: str) -> str:
    """Give a single-clue page a #play target so a thumbnail can open the Short."""
    if 'id="play"' in html_text:
        return html_text
    return re.sub(
        r'(<video\b[^>]*\bclass="short"[^>]*)(>)',
        r'\1 id="play">',
        html_text,
        count=1,
        flags=re.I,
    )


def _ensure_films_nav(html_text: str) -> str:
    if ">Films</a>" in html_text:
        return html_text
    return re.sub(
        r'(<a href="((?:\.\./)*)index\.html">Today</a>)',
        r'\1\n        <a href="\2films.html">Films</a>',
        html_text,
        count=1,
    )


def _media_prefix(html_path: Path, root: Path) -> str:
    rel = html_path.parent.relative_to(root)
    return "../" * len(rel.parts)


def legacy_videos(root: Path) -> list[Path]:
    """Study Shorts that are not already the film on a published clue page."""
    media = root / "media"
    if not media.is_dir():
        return []
    rank = {name: index for index, name in enumerate(_LEGACY_ORDER)}
    files = [
        path
        for path in media.glob("*.mp4")
        if not (root / "c" / path.stem / "index.html").exists()
    ]
    files.sort(key=lambda path: (rank.get(path.name, 1000), path.name))
    return files


def _pretty_day(date: str) -> str:
    return datetime.strptime(date, "%Y-%m-%d").strftime("%A %-d %B %Y")


class SolvedFilm(NamedTuple):
    """One published daily clue. The written answer is never copied onto a shelf."""

    date: str
    pretty: str
    clue: str
    kicker: str
    slug: str
    video: str
    poster: str


def solved_films(root: Path, skip_date: str | None = None) -> list[SolvedFilm]:
    """Daily solves, newest first. The answer line on the day page stays out."""
    day_root = Path(root) / "d"
    if not day_root.is_dir():
        return []
    found: list[SolvedFilm] = []
    folders = [folder for folder in day_root.iterdir() if folder.is_dir() and (folder / "index.html").exists()]
    folders.sort(key=lambda folder: folder.name, reverse=True)
    for folder in folders:
        if skip_date and folder.name == skip_date:
            continue
        try:
            pretty = _pretty_day(folder.name)
        except ValueError:
            continue
        soup = BeautifulSoup((folder / "index.html").read_text(encoding="utf-8"), "lxml")
        articles = soup.select("article.clue")
        if not articles:
            for node in soup.select("p.clue-text"):
                found.append(SolvedFilm(folder.name, pretty, node.get_text(" ", strip=True), "", "", "", ""))
            continue
        for article in articles:
            clue_node = article.select_one("p.clue-text")
            clue = clue_node.get_text(" ", strip=True) if clue_node else ""
            kicker_node = article.select_one("p.kicker")
            kicker = kicker_node.get_text(" ", strip=True) if kicker_node else ""
            slug = article.get("data-slug") or ""
            video = ""
            poster = ""
            video_node = article.select_one("video")
            src = video_node.get("src", "") if video_node else ""
            name = Path(src).name
            if name.endswith(".mp4") and (Path(root) / "media" / name).is_file():
                video = name
                card = f"{Path(name).stem}-poster.webp"
                if (Path(root) / "media" / card).is_file():
                    poster = card
            found.append(SolvedFilm(folder.name, pretty, clue, kicker, slug, video, poster))
    return found


def _croc_hello(prefix: str, *, title: str, lede: str) -> str:
    return f"""
    <section class="croc-hello">
      <img class="croc-figure" src="{prefix}assets/croc.webp" width="640" height="560" alt="">
      <div>
        <p class="kicker">Cryptic Croc</p>
        <h1>{_e(title)}</h1>
        <p>{_e(lede)}</p>
      </div>
    </section>
    """


def _solved_shelf(root: Path, prefix: str = "", skip_date: str | None = None) -> str:
    cards = []
    for film in solved_films(root, skip_date=skip_date):
        href = f"{prefix}c/{film.slug}/#play" if film.slug else f"{prefix}d/{film.date}/#play"
        image = ""
        if film.poster:
            image = f'<img src="{prefix}media/{_e(film.poster)}" alt="">'
        cards.append(
            f'<a class="film-card" href="{href}">'
            f"{image}"
            f'<p class="when">{_e(film.pretty)}</p>'
            f'<p class="clue-text">{_e(film.clue)}</p>'
            f"</a>"
        )
    grid = f'<div class="shelf">{"".join(cards)}</div>' if cards else ""
    return f"""
    <section class="solved">
      <p class="kicker">Solved</p>
      <h2>Every film we have cut.</h2>
      {grid}
      <a class="action" href="{prefix}films.html">All the Shorts</a>
    </section>
    """


def _playable_daily(root: Path) -> str:
    blocks = []
    for film in solved_films(root):
        player = ""
        if film.video:
            poster_attr = f' poster="media/{_e(film.poster)}"' if film.poster else ""
            player = (
                f'<video class="short" controls playsinline preload="metadata"{poster_attr} '
                f'src="media/{_e(film.video)}"></video>'
            )
        opener = ""
        slug_attr = ""
        if film.slug:
            opener = f'<p class="credit"><a href="c/{_e(film.slug)}/#play">Open this clue</a></p>'
            slug_attr = f' data-slug="{_e(film.slug)}" id="{_e(film.slug)}"'
        elif film.date:
            opener = f'<p class="credit"><a href="d/{_e(film.date)}/#play">Open this day</a></p>'
            slug_attr = f' id="day-{_e(film.date)}"'
        blocks.append(
            f'<article class="clue"{slug_attr}>'
            f'<p class="kicker">{_e(film.pretty)}</p>'
            f'<p class="clue-text">{_e(film.clue)}</p>'
            f"{player}{opener}"
            "</article>"
        )
    if not blocks:
        return "<p>No daily pair on the site yet.</p>"
    return "<section class='pair'>" + "\n".join(blocks) + "</section>"


def earlier_days(root: Path, skip_date: str | None = None) -> list[tuple[str, str, list[str]]]:
    """Published day pages, newest first. Each item is date, pretty date, clue surfaces."""
    day_root = root / "d"
    if not day_root.is_dir():
        return []
    found: list[tuple[str, str, list[str]]] = []
    for folder in day_root.iterdir():
        page = folder / "index.html"
        if not folder.is_dir() or not page.exists():
            continue
        try:
            datetime.strptime(folder.name, "%Y-%m-%d")
        except ValueError:
            continue
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")
        clues = [node.get_text(" ", strip=True) for node in soup.select("p.clue-text")]
        found.append((folder.name, _pretty_day(folder.name), clues))
    found.sort(reverse=True)
    if skip_date:
        return [item for item in found if item[0] != skip_date]
    return found


def _legacy_article(path: Path) -> str:
    title, credit = _LEGACY_LABELS.get(path.name, (path.stem.replace("-", " "), "Study cut"))
    audio = path.with_suffix(".mp3")
    soundtrack = ""
    if audio.exists():
        soundtrack = f'<audio controls preload="none" src="media/{_e(audio.name)}"></audio>'
    poster = path.with_name(f"{path.stem}-poster.webp")
    poster_attr = f' poster="media/{_e(poster.name)}"' if poster.exists() else ""
    return (
        '<article class="clue">'
        f'<p class="kicker">{_e(credit)}</p>'
        f'<p class="clue-text">{_e(title)}</p>'
        f'<video class="short" controls playsinline preload="metadata"{poster_attr} '
        f'src="media/{_e(path.name)}"></video>'
        f"{soundtrack}"
        "</article>"
    )


def _earlier_teaser(root: Path, prefix: str = "", skip_date: str | None = None) -> str:
    return _solved_shelf(root, prefix=prefix, skip_date=skip_date)


def _films_body(root: Path) -> str:
    return f"""
    {_croc_hello("", title="Every film on cryptic.fit.", lede="Daily solves, newest first. Andrew says we are AI, then Cryptic Croc presents the clue.")}
    <h2>Daily pairs.</h2>
    {_playable_daily(root)}
    """


_STUDY_POSTER = {
    "mass-media-if-you-need": "mass-media",
    "mass-media-ryan-clue": "mass-media",
    "mass-media-sonia": "mass-media",
    "aimlessly-sonia": "aimlessly",
    "smiles-kind-sonia": "smiles",
    "smiles-acted-libby": "smiles",
    "smiles-warm-libby": "smiles",
    "smiles-next-q-libby": "smiles",
    "smiles-libby": "smiles",
    "cole-king-libby": "cole",
    "cole-libby": "cole",
    "wellington-libby": "wellington",
    "wellington-parse": "wellington",
    "fats-libby": "fats",
    "rasta-libby": "rasta",
    "rasta-study": "rasta",
    "rasta-source": "rasta",
    "davis-cup-libby": "davis-cup",
}


def clue_for_media(root: Path, stem: str):
    """Clue behind a media filename, so the poster can be drawn unsolved."""
    from twodown.pipeline import published_clue, study_clue

    found = study_clue(_STUDY_POSTER.get(stem, stem))
    if found is not None:
        return found
    try:
        return published_clue(stem, root)
    except (FileNotFoundError, ValueError):
        return None


def ensure_safe_posters(root: Path) -> None:
    """Write a spoiler-free poster beside every Short on the site."""
    media = root / "media"
    if not media.is_dir():
        return
    for video in sorted(media.glob("*.mp4")):
        dest = video.with_name(f"{video.stem}-poster.webp")
        clue = clue_for_media(root, video.stem)
        if clue is not None:
            write_thumbnail(clue, dest)
        else:
            try:
                opening_frame_poster(video, dest)
            except (OSError, RuntimeError):
                continue
        leftover = video.with_name(f"{video.stem}-poster.jpg")
        if leftover.exists():
            leftover.unlink()


def attach_video_posters(html_text: str) -> str:
    """Point each player at the unsolved poster, not a later frame of the film."""

    def _poster_for(src: str) -> str:
        return src[:-4] + "-poster.webp" if src.endswith(".mp4") else ""

    def _video(match: re.Match[str]) -> str:
        tag = re.sub(r'\s+poster="[^"]*"', "", match.group(0), count=1)
        src_match = re.search(r'\bsrc="([^"]+\.mp4)"', tag)
        if not src_match:
            return tag
        poster = _poster_for(src_match.group(1))
        if tag.endswith("/>"):
            return tag[:-2] + f' poster="{poster}"/>'
        return tag[:-1] + f' poster="{poster}">'

    html_text = re.sub(r"<video\b[^>]*>", _video, html_text, flags=re.I)

    def _source(match: re.Match[str]) -> str:
        video_open, src = match.group(1), match.group(2)
        if "poster=" in video_open:
            return match.group(0)
        poster = _poster_for(src)
        if not poster:
            return match.group(0)
        if video_open.endswith("/>"):
            return match.group(0)
        opened = video_open[:-1] + f' poster="{poster}">'
        return opened + match.group(0)[len(video_open) :]

    return re.sub(
        r'(<video\b[^>]*>)\s*<source\b[^>]*\bsrc="([^"]+\.mp4)"',
        _source,
        html_text,
        flags=re.I,
    )


def publish_films(root: Path) -> Path:
    """Write the archive and point older pages at the films that ship with the site."""
    root = Path(root)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "app.js").write_text(JS, encoding="utf-8")
    ensure_safe_posters(root)
    page = root / "films.html"
    page.write_text(
        _page(
            _films_body(root),
            PageSeo(
                title=f"Films — {BRAND}",
                description="Every cryptic.fit Short. Have a go before you tap solve.",
                path="/films.html",
                json_ld=website_ld(),
            ),
        ),
        encoding="utf-8",
    )
    index = root / "index.html"
    if index.exists():
        text = index.read_text(encoding="utf-8")
        if "All the Shorts" not in text:
            days = earlier_days(root)
            skip = days[0][0] if days else None
            teaser = _earlier_teaser(root, skip_date=skip)
            text = text.replace("<aside class=\"teaser\">", teaser + "\n    <aside class=\"teaser\">", 1)
        index.write_text(_ensure_films_nav(text), encoding="utf-8")
    for html_path in root.rglob("*.html"):
        if html_path == page:
            continue
        original = html_path.read_text(encoding="utf-8")
        updated = retarget_cdn(original, _media_prefix(html_path, root))
        updated = attach_video_posters(updated)
        updated = retarget_play_links(updated)
        if html_path.parent.parent.name == "c":
            updated = attach_play_anchor(updated)
        updated = _ensure_films_nav(updated)
        updated = _ensure_profile(updated, picture_panel=html_path.name == "follow.html")
        if updated != original:
            html_path.write_text(updated, encoding="utf-8")
    _ensure_sitemap_films(root)
    return page


def _ensure_sitemap_films(root: Path) -> None:
    path = root / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    loc = f"{SITE_ORIGIN}/films.html"
    if loc in text:
        return
    days = earlier_days(root)
    lastmod = days[0][0] if days else datetime.now().date().isoformat()
    entry = f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>\n"
    path.write_text(text.replace("</urlset>", entry + "</urlset>", 1), encoding="utf-8")


def publish_site(pair: DailyPair, dest: Path | None = None) -> Path:
    root = Path(dest or SITE_ROOT)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (root / "assets" / "app.js").write_text(JS, encoding="utf-8")
    (root / "CNAME").write_text(f"{SITE_HOST}\n", encoding="utf-8")
    (root / ".nojekyll").write_text("", encoding="utf-8")
    (root / "robots.txt").write_text(robots_txt(), encoding="utf-8")
    (root / "assets" / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    write_youtube_picture(root / "assets" / "profile.png", ring=False)
    write_site_croc(root / "assets" / "croc.webp")
    write_share_card(root / "media" / "og.webp")
    ads_path = root / "ads.txt"
    listing = ads_txt()
    if listing:
        ads_path.write_text(listing, encoding="utf-8")
    elif ads_path.exists():
        ads_path.unlink()
    _copy_media(pair, root)

    pretty = datetime.strptime(pair.date, "%Y-%m-%d").strftime("%A %-d %B %Y")
    articles = "\n".join(_article(item, "media/") for item in pair.clues)
    index_body = f"""
    {_croc_hello("", title=TAGLINE, lede="Two clues a day from the Independent, the Guardian and the Financial Times. Have a go before you tap solve.")}
    <p class="kicker">Two clues · {_e(pretty)}</p>
    <h2 class="day-title">Today’s pair.</h2>
    <p class="lede">Have a go before you tap solve. We speak the parses. We don’t nick the grid. Pick a place from the header if you’d rather solve against the Matterhorn than newsprint.</p>
    <section class="pair">
      {articles}
    </section>
    <aside class="teaser">
      <p class="kicker">Follow</p>
      <h2>Keep the pair coming.</h2>
      <p>Follow is on by default. Email one clue a day, the RSS feed, or {BRAND} on YouTube. No account on the site.</p>
      <a class="action" href="follow.html">Follow {BRAND}</a>
    </aside>
    {_earlier_teaser(root, skip_date=pair.date)}
    {_keep_free_teaser("")}
    <aside class="teaser">
      <p class="kicker">Readers</p>
      <h2>Suggest a clue.</h2>
      <p>One homemade cryptic a day, emailed to us. Or get a clue in your inbox each morning.</p>
      <a class="action" href="suggest.html">Suggest today’s clue</a>
    </aside>
    """
    (root / "index.html").write_text(
        _page(
            index_body,
            PageSeo(
                title=f"Two cryptic clues · {pretty} — {BRAND}",
                description=homepage_description(pretty),
                path="/",
                json_ld=[website_ld(), item_list_ld(pair)],
                published=pair.date,
            ),
            show_ads=True,
        ),
        encoding="utf-8",
    )

    day_dir = root / "d" / pair.date
    day_dir.mkdir(parents=True, exist_ok=True)
    day_articles = "\n".join(_article(item, "../../media/") for item in pair.clues)
    (day_dir / "index.html").write_text(
        _page(
            f"<h1>{_e(pretty)}</h1><section class='pair'>{day_articles}</section>{_keep_free_teaser('../../')}",
            PageSeo(
                title=f"Two cryptic clues · {pretty} — {BRAND}",
                description=homepage_description(pretty),
                path=f"/d/{pair.date}/",
                og_type="article",
                json_ld=item_list_ld(pair),
                published=pair.date,
            ),
            depth=2,
            show_ads=True,
        ),
        encoding="utf-8",
    )

    for item in pair.clues:
        page_dir = root / "c" / item.clue.slug
        page_dir.mkdir(parents=True, exist_ok=True)
        enum = f" ({_e(item.clue.enumeration)})" if item.clue.enumeration else ""
        body = (
            f'<p class="kicker">One clue.</p>'
            f"<h1>{_e(item.clue.clue)}{enum}</h1>"
            f"{_article(item, '../../media/', open_by_default=False, show_clue_text=False, play_anchor=True)}"
        )
        path = page_dir / "index.html"
        path.write_text(
            _page(
                body,
                PageSeo(
                    title=clue_share_title(item.clue),
                    description=clue_description(item.clue),
                    path=f"/c/{item.clue.slug}/",
                    og_type="article",
                    json_ld=article_ld(item.clue, canonical=f"{SITE_ORIGIN}/c/{item.clue.slug}/", published=pair.date),
                    published=pair.date,
                ),
                depth=2,
            ),
            encoding="utf-8",
        )
        item.site_path = f"{SITE_ORIGIN}/c/{item.clue.slug}/"

    about = f"""
    <h1>About.</h1>
    <p class="lede">{BRAND_LINE} {CREDIT_LINE} {CREDIT_WHO[:1].upper()}{CREDIT_WHO[1:]}. The only source is the Independent, the Guardian and the Financial Times. We never invent answers. Andrew invites, then Cryptic Croc presents the new films. Sonia, Libby, Ryan and Thomas stay on the voice list, and you can still pick a real place as the backdrop. The same Shorts go to YouTube, TikTok, Instagram and Facebook when those accounts are connected. The site is the spoiler-safe home.</p>
    <p>Answers and wordplay belong to the setters and the bloggers. We rewrite for speech and always link the original post.</p>
    <p>Readers can <a href="suggest.html">suggest one homemade clue a day</a>, or ask for a daily clue by email. Both land in Aled’s inbox at <a href="mailto:{_e(SUGGEST_EMAIL)}">{_e(SUGGEST_EMAIL)}</a>.</p>
    <p>When the site has readers, a small labelled ad can sit under the pair — never on the answer. How that works is on <a href="support.html">Support</a>.</p>
    <h2>Backgrounds.</h2>
    <p>Photographs are cropped to 9:16 from Wikimedia Commons. Newsprint is still there if you want the paper look.</p>
    {_about_credits()}
    {_ad_unit()}
    """
    (root / "about.html").write_text(
        _page(
            about,
            PageSeo(
                title=f"About — {BRAND}",
                description=f"{BRAND_LINE} {CREDIT_LINE} From the Independent, the Guardian and the Financial Times. We never invent answers.",
                path="/about.html",
                json_ld=website_ld(),
            ),
            show_ads=True,
        ),
        encoding="utf-8",
    )

    inbox = _e(SUGGEST_EMAIL)
    suggest = f"""
    <p class="kicker">Readers</p>
    <h1>Suggest a clue.</h1>
    <p class="lede">One homemade cryptic a day. We read them; we don’t promise to publish them. Answers stay off the public page — they go in the email.</p>
    <div class="suggest-forms">
      <section class="panel">
        <h2>Send us today’s clue.</h2>
        <p>Clue, enumeration and answer. Sends to <a href="mailto:{inbox}">{inbox}</a>.</p>
        <form class="suggest-form" data-suggest-form data-inbox="{inbox}">
          <label>The clue
            <textarea name="clue" required maxlength="280" rows="3" placeholder="Rioting led unrest in the final analysis"></textarea>
          </label>
          <div class="suggest-row">
            <label>Enumeration
              <input name="enumeration" maxlength="24" placeholder="3,6" autocomplete="off">
            </label>
            <label>Answer
              <input name="answer" required maxlength="80" placeholder="END RESULT" autocomplete="off">
            </label>
          </div>
          <label>Your name (optional)
            <input name="name" maxlength="80" autocomplete="name">
          </label>
          <label>Your email (optional, if you’d like a reply)
            <input name="email" type="email" maxlength="120" autocomplete="email">
          </label>
          <button type="submit" class="reveal">Email today’s suggestion</button>
          <p class="suggest-status" data-suggest-status></p>
        </form>
      </section>
      <section class="panel">
        <h2>Get a clue by email.</h2>
        <p>One a day, spoiler-safe: the clue only, not the answer. Ask from this form and we’ll add you.</p>
        <form class="suggest-form" data-subscribe-form data-inbox="{inbox}">
          <label>Your email
            <input name="email" type="email" required maxlength="120" autocomplete="email" placeholder="you@example.com">
          </label>
          <button type="submit" class="reveal">Send me one clue a day</button>
          <p class="suggest-status" data-suggest-status></p>
        </form>
      </section>
    </div>
    """
    (root / "suggest.html").write_text(
        _page(
            suggest,
            PageSeo(
                title=f"Suggest a clue — {BRAND}",
                description="Send one homemade cryptic a day, or ask for a daily clue by email. Answers stay off the public page.",
                path="/suggest.html",
            ),
        ),
        encoding="utf-8",
    )

    profiles = "".join(
        f'<p><a class="action" href="{_e(url)}" data-follow-link rel="me noopener" target="_blank">Follow on {_e(label)}</a></p>'
        for _slug, label, url in follow_profiles()
    )
    follow_page = f"""
    <p class="kicker">Follow</p>
    <h1>Follow {BRAND}.</h1>
    <p class="lede">Following is the default. Stay for the daily pair, or take it with you by email, RSS or YouTube. There is no account to create on the site.</p>
    <div class="suggest-forms">
      {_picture_panel("")}
      <section class="panel" id="email">
        <h2>Email, one clue a day.</h2>
        <p>Spoiler-safe: the clue only. Sends to <a href="mailto:{inbox}">{inbox}</a>.</p>
        <form class="suggest-form" data-subscribe-form data-inbox="{inbox}">
          <label>Your email
            <input name="email" type="email" required maxlength="120" autocomplete="email" placeholder="you@example.com">
          </label>
          <button type="submit" class="reveal">Send me one clue a day</button>
          <p class="suggest-status" data-suggest-status></p>
        </form>
      </section>
      <section class="panel">
        <h2>RSS and YouTube.</h2>
        <p>The feed is the pair, not the answers. {BRAND} Shorts go to YouTube when that channel is connected.</p>
        <p><a class="action" href="feed.xml" data-follow-link>Subscribe to RSS</a></p>
        {profiles}
      </section>
    </div>
    """
    (root / "follow.html").write_text(
        _page(
            follow_page,
            PageSeo(
                title=f"Follow — {BRAND}",
                description=f"Follow {BRAND} by email, RSS or YouTube. {BRAND_LINE} {CREDIT_LINE} No account required.",
                path="/follow.html",
            ),
        ),
        encoding="utf-8",
    )

    sponsor = _e(SPONSOR_EMAIL)
    support = f"""
    <p class="kicker">Money</p>
    <h1>Keep the clues free.</h1>
    <p class="lede">When people show up, we can pay for {BRAND} without a paywall. Ads are one way. They are not switched on yet. They will never sit on the answer or talk over the seven-second pause.</p>
    <section class="panel">
      <h2>1. YouTube is the main bet.</h2>
      <p>The two daily Shorts on the <strong>{BRAND}</strong> channel are where hits turn into money. YouTube’s Partner Program pays a share of ads in the Shorts feed once the channel has 1,000 subscribers and 10 million Shorts views in 90 days (or 4,000 hours of long-form watch time). Until then YouTube may still run ads — we just don’t get a cut.</p>
      <p>At 500 subscribers, Super Thanks and memberships can open first. Same Google AdSense account can later cover the website.</p>
    </section>
    <section class="panel">
      <h2>2. A small ad on the site.</h2>
      <p>Once <a href="{SITE_ORIGIN}/">{BRAND}</a> is live, Google AdSense can put one labelled display unit <em>under</em> the pair. Manual placement only — no Auto ads, no ads inside Solve, no ads on a single-clue spoiler page. The UK needs a consent banner before any ad cookie is set; ads stay off until that is in place.</p>
      <p>AdSense can refuse sites that mostly reprint other people’s puzzles. We write original pages (this one, About, how the agent works) and we credit all — the setter, the paper, and the photograph. Approval is not guaranteed. If Google says no, we skip site ads and lean on YouTube and sponsors.</p>
    </section>
    <section class="panel">
      <h2>3. Sponsor a week.</h2>
      <p>A crossword dictionary, a pen, a bookshop: one quiet line under the pair for seven days. Better money per reader than a banner, and it stays on-brand. Write to <a href="mailto:{sponsor}?subject=Sponsor%20{BRAND}">{sponsor}</a>.</p>
    </section>
    <h2>Rules.</h2>
    <ul class="rules">
      <li>The clue stays free. Solve stays a tap, not a paywall.</li>
      <li>No ad on the answer, the parse, or the spoken pause.</li>
      <li>Parses still come only from the original posts.</li>
      <li>TikTok, Instagram and Facebook are for reach. Their creator funds are extra if they ever qualify — not the plan.</li>
    </ul>
    {_ad_unit()}
    """
    (root / "support.html").write_text(
        _page(
            support,
            PageSeo(
                title=f"Support — {BRAND}",
                description=f"How {BRAND} stays free: YouTube Shorts, a labelled site ad under the pair, and crossword sponsors. Ads never sit on the answer.",
                path="/support.html",
            ),
            show_ads=True,
        ),
        encoding="utf-8",
    )

    privacy = f"""
    <h1>Privacy.</h1>
    <p class="lede">{BRAND} is a static site. We do not run an account system or a tracker of our own.</p>
    <section class="panel">
      <h2>What stays in your browser.</h2>
      <p>Voice, place, and “already suggested today” are saved in localStorage on your device so the header remembers your picks. That data does not come to us.</p>
      <p>Suggest-a-clue and the daily-clue signup open your email app. If you send a message, it arrives at <a href="mailto:{_e(SUGGEST_EMAIL)}">{_e(SUGGEST_EMAIL)}</a>.</p>
    </section>
    <section class="panel">
      <h2>Ads.</h2>
      <p>Display ads are off until we have a live domain, an approved AdSense account, and — for UK visitors — a consent banner. When they are on, Google may set cookies to choose and measure those ads. We will not load the ad script until that is true. See <a href="support.html">Support</a>.</p>
    </section>
    <p>Questions: <a href="mailto:{_e(SUGGEST_EMAIL)}">{_e(SUGGEST_EMAIL)}</a>.</p>
    """
    (root / "privacy.html").write_text(
        _page(
            privacy,
            PageSeo(
                title=f"Privacy — {BRAND}",
                description=f"{BRAND} is a static site. Voice and place stay in your browser. Display ads stay off until a UK consent banner is in place.",
                path="/privacy.html",
            ),
        ),
        encoding="utf-8",
    )
    publish_films(root)
    (root / "feed.xml").write_text(rss_xml(pair, pretty), encoding="utf-8")
    (root / "sitemap.xml").write_text(sitemap_xml(collect_sitemap_urls(root, pair)), encoding="utf-8")
    pair.site_index = f"{SITE_ORIGIN}/"
    return root
