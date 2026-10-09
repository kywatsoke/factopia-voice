"use strict";
const $ = id => document.getElementById(id);
const el = (tag, props = {}, kids = []) => {
  const n = Object.assign(document.createElement(tag), props);
  for (const k of [].concat(kids)) n.append(k);
  return n;
};
let S = null;            // last state from the server
let ready = false;
let saveTimer = null;

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Something went wrong.");
  return d;
}
const draft = {
  get() { try { return localStorage.getItem("fv-draft") || ""; } catch { return ""; } },
  set(v) { try { localStorage.setItem("fv-draft", v); } catch {} },
};

/* ---------- navigation ---------- */
function show(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === "view-" + view));
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
}
$("nav").addEventListener("click", e => { const b = e.target.closest("button"); if (b) show(b.dataset.view); });

/* ---------- script stats ---------- */
const PAUSE = /\[\s*pause(?:\s+(\d+(?:\.\d+)?))?\s*s?\s*\]/gi;
function measure() {
  const raw = $("script").value, pause = +$("pause").value, speed = +$("speed").value;
  let pauses = 0;
  const blocks = raw.trim().split(/\n[ \t]*\n+/).filter(b => b.trim());
  pauses += Math.max(0, blocks.length - 1) * pause;
  for (const m of raw.matchAll(PAUSE)) pauses += m[1] ? Math.min(5, +m[1]) : pause;
  const words = (raw.replace(PAUSE, " ").match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu) || []).length;
  const wps = (S && S.profile.wps) || 2.6, max = (S && S.profile.max_seconds) || 50;
  const secs = words ? words / (wps * speed) + pauses : 0;
  $("words").textContent = words;
  $("secs").textContent = Math.round(secs);
  const ratio = secs / max, meter = $("meterFill").parentElement;
  $("meterFill").style.width = Math.min(100, ratio * 100) + "%";
  meter.classList.toggle("near", ratio > 0.85 && ratio <= 1);
  meter.classList.toggle("over", ratio > 1);
  $("overNote").textContent = ratio > 1 ? "over by " + Math.ceil(secs - max) + "s" : "";
  $("speedOut").textContent = speed.toFixed(2) + "x";
  $("pauseOut").textContent = pause.toFixed(2) + "s";
}
$("script").addEventListener("input", () => { measure(); draft.set($("script").value); });

/* ---------- controls ---------- */
function format() { return document.querySelector("#format .on").dataset.v; }
function setFormat(v) { document.querySelectorAll("#format button").forEach(b => b.classList.toggle("on", b.dataset.v === v)); }
function saveProfile() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      S.profile = await api("/api/profile", { speed: +$("speed").value, pause: +$("pause").value,
        format: format(), max_seconds: +$("sMax").value || S.profile.max_seconds });
      $("maxLabel").textContent = S.profile.max_seconds; measure();
    } catch {}
  }, 350);
}
for (const id of ["speed", "pause"]) $(id).addEventListener("input", () => { measure(); saveProfile(); });
$("format").addEventListener("click", e => { const b = e.target.closest("button"); if (b) { setFormat(b.dataset.v); saveProfile(); } });
$("sMax").addEventListener("change", saveProfile);

/* ---------- generate ---------- */
function status(text, kind) { const s = $("status"); s.textContent = text; s.className = "hint" + (kind ? " " + kind : ""); }
async function generate() {
  if (!ready || $("go").disabled) return;
  if (!$("script").value.trim()) { status("Type or paste a script first.", "err"); $("script").focus(); return; }
  $("go").disabled = true; $("go").textContent = "Generating";
  status("Recording the narration", "busy");
  try {
    const clip = await api("/api/generate", { text: $("script").value, speed: +$("speed").value,
      pause: +$("pause").value, format: format() });
    showResult(clip, true);
    status("Done in " + clip.took + " seconds.");
    await refresh();
  } catch (e) { status(e.message, "err"); }
  $("go").disabled = false; $("go").textContent = "Generate voiceover";
}
$("go").addEventListener("click", generate);
document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") generate(); });

const audioUrl = c => "/audio/" + encodeURIComponent(c.file);
const native = () => !!(S && S.shell === "native");
const revealLabel = () => (S && S.platform === "darwin") ? "Show in Finder" : "Show in folder";
const reveal = file => api("/api/reveal", { file }).catch(e => status(e.message, "err"));
let lastClip = null;
function showResult(clip, play) {
  lastClip = clip;
  $("result").hidden = false;
  $("resTitle").textContent = clip.title;
  $("resMeta").textContent = clip.seconds + " sec  ·  " + clip.format.toUpperCase() + "  ·  " + clip.voice + " " + (+clip.speed).toFixed(2) + "x";
  $("resAudio").src = audioUrl(clip);
  $("resDownload").href = audioUrl(clip) + "?download=1";
  $("resDownload").download = clip.file;
  $("resDownload").hidden = native();             // in the app window the file is already in your folder
  $("resFolder").textContent = revealLabel();
  $("resFolder").classList.toggle("primary", native());
  if (play) { stopPlayer(); $("resAudio").play().catch(() => {}); }
}
const openFolder = (what = "output") => api("/api/open", { what }).catch(() => {});
$("resFolder").addEventListener("click", () => lastClip && reveal(lastClip.file));
for (const id of ["libFolder", "sOpen"]) $(id).addEventListener("click", () => openFolder("output"));

/* ---------- shared small player ---------- */
const player = $("player");
let playingBtn = null;
function stopPlayer() { player.pause(); if (playingBtn) { playingBtn.classList.remove("on"); playingBtn.textContent = "▶"; playingBtn = null; } }
player.addEventListener("ended", stopPlayer);
function toggle(btn, url) {
  const same = playingBtn === btn;
  stopPlayer(); $("resAudio").pause();
  if (same) return;
  player.src = url; player.play().catch(() => {});
  playingBtn = btn; btn.classList.add("on"); btn.textContent = "■";
}
async function speak(text, btn) {
  if (!ready || !text.trim()) return;
  const label = btn.textContent; btn.disabled = true; btn.textContent = "…";
  try { const p = await api("/api/preview", { text }); stopPlayer(); player.src = p.url; await player.play(); }
  catch (e) { status(e.message, "err"); }
  btn.disabled = false; btn.textContent = label;
}
$("vPreview").addEventListener("click", e => speak("Here is a fact that sounds made up, but is completely true.", e.currentTarget));

/* ---------- library ---------- */
function renderLibrary() {
  const box = $("libList"); box.replaceChildren();
  $("libCount").textContent = S.library.length || "";
  if (!S.library.length) { box.append(el("div", { className: "empty", textContent: "No clips yet. Your voiceovers will appear here." })); return; }
  for (const c of S.library) {
    const play = el("button", { className: "play", textContent: "▶", title: "Play" });
    play.addEventListener("click", () => toggle(play, audioUrl(c)));
    const reuse = el("button", { className: "btn ghost", textContent: "Reuse script" });
    reuse.addEventListener("click", () => { $("script").value = c.script; draft.set(c.script); measure(); show("studio"); $("script").focus(); });
    const dl = native()
      ? Object.assign(el("button", { className: "btn ghost", textContent: revealLabel() }), { onclick: () => reveal(c.file) })
      : el("a", { className: "btn ghost", textContent: "Download", href: audioUrl(c) + "?download=1", download: c.file });
    const cap = el("button", { className: "btn ghost", textContent: "Captions" });
    cap.addEventListener("click", async () => { cap.disabled = true; try { stopPlayer(); await window.captionClip(c.id); } catch (e) { cap.textContent = e.message; } cap.disabled = false; });
    const del = el("button", { className: "btn ghost", textContent: "Delete" });
    del.addEventListener("click", async () => {
      if (del.dataset.sure !== "1") { del.dataset.sure = "1"; del.textContent = "Really delete?"; del.classList.add("danger");
        setTimeout(() => { del.dataset.sure = ""; del.textContent = "Delete"; del.classList.remove("danger"); }, 3000); return; }
      stopPlayer(); S.library = await api("/api/library/delete", { id: c.id }); renderLibrary();
    });
    box.append(el("div", { className: "item" }, [play,
      el("div", {}, [el("div", { className: "item-title", textContent: c.title }),
        el("div", { className: "item-sub", textContent: `${c.created}  ·  ${c.seconds} sec  ·  ${c.words} words  ·  ${c.format.toUpperCase()}` })]),
      el("div", { className: "item-actions" }, [reuse, cap, dl, del])]));
  }
}

/* ---------- pronunciation ---------- */
function renderWords() {
  const box = $("wordList"); box.replaceChildren();
  $("wordCount").textContent = S.dictionary.length || "";
  if (!S.dictionary.length) { box.append(el("div", { className: "empty", textContent: "No fixes yet. When the voice says a word wrong, add it above." })); return; }
  S.dictionary.forEach((w, i) => {
    const hear = el("button", { className: "btn ghost", textContent: "Listen" });
    hear.addEventListener("click", () => speak(w.say, hear));
    const del = el("button", { className: "btn ghost", textContent: "Remove" });
    del.addEventListener("click", async () => { S.dictionary = await api("/api/dictionary", { entries: S.dictionary.filter((_, j) => j !== i) }); renderWords(); });
    box.append(el("div", { className: "item" }, [el("div", { className: "avatar", textContent: w.word[0].toUpperCase() }),
      el("div", {}, [el("div", { className: "item-title" }, [w.word, el("span", { className: "arrow", textContent: "→" }), w.say])]),
      el("div", { className: "item-actions" }, [hear, del])]));
  });
}
$("wTest").addEventListener("click", e => speak($("wSay").value || $("wWord").value, e.currentTarget));
$("wordForm").addEventListener("submit", async e => {
  e.preventDefault();
  const word = $("wWord").value.trim(), say = $("wSay").value.trim();
  if (!word || !say) return;
  const rest = S.dictionary.filter(w => w.word.toLowerCase() !== word.toLowerCase());
  S.dictionary = await api("/api/dictionary", { entries: [{ word, say }, ...rest] });
  $("wWord").value = $("wSay").value = ""; renderWords(); $("wWord").focus();
});

/* ---------- settings ---------- */
$("sQuit").addEventListener("click", async () => {
  await api("/api/quit", {}).catch(() => {});
  ready = false; $("setup").hidden = false; $("setupBar").parentElement.hidden = true; $("setupNote").hidden = true;
  $("setupTitle").textContent = "Factopia Voice has stopped"; $("setupText").textContent = "You can close this window.";
});
setInterval(() => { fetch("/api/alive", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {}); }, 10000);

/* ---------- state ---------- */
function paint(first) {
  const p = S.profile, v = S.voice;
  if (v) {
    $("vName").textContent = v.name; $("vAvatar").textContent = v.name[0];
    $("vSub").textContent = v.language_name + (v.description ? " · " + v.description : "");
    $("sVoice").textContent = `${v.name}, ${v.language_name}`;
  }
  if (S.engine) $("sEngine").textContent = `${S.engine.name} (${S.engine.license} licence), runs offline on this computer`;
  $("sFolder").textContent = S.folder;
  $("sVersion").textContent = S.version;
  $("maxLabel").textContent = p.max_seconds;
  if (first) {
    $("speed").value = p.speed; $("pause").value = p.pause; setFormat(p.format); $("sMax").value = p.max_seconds;
    $("script").value = draft.get();
    if (S.library.length) showResult(S.library[0], false);
  }
  renderLibrary(); renderWords(); measure();
}
async function refresh() { S = await api("/api/state"); paint(false); }

async function boot() {
  let first = true;
  for (;;) {
    try {
      S = await api("/api/state");
      if (S.welcome && window.welcome) { $("setup").hidden = true; await window.welcome(); $("setup").hidden = false; continue; }
      const st = S.status, bar = $("setupBar").parentElement;
      if (st.phase === "ready") {
        ready = true; $("setup").hidden = true; $("dot").className = "dot ok"; $("readyText").textContent = "Voice ready";
        paint(first);
        if (window.checkUpdate) window.checkUpdate(false);
        return;
      }
      if (st.phase === "error") {
        $("setupTitle").textContent = "The voice could not start"; $("setupText").textContent = st.detail;
        bar.hidden = true; $("setupRetryRow").hidden = false;
        $("setupNote").textContent = "Check the internet connection and press Try again. The download continues where it stopped.";
        $("dot").className = "dot bad"; return;
      }
      $("setupRetryRow").hidden = true; bar.hidden = false; $("setupTitle").textContent = "Getting the voice ready";
      $("setupText").textContent = st.detail || "Starting up";
      bar.classList.toggle("wait", st.phase !== "downloading");
      if (st.phase === "downloading") $("setupBar").style.width = st.percent + "%";
    } catch { $("setupText").textContent = "Waiting for Factopia Voice to start"; }
    await new Promise(r => setTimeout(r, 700));
  }
}
$("setupRetry").addEventListener("click", async () => {
  $("setupRetryRow").hidden = true; $("setupText").textContent = "Trying again";
  try { await api("/api/voice/retry", {}); } catch {}
  boot();
});
$("setupLogs").addEventListener("click", () => api("/api/open", { what: "logs" }).catch(() => {}));
boot();
