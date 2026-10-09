"use strict";
(() => {
  const C = { p: null, sel: 0, fonts: null, saveTimer: 0, prevTimer: 0, prevUrl: "", audio: new Audio(), stopAt: 0, dirty: false };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const fmt = s => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
  const bar = (id, pct) => { const b = $(id); b.hidden = pct === null; if (pct !== null) b.firstElementChild.style.width = pct + "%"; };
  const say = (id, text, kind) => { const n = $(id); n.textContent = text; n.className = "hint" + (n.classList.contains("left") ? " left" : "") + (kind ? " " + kind : ""); };

  async function pollJob(job, onUpdate) {
    for (;;) {
      onUpdate(job);
      if (job.done) { if (job.error) throw new Error(job.error); return job.result; }
      await sleep(600);
      job = await api("/api/captions/job?id=" + job.id);
    }
  }

  /* ---------- project list ---------- */
  async function loadList() {
    const data = await api("/api/captions"), box = $("capProjects");
    box.replaceChildren();
    if (!data.projects.length) { box.append(el("div", { className: "empty", textContent: "No captions yet. Import a file above, or use Captions on a clip in the Library." })); return; }
    for (const p of data.projects) {
      const open = el("button", { className: "btn ghost", textContent: "Open" });
      open.addEventListener("click", () => openProject(p.id));
      const del = el("button", { className: "btn ghost", textContent: "Delete" });
      del.addEventListener("click", async () => {
        if (del.dataset.sure !== "1") { del.dataset.sure = "1"; del.textContent = "Really delete?"; del.classList.add("danger");
          setTimeout(() => { del.dataset.sure = ""; del.textContent = "Delete"; del.classList.remove("danger"); }, 3000); return; }
        await api("/api/captions/delete", { id: p.id }); loadList();
      });
      box.append(el("div", { className: "item" }, [
        el("div", { className: "avatar", textContent: p.has_video ? "▶" : "♪" }),
        el("div", {}, [el("div", { className: "item-title", textContent: p.name }),
          el("div", { className: "item-sub", textContent: `${p.updated}  ·  ${fmt(p.duration)}  ·  ${p.lines ? p.lines + " lines" : "not read yet"}` })]),
        el("div", { className: "item-actions" }, [open, del])]));
    }
  }
  function showList() { C.audio.pause(); $("capEditor").hidden = true; $("capList").hidden = false; loadList().catch(() => {}); }

  /* ---------- import ---------- */
  async function importSrt(file, projectId) {
    const headers = { "X-File-Name": encodeURIComponent(file.name) };
    if (projectId) headers["X-Project"] = projectId;
    const r = await fetch("/api/captions/import-srt", { method: "POST", headers, body: file });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || "That subtitle file could not be read.");
    return data;
  }
  function importFile(file) {
    if (!file) return;
    if (/\.srt$/i.test(file.name)) {
      say("capImportStatus", "Reading " + file.name, "busy");
      importSrt(file).then(p => { say("capImportStatus", ""); $("capFile").value = ""; openProject(p.id); })
        .catch(e => { say("capImportStatus", e.message, "err"); $("capFile").value = ""; });
      return;
    }
    say("capImportStatus", "Copying " + file.name, "busy"); bar("capUploadBar", 0); $("capChoose").disabled = true;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/captions/import");
    xhr.setRequestHeader("X-File-Name", encodeURIComponent(file.name));
    xhr.upload.onprogress = e => { if (e.lengthComputable) bar("capUploadBar", Math.round(e.loaded * 100 / e.total)); };
    const finish = () => { bar("capUploadBar", null); $("capChoose").disabled = false; $("capFile").value = ""; };
    xhr.onload = () => {
      finish();
      let data = {}; try { data = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status !== 200) return say("capImportStatus", data.error || "The file could not be imported.", "err");
      say("capImportStatus", ""); openProject(data.id);
    };
    xhr.onerror = () => { finish(); say("capImportStatus", "The file could not be imported.", "err"); };
    xhr.send(file);
  }
  $("capChoose").addEventListener("click", () => $("capFile").click());
  $("capFile").addEventListener("change", e => importFile(e.target.files[0]));
  const drop = $("capDrop");
  for (const ev of ["dragenter", "dragover"]) drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); });
  for (const ev of ["dragleave", "drop"]) drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); });
  drop.addEventListener("drop", e => importFile(e.dataTransfer.files[0]));

  /* ---------- editor ---------- */
  async function openProject(id) {
    C.p = await api("/api/captions/project?id=" + id); C.sel = 0; C.dirty = false;
    if (!C.fonts) {
      const f = await api("/api/captions/fonts"); C.fonts = f;
      $("stFont").replaceChildren(...f.fonts.map(x => el("option", { value: x.id, textContent: x.label })));
    }
    if (!C.p.style.font) C.p.style.font = C.fonts.default;
    if (!$("capLang").options.length && S && S.languages) {
      for (const [k, v] of Object.entries(S.languages)) {
        $("capLang").append(el("option", { value: k, textContent: v.name }));
        $("capTarget").append(el("option", { value: k, textContent: v.native === v.name ? v.name : `${v.name}  ${v.native}` }));
      }
    }
    say("capTrStatus", ""); bar("capTrBar", null);
    show("captions"); $("capList").hidden = true; $("capEditor").hidden = false; $("capResult").hidden = true;
    say("capExportStatus", ""); say("capJobStatus", ""); bar("capJobBar", null); bar("capExportBar", null);
    paint();
  }
  function paint() {
    const p = C.p;
    $("capName").textContent = p.name;
    $("capMeta").textContent = (p.has_video ? `Video, ${p.width} x ${p.height}` : "Sound only") + `, ${fmt(p.duration)} long`;
    const has = p.lines.length > 0;
    $("capStart").hidden = has; $("capLinesCard").hidden = !has;
    $("capScript").value = p.script || "";
    $("capExportVideo").hidden = !p.has_video;
    $("capLang").value = p.language || "en";
    for (const o of $("capTarget").options) o.hidden = o.value === (p.language || "en");
    if ($("capTarget").value === (p.language || "en")) $("capTarget").value = [...$("capTarget").options].find(o => !o.hidden).value;
    for (const id of ["capLength", "capLengthLabel", "capRedo"]) $(id).hidden = !p.has_words;
    document.querySelectorAll("#capLength button").forEach(b => b.classList.toggle("on", b.dataset.v === p.length));
    const s = p.style;
    $("stFont").value = s.font; $("stSize").value = s.size; $("stColor").value = s.color; $("stOutline").value = s.outline;
    $("stOutlineColor").value = s.outline_color; $("stBox").checked = s.box; $("stBoxColor").value = s.box_color;
    $("stBoxOpacity").value = s.box_opacity; $("stPosition").value = s.position; $("stWidth").value = s.width; $("stUpper").checked = s.uppercase;
    labels(); renderLines(); preview();
  }
  function labels() {
    const s = C.p.style;
    $("stSizeOut").textContent = s.size; $("stOutlineOut").textContent = s.outline ? s.outline : "off";
    $("stBoxOpacityOut").textContent = s.box_opacity + "%"; $("stPositionOut").textContent = s.position + "% down"; $("stWidthOut").textContent = s.width + "%";
  }

  function select(i, row) {
    C.sel = i;
    document.querySelectorAll("#capLines .cline").forEach(r => r.classList.remove("sel"));
    (row || $("capLines").children[i])?.classList.add("sel");
    preview();
  }
  function renderLines(focus) {
    const box = $("capLines"); box.replaceChildren();
    C.p.lines.forEach((line, i) => {
      const play = el("button", { className: "play", textContent: "▶", title: "Play this line" });
      const start = el("input", { type: "number", step: "0.05", min: "0", value: line.start.toFixed(2), title: "Starts at (seconds)" });
      const end = el("input", { type: "number", step: "0.05", min: "0", value: line.end.toFixed(2), title: "Ends at (seconds)" });
      const text = el("input", { type: "text", value: line.text, maxLength: 400 });
      const split = el("button", { textContent: "Split", title: "Split at the cursor" });
      const merge = el("button", { textContent: "Join", title: "Join with the next line" });
      const del = el("button", { textContent: "✕", title: "Delete this line" });
      play.hidden = C.p.has_audio === false;
      const row = el("div", { className: "cline" + (i === C.sel ? " sel" : "") }, [play, start, end, text, el("div", { className: "acts" }, [split, merge, del])]);
      play.addEventListener("click", () => { select(i, row); playLine(i); });
      for (const input of [start, end, text]) input.addEventListener("focus", () => { if (C.sel !== i) select(i, row); });
      start.addEventListener("change", () => { line.start = Math.max(0, +start.value || 0); changed(); });
      end.addEventListener("change", () => { line.end = Math.max(line.start + 0.1, +end.value || 0); end.value = line.end.toFixed(2); changed(); });
      text.addEventListener("input", () => { line.text = text.value; changed(); });
      split.addEventListener("click", () => {
        if (line.text.length < 2) return;
        let at = text.selectionStart; if (!at || at >= line.text.length) at = line.text.indexOf(" ", Math.floor(line.text.length / 2) - 1);
        if (at <= 0) at = line.text.indexOf(" ");
        if (at <= 0) at = Math.floor(line.text.length / 2);
        const a = line.text.slice(0, at).trim(), b = line.text.slice(at).trim(); if (!a || !b) return;
        const mid = +(line.start + (line.end - line.start) * a.length / (a.length + b.length)).toFixed(2);
        C.p.lines.splice(i, 1, { start: line.start, end: mid, text: a }, { start: mid, end: line.end, text: b });
        changed(); renderLines();
      });
      merge.addEventListener("click", () => {
        const next = C.p.lines[i + 1]; if (!next) return;
        C.p.lines.splice(i, 2, { start: line.start, end: next.end, text: line.text + " " + next.text }); changed(); renderLines();
      });
      del.addEventListener("click", () => { C.p.lines.splice(i, 1); C.sel = Math.min(C.sel, C.p.lines.length - 1); changed(); if (!C.p.lines.length) paint(); else renderLines(); });
      box.append(row);
    });
    if (focus !== undefined) box.children[focus]?.querySelector("input[type=text]")?.focus();
  }
  $("capAdd").addEventListener("click", () => {
    const last = C.p.lines[C.p.lines.length - 1], start = last ? last.end : 0;
    C.p.lines.push({ start, end: Math.min(C.p.duration || start + 2, start + 2), text: "New line" });
    C.sel = C.p.lines.length - 1; changed(); renderLines(C.sel);
  });

  /* ---------- saving ---------- */
  function changed() { C.dirty = true; say("capSaved", "Saving"); clearTimeout(C.saveTimer); C.saveTimer = setTimeout(save, 600); preview(); }
  async function save() {
    clearTimeout(C.saveTimer);
    if (!C.p || !C.dirty) return;
    C.dirty = false;
    try { await api("/api/captions/save", { id: C.p.id, lines: C.p.lines, style: C.p.style }); say("capSaved", "Saved"); }
    catch (e) { C.dirty = true; say("capSaved", e.message, "err"); }
  }

  /* ---------- style ---------- */
  const styleInputs = { stFont: ["font", "value"], stSize: ["size", "num"], stColor: ["color", "value"], stOutline: ["outline", "num"],
    stOutlineColor: ["outline_color", "value"], stBox: ["box", "checked"], stBoxColor: ["box_color", "value"], stBoxOpacity: ["box_opacity", "num"],
    stPosition: ["position", "num"], stWidth: ["width", "num"], stUpper: ["uppercase", "checked"] };
  for (const [id, [key, kind]] of Object.entries(styleInputs)) {
    $(id).addEventListener("input", () => {
      C.p.style[key] = kind === "num" ? +$(id).value : kind === "checked" ? $(id).checked : $(id).value;
      if (key === "box_color" || key === "box_opacity") { C.p.style.box = true; $("stBox").checked = true; }
      labels(); changed();
    });
  }

  /* ---------- preview and playback ---------- */
  function preview() {
    clearTimeout(C.prevTimer);
    C.prevTimer = setTimeout(async () => {
      if (!C.p) return;
      const line = C.p.lines[C.sel], id = C.p.id;
      const body = { id, style: C.p.style, text: line ? line.text : "Your captions will look like this", t: line ? (line.start + line.end) / 2 : 0 };
      try {
        const r = await fetch("/api/captions/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        if (!C.p || C.p.id !== id) return;
        if (!r.ok) { const e = await r.json().catch(() => ({})); if (e.error) say("capExportStatus", e.error, "err"); return; }
        const url = URL.createObjectURL(await r.blob());
        $("capPreview").src = url; if (C.prevUrl) URL.revokeObjectURL(C.prevUrl); C.prevUrl = url;
      } catch {}
    }, 220);
  }
  C.audio.addEventListener("timeupdate", () => { if (C.stopAt && C.audio.currentTime >= C.stopAt) { C.audio.pause(); C.stopAt = 0; } });
  function playLine(i) {
    const line = C.p.lines[i], src = "/captions/audio/" + C.p.id;
    if (!C.audio.src.endsWith(src)) C.audio.src = src;
    C.audio.currentTime = line.start; C.stopAt = line.end; C.audio.play().catch(() => {});
  }

  /* ---------- reading the speech ---------- */
  async function transcribe() {
    const btn = $("capTranscribe"); btn.disabled = true; $("capRedo").disabled = true;
    try {
      const job = await api("/api/captions/transcribe", { id: C.p.id, script: $("capScript").value, length: C.p.length });
      await pollJob(job, j => { bar("capJobBar", j.percent); say("capJobStatus", j.detail + (j.percent ? " " + j.percent + "%" : ""), "busy"); });
      bar("capJobBar", null); say("capJobStatus", "");
      C.p = await api("/api/captions/project?id=" + C.p.id); C.sel = 0; paint();
    } catch (e) { bar("capJobBar", null); say("capJobStatus", e.message, "err"); }
    btn.disabled = false; $("capRedo").disabled = false;
  }
  $("capTranscribe").addEventListener("click", transcribe);
  $("capRedo").addEventListener("click", () => {
    const b = $("capRedo");
    if (b.dataset.sure !== "1") { b.dataset.sure = "1"; b.textContent = "Replace my edits?"; setTimeout(() => { b.dataset.sure = ""; b.textContent = "Read speech again"; }, 3000); return; }
    b.dataset.sure = ""; b.textContent = "Read speech again";
    C.p.lines = []; $("capStart").hidden = false; $("capLinesCard").hidden = true; $("capScript").value = C.p.script || "";
  });
  $("capLength").addEventListener("click", async e => {
    const b = e.target.closest("button"); if (!b || b.dataset.v === C.p.length) return;
    if (C.dirty && b.dataset.sure !== "1") { b.dataset.sure = "1"; const t = b.textContent; b.textContent = "Replace edits?"; setTimeout(() => { b.dataset.sure = ""; b.textContent = t; }, 3000); return; }
    clearTimeout(C.saveTimer); C.dirty = false;
    try { C.p = await api("/api/captions/regroup", { id: C.p.id, length: b.dataset.v }); C.sel = 0; paint(); say("capSaved", ""); }
    catch (err) { say("capSaved", err.message, "err"); }
    document.querySelectorAll("#capLength button").forEach(x => { x.textContent = { short: "Short", medium: "Medium", long: "Sentences" }[x.dataset.v]; x.dataset.sure = ""; });
  });

  $("capLoadSrt").addEventListener("click", () => $("capSrtFile").click());
  $("capSrtFile").addEventListener("change", async e => {
    const f = e.target.files[0]; if (!f) return;
    try { const p = await importSrt(f, C.p.id); C.p = p; C.sel = 0; paint(); }
    catch (err) { say("capJobStatus", err.message, "err"); }
    $("capSrtFile").value = "";
  });
  $("capLang").addEventListener("change", async () => {
    clearTimeout(C.saveTimer);
    try { await api("/api/captions/save", { id: C.p.id, lines: C.p.lines, language: $("capLang").value });
      C.p = await api("/api/captions/project?id=" + C.p.id); paint(); say("capSaved", "Language set"); }
    catch (e) { say("capSaved", e.message, "err"); }
  });

  /* ---------- translation ---------- */
  $("capTranslate").addEventListener("click", async () => {
    const btn = $("capTranslate"); btn.disabled = true;
    try {
      C.dirty = true; await save();
      const job = await api("/api/captions/translate", { id: C.p.id, target: $("capTarget").value });
      const r = await pollJob(job, j => { bar("capTrBar", j.percent); say("capTrStatus", j.detail, "busy"); });
      bar("capTrBar", null); say("capTrStatus", "");
      await openProject(r.id);
      say("capTrStatus", `Translated ${r.sentences} sentences into ${r.lines} lines. This is the new copy.`);
    } catch (e) {
      bar("capTrBar", null); say("capTrStatus", e.message, "err");
      if (/Set up translation/.test(e.message) && window.translationStatus) window.translationStatus();
    }
    btn.disabled = false;
  });

  /* ---------- export ---------- */
  let lastExport = null;
  function showResult(r, meta) {
    const url = "/audio/" + encodeURIComponent(r.file);
    lastExport = r.file;
    $("capResult").hidden = false; $("capResultName").textContent = r.file; $("capResultMeta").textContent = meta;
    $("capResultDownload").href = url + "?download=1"; $("capResultDownload").download = r.file;
    $("capResultDownload").hidden = native();
    $("capResultFolder").textContent = revealLabel();
    $("capResultFolder").classList.toggle("primary", native());
  }
  $("capResultFolder").addEventListener("click", () => lastExport && reveal(lastExport));
  $("capExportSrt").addEventListener("click", async () => {
    try { C.dirty = true; await save(); const r = await api("/api/captions/export", { id: C.p.id, kind: "srt" });
      showResult(r, C.p.lines.length + " lines"); say("capExportStatus", "Subtitle file saved."); }
    catch (e) { say("capExportStatus", e.message, "err"); }
  });
  $("capExportVideo").addEventListener("click", async () => {
    const btn = $("capExportVideo"); btn.disabled = true;
    try {
      C.dirty = true; await save();
      const job = await api("/api/captions/export", { id: C.p.id, kind: "video" });
      const r = await pollJob(job, j => { bar("capExportBar", j.percent); say("capExportStatus", j.detail + " " + j.percent + "%", "busy"); });
      bar("capExportBar", null); say("capExportStatus", "Video exported in " + r.took + " seconds.");
      showResult(r, r.megabytes + " MB" + (r.encoder ? "  ·  " + r.encoder : ""));
    } catch (e) { bar("capExportBar", null); say("capExportStatus", e.message, "err"); }
    btn.disabled = false;
  });

  /* ---------- wiring ---------- */
  $("capBack").addEventListener("click", async () => { await save(); showList(); });
  document.querySelector('#nav [data-view="captions"]').addEventListener("click", () => { if ($("capEditor").hidden) loadList().catch(() => {}); });
  window.captionClip = async clipId => { const p = await api("/api/captions/from-clip", { clip_id: clipId }); await openProject(p.id); };
})();
