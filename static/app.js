const $ = (id) => document.getElementById(id);
const form = $("composer");
const textInput = $("text");
const imageInput = $("image");
const thread = $("thread");
const messages = $("messages");

const PLACEHOLDERS = {
  classic: "Write your text. Each sentence becomes one scene.",
  story: "Describe the story, e.g. The panda walks through the jungle, talking to a friend on a phone.",
};
const HINTS = {
  classic: "Each sentence becomes a scene with voice-over.",
  story: "AI writes a 30-second story from your idea, and 2 scenes are animated by AI (about 5–8 minutes).",
};
const HISTORY_KEY = "videos";
const PLAY_ICON = '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/></svg>';

let photo = null; // the attached File

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// ---------- theme ----------

function updateThemeLabel() {
  $("theme-label").textContent = document.documentElement.dataset.theme === "dark" ? "Light mode" : "Dark mode";
}
$("theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch {}
  updateThemeLabel();
});
updateThemeLabel();

// ---------- sidebar (drawer on small screens) ----------

const closeNav = () => document.body.classList.remove("nav-open");
$("menu").addEventListener("click", () => document.body.classList.toggle("nav-open"));
$("scrim").addEventListener("click", closeNav);

// ---------- server status ----------

fetch("/api/health")
  .then((r) => r.json())
  .then((health) => {
    for (const span of $("status").querySelectorAll("[data-key]")) {
      span.classList.add(health[span.dataset.key] ? "ok" : "bad");
    }
    const warnings = [];
    if (!health.ffmpeg) warnings.push("FFmpeg is not installed on the server, so videos can't be made yet.");
    if (!health.voice) {
      form.voice.checked = false;
      form.voice.disabled = true;
      warnings.push("No voice model found, so voice-over is off.");
    }
    if (!health.story) {
      const storyInput = document.querySelector('input[name="mode"][value="story"]');
      storyInput.disabled = true;
      $("story-mode-label").title = "AI story mode needs Ollama running (see README.md).";
      if (storyInput.checked) setMode("classic");
    }
    if (warnings.length) {
      $("setup-warning").textContent = warnings.join(" ");
      $("setup-warning").hidden = false;
    }
  })
  .catch(() => {});

// ---------- mode ----------

const currentMode = () => document.querySelector('input[name="mode"]:checked').value;
function setMode(mode) {
  const input = document.querySelector(`input[name="mode"][value="${mode}"]`);
  if (input.disabled) return;
  input.checked = true;
  applyMode();
}
function applyMode() {
  const mode = currentMode();
  textInput.placeholder = PLACEHOLDERS[mode];
  $("mode-hint").textContent = HINTS[mode];
}
document.querySelectorAll('input[name="mode"]').forEach((i) => i.addEventListener("change", applyMode));
applyMode();

// ---------- suggestions ----------

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    setMode(button.dataset.mode);
    textInput.value = button.dataset.text;
    onTextChange();
    textInput.focus();
    if (!photo) nudgeAttach();
  });
});

// ---------- photo: pick, drop anywhere, or paste ----------

function setPhoto(file) {
  if (!file || !file.type.startsWith("image/")) return;
  photo = file;
  $("preview").src = URL.createObjectURL(file);
  $("attachment").hidden = false;
  $("attach").classList.add("has-photo");
  hideFormError();
}
function clearPhoto() {
  photo = null;
  imageInput.value = "";
  $("attachment").hidden = true;
  $("attach").classList.remove("has-photo");
}
function nudgeAttach() {
  const attach = $("attach");
  attach.classList.remove("nudge");
  void attach.offsetWidth; // restart the animation
  attach.classList.add("nudge");
}
imageInput.addEventListener("change", () => setPhoto(imageInput.files[0]));
$("remove-photo").addEventListener("click", clearPhoto);

let dragDepth = 0;
const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
window.addEventListener("dragenter", (e) => {
  if (!hasFiles(e)) return;
  dragDepth++;
  $("drop-overlay").hidden = false;
});
window.addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) $("drop-overlay").hidden = true;
});
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  $("drop-overlay").hidden = true;
  setPhoto(e.dataTransfer.files[0]);
});
textInput.addEventListener("paste", (e) => {
  const file = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (file) {
    e.preventDefault();
    setPhoto(file);
  }
});

// ---------- text box ----------

function onTextChange() {
  textInput.style.height = "auto";
  textInput.style.height = `${Math.min(textInput.scrollHeight, 220)}px`;
  const length = textInput.value.length;
  $("count").textContent = length > 1500 ? `${length} / 2000` : "";
  $("send").disabled = !textInput.value.trim();
}
textInput.addEventListener("input", onTextChange);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    if (!$("send").disabled) form.requestSubmit();
  }
});

function showFormError(message) {
  $("form-error").textContent = message;
  $("form-error").hidden = false;
}
function hideFormError() { $("form-error").hidden = true; }

// ---------- thread ----------

function showWelcome(show) { $("welcome").hidden = !show; }
function scrollToEnd() { requestAnimationFrame(() => { thread.scrollTop = thread.scrollHeight; }); }

function describe(item) {
  const parts = [item.story ? "AI story" : "Classic", item.ratio, `${item.quality}p`];
  if (!item.voice) parts.push("no voice");
  return parts.join(" · ");
}

function addUserMessage(item, imageUrl) {
  const msg = el("div", "msg user");
  const bubble = el("div", "bubble");
  if (imageUrl) {
    const img = el("img");
    img.src = imageUrl;
    img.alt = "Your photo";
    bubble.append(img);
  }
  bubble.append(el("p", null, item.text), el("div", "meta", describe(item)));
  msg.append(bubble);
  messages.append(msg);
}

function addBotMessage() {
  const msg = el("div", "msg bot working");
  const avatar = el("div", "avatar");
  avatar.innerHTML = PLAY_ICON;
  const body = el("div", "bot-body");
  const bar = el("div", "bar");
  const fill = el("div", "bar-fill");
  const step = el("p", "step", "Uploading…");
  bar.append(fill);
  body.append(bar, step);
  msg.append(avatar, body);
  messages.append(msg);
  scrollToEnd();

  return {
    update(progress, text) {
      fill.style.width = `${Math.max(2, progress)}%`;
      step.textContent = `${text} · ${progress}%`;
    },
    done(url, notes = []) {
      msg.classList.remove("working");
      body.replaceChildren();
      body.append(el("p", "done-text", "Your video is ready."));
      const video = el("video");
      video.src = url;
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      body.append(video);
      if (notes.length) body.append(el("p", "warning notes", notes.join(" ")));
      const actions = el("div", "bot-actions");
      const download = el("a", "pill-btn primary", "Download MP4");
      download.href = url;
      download.download = "";
      const open = el("a", "pill-btn", "Open in new tab");
      open.href = url;
      open.target = "_blank";
      open.rel = "noopener";
      const another = el("button", "pill-btn", "Make another");
      another.type = "button";
      another.addEventListener("click", () => textInput.focus());
      actions.append(download, open, another);
      body.append(actions);
      video.addEventListener("loadedmetadata", scrollToEnd, { once: true });
      scrollToEnd();
    },
    fail(message) {
      msg.classList.remove("working");
      msg.classList.add("failed");
      body.replaceChildren(el("p", null, message));
      scrollToEnd();
    },
  };
}

// ---------- history (kept in this browser only) ----------

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch { return []; }
}
function saveHistory(item) {
  const list = [item, ...loadHistory().filter((h) => h.url !== item.url)].slice(0, 30);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(list)); } catch {}
  renderHistory();
}
function renderHistory() {
  const list = $("history");
  list.replaceChildren();
  for (const item of loadHistory()) {
    const button = el("button");
    button.type = "button";
    button.title = item.text;
    button.append(el("span", "h-title", item.text), el("span", "h-meta", describe(item)));
    button.addEventListener("click", () => {
      messages.replaceChildren();
      showWelcome(false);
      addUserMessage(item, null);
      addBotMessage().done(item.url);
      closeNav();
    });
    const li = el("li");
    li.append(button);
    list.append(li);
  }
}
renderHistory();

$("new-video").addEventListener("click", () => {
  messages.replaceChildren();
  showWelcome(true);
  closeNav();
  textInput.focus();
});

// ---------- generate ----------

async function readError(res) {
  try {
    const data = await res.json();
    return typeof data.detail === "string" ? data.detail : "Please check your inputs.";
  } catch {
    return `Server error (${res.status}).`;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideFormError();
  const text = textInput.value.trim();
  if (!text) return;
  if (!photo) {
    nudgeAttach();
    return showFormError("Attach a photo first: click Photo, drop one anywhere on the page, or paste it.");
  }

  const item = {
    text,
    ratio: form.ratio.value,
    quality: form.quality.value,
    style: form.style.value,
    voice: form.voice.checked,
    story: currentMode() === "story",
  };
  const data = new FormData();
  data.append("image", photo);
  for (const [key, value] of Object.entries(item)) data.append(key, String(value));

  showWelcome(false);
  addUserMessage(item, $("preview").src);
  const bot = addBotMessage();
  textInput.value = "";
  onTextChange();

  try {
    const res = await fetch("/api/generate", { method: "POST", body: data });
    if (!res.ok) throw new Error(await readError(res));
    const { job_id } = await res.json();
    poll(job_id, bot, item);
  } catch (err) {
    bot.fail(err.message || "Could not reach the server.");
  }
});

async function poll(jobId, bot, item) {
  try {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) throw new Error(await readError(res));
    const job = await res.json();
    if (job.status === "error") throw new Error(job.error || "Video generation failed.");
    if (job.status === "done") {
      bot.done(job.video_url, job.notes);
      saveHistory({ ...item, url: job.video_url, date: Date.now() });
      return;
    }
    bot.update(job.progress, job.step);
    setTimeout(() => poll(jobId, bot, item), 1000);
  } catch (err) {
    bot.fail(err.message);
  }
}
