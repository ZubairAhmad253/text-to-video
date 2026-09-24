const $ = (id) => document.getElementById(id);
const form = $("form");
const imageInput = $("image");
const drop = $("drop");
const textInput = $("text");

// Light / dark theme toggle (the initial theme is set in index.html)
$("theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch {}
});

// Warn if FFmpeg or the voice model is missing on the server.
fetch("/api/health")
  .then((r) => r.json())
  .then((health) => {
    const messages = [];
    if (!health.ffmpeg) messages.push("FFmpeg is not installed on the server, so videos can't be created yet.");
    if (!health.voice) {
      messages.push("No voice model found, so voice-over is turned off.");
      form.voice.checked = false;
      form.voice.disabled = true;
    }
    if (!health.story) {
      form.story.disabled = true;
      $("story").parentElement.title = "Story mode needs Ollama running (see README.md).";
      messages.push("Ollama is not running, so AI story mode is turned off.");
    }
    if (messages.length) {
      $("setup-warning").textContent = messages.join(" ");
      $("setup-warning").hidden = false;
    }
  })
  .catch(() => {});

// Photo picker + drag and drop
function showPreview(file) {
  if (!file) return;
  $("preview").src = URL.createObjectURL(file);
  $("preview").hidden = false;
  $("drop-hint").hidden = true;
}
imageInput.addEventListener("change", () => showPreview(imageInput.files[0]));
["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) {
    imageInput.files = e.dataTransfer.files;
    showPreview(imageInput.files[0]);
  }
});

textInput.addEventListener("input", () => { $("count").textContent = textInput.value.length; });

const defaultPlaceholder = textInput.placeholder;
$("story").addEventListener("change", () => {
  textInput.placeholder = $("story").checked
    ? "Describe the story, e.g. The panda walks through the jungle, talking to a friend on a mobile phone."
    : defaultPlaceholder;
});

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = false;
}

function setBusy(busy) {
  $("submit").disabled = busy;
  $("submit").textContent = busy ? "Generating…" : "Generate video";
  $("progress").hidden = !busy;
  if (busy) {
    $("bar-fill").style.width = "0%";
    $("step-text").textContent = "Uploading…";
  }
}

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
  $("error").hidden = true;
  if (!imageInput.files[0]) return showError("Please choose a photo.");
  if (!textInput.value.trim()) return showError("Please write some text.");

  const data = new FormData(form);
  data.set("voice", form.voice.checked ? "true" : "false");
  data.set("story", form.story.checked ? "true" : "false");

  setBusy(true);
  try {
    const res = await fetch("/api/generate", { method: "POST", body: data });
    if (!res.ok) throw new Error(await readError(res));
    const { job_id } = await res.json();
    poll(job_id);
  } catch (err) {
    showError(err.message || "Could not reach the server.");
    setBusy(false);
  }
});

async function poll(jobId) {
  try {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) throw new Error(await readError(res));
    const job = await res.json();

    if (job.status === "error") throw new Error(job.error || "Video generation failed.");
    if (job.status === "done") return showResult(job.video_url, job.notes);

    $("bar-fill").style.width = `${job.progress}%`;
    $("step-text").textContent = `${job.step} · ${job.progress}%`;
    setTimeout(() => poll(jobId), 1000);
  } catch (err) {
    showError(err.message);
    setBusy(false);
  }
}

function showResult(url, notes = []) {
  setBusy(false);
  $("notes").textContent = notes.join(" ");
  $("notes").hidden = !notes.length;
  form.hidden = true;
  $("video").src = url;
  $("download").href = url;
  $("result").hidden = false;
}

$("again").addEventListener("click", () => {
  $("result").hidden = true;
  $("video").removeAttribute("src");
  form.hidden = false;
});
