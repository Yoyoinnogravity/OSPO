
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
    const onAudioError = () => {
      const sidecar = prefix + slug + ".mp3";
      if (slug && audio.dataset.sidecarTried !== "1") {
        audio.dataset.sidecarTried = "1";
        audio.src = sidecar;
        return;
      }
      audio.removeEventListener("error", onAudioError);
      const fallback = filmVoice(video);
      if (audio.dataset.voice !== fallback) applyVoice(fallback, false);
    };
    audio.addEventListener("error", onAudioError);
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
  return name.replace(/\.mp4$/i, "");
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
    ].filter(Boolean).join("\n");
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
    const body = "Please send me one cryptic clue a day.\nEmail: " + email;
    localStorage.setItem(SUBSCRIBE_KEY, "1");
    window.location.href = mailtoUrl(inbox, "Daily clue by email", body);
    lockSuggest(subscribeForm, "Thanks. Your email app should open. We’ll send one clue a day.");
  });
}

document.querySelectorAll("[data-copy]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const text = btn.getAttribute("data-copy") || "";
    const label = btn.dataset.copyLabel || "Copy";
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
    } catch (err) {
      btn.textContent = "Copy failed";
    }
    window.setTimeout(() => {
      btn.textContent = label;
    }, 1600);
  });
});

const YT_UPLOADS_KEY = "cryptic-fit-youtube-uploads";

function parseYoutubeId(text) {
  const raw = String(text || "").trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(raw)) return raw;
  try {
    const url = new URL(raw);
    const host = url.hostname.replace(/^www\./, "");
    const parts = url.pathname.split("/").filter(Boolean);
    if (host === "youtu.be" && parts[0] && /^[A-Za-z0-9_-]{11}$/.test(parts[0])) return parts[0];
    if ((host === "youtube.com" || host === "m.youtube.com") && parts[0] === "shorts" && parts[1] && /^[A-Za-z0-9_-]{11}$/.test(parts[1])) {
      return parts[1];
    }
    const watch = url.searchParams.get("v");
    if (watch && /^[A-Za-z0-9_-]{11}$/.test(watch)) return watch;
  } catch (err) {
    return "";
  }
  return "";
}

function loadLocalUploads() {
  try {
    const data = JSON.parse(localStorage.getItem(YT_UPLOADS_KEY) || "{}");
    return data && typeof data === "object" ? data : {};
  } catch (err) {
    return {};
  }
}

function saveLocalUploads(data) {
  localStorage.setItem(YT_UPLOADS_KEY, JSON.stringify(data));
}

function youtubeShortsUrl(id) {
  return "https://www.youtube.com/shorts/" + id;
}

function showPostedRow(row, id) {
  const pendingBits = row.querySelector("[data-staging-pending]");
  const postedBits = row.querySelector("[data-staging-posted]");
  const link = row.querySelector("[data-shorts-link]");
  if (pendingBits) pendingBits.hidden = true;
  if (postedBits) postedBits.hidden = false;
  if (link && id) {
    link.href = youtubeShortsUrl(id);
    link.textContent = "Open on YouTube";
  }
  row.dataset.youtubeId = id || "";
  const list = document.getElementById("on-youtube-list");
  if (list && row.parentElement && row.parentElement.id !== "on-youtube-list") {
    list.appendChild(row);
  }
  const empty = document.querySelector("[data-on-youtube-empty]");
  if (empty) empty.hidden = Boolean(list && list.querySelector("[data-staging-row]"));
}

function applyStagingMarks() {
  const local = loadLocalUploads();
  document.querySelectorAll("[data-staging-row]").forEach((row) => {
    const slug = row.dataset.slug;
    const rec = slug ? local[slug] : null;
    const id = (rec && rec.youtube_id) || row.dataset.youtubeId || "";
    if (id) showPostedRow(row, id);
  });
  const list = document.getElementById("on-youtube-list");
  const empty = document.querySelector("[data-on-youtube-empty]");
  if (empty) empty.hidden = Boolean(list && list.querySelector("[data-staging-row]"));
}

document.querySelectorAll("[data-mark-uploaded]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const slug = form.dataset.slug;
    const input = form.querySelector("input[name='url']");
    const status = form.querySelector("[data-mark-status]");
    const id = parseYoutubeId(input ? input.value : "");
    if (!slug || !id) {
      if (status) status.textContent = "Paste a YouTube Shorts or watch URL.";
      return;
    }
    const local = loadLocalUploads();
    local[slug] = {
      youtube_id: id,
      url: youtubeShortsUrl(id),
      uploaded_at: new Date().toISOString().slice(0, 10),
    };
    saveLocalUploads(local);
    const row = form.closest("[data-staging-row]");
    if (row) showPostedRow(row, id);
    if (status) status.textContent = "Saved in this browser. Tell us the URL and we will persist it on the site.";
  });
});
applyStagingMarks();
