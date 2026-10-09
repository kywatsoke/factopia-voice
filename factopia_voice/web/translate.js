"use strict";
(() => {
  const X = { ready: false, filled: false, detected: "" };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const bar = (id, pct) => { const b = $(id); b.hidden = pct === null; if (pct !== null && pct !== undefined) b.firstElementChild.style.width = pct + "%"; };
  const msg = (id, text, kind) => { const n = $(id); n.textContent = text; n.className = "hint" + (n.classList.contains("left") ? " left" : "") + (kind ? " " + kind : ""); };
  async function poll(job, onUpdate) {
    for (;;) {
      onUpdate(job);
      if (job.done) { if (job.error) throw new Error(job.error); return job.result; }
      await sleep(500);
      job = await api("/api/captions/job?id=" + job.id);
    }
  }

  function fill() {
    if (X.filled || !S || !S.languages) return;
    const opts = Object.entries(S.languages).map(([k, v]) => el("option", { value: k, textContent: v.native === v.name ? v.name : `${v.name}  ${v.native}` }));
    $("trFrom").append(...opts.map(o => o.cloneNode(true)));
    $("trTo").append(...opts.map(o => o.cloneNode(true)));
    $("trTo").value = "my";
    try { const saved = JSON.parse(localStorage.getItem("fv-tr") || "{}"); if (saved.from) $("trFrom").value = saved.from; if (saved.to) $("trTo").value = saved.to; } catch {}
    if (window.fillTranslation) window.fillTranslation();
    X.filled = true; updateStudioButton();
  }
  function remember() { try { localStorage.setItem("fv-tr", JSON.stringify({ from: $("trFrom").value, to: $("trTo").value })); } catch {} }
  function updateStudioButton() { $("trToStudio").hidden = !($("trTo").value === "en" && $("trOut").value.trim()); }

  async function refresh() {
    fill();
    let st;
    try { st = await api("/api/translate/status"); } catch (e) { st = { ready: false, step: "error", message: e.message }; }
    X.ready = st.ready;
    $("trDot").className = "dot " + (st.ready ? "ok" : "warn");
    $("trStatus").textContent = st.message;
    $("sTranslate").textContent = st.ready ? "Ready" : "Not set up yet";
    $("trSetupActions").hidden = st.ready;
    $("trGetOllama").hidden = st.step !== "install";
    $("trSetupBtn").hidden = st.step === "install" || st.step === "engine";
    $("trSetupBtn").textContent = st.step === "download" ? "Download the translation model" : st.step === "start" ? "Start Ollama" : "Set up translation";
    $("trGo").disabled = !st.ready;
    return st;
  }

  $("trSetupBtn").addEventListener("click", async () => {
    $("trSetupBtn").disabled = true;
    try {
      const job = await api("/api/translate/setup", { quality: $("sQuality").value || (S && S.profile && S.profile.translation_quality) || "standard" });
      await poll(job, j => { bar("trSetupBar", j.percent); msg("trSetupDetail", j.detail, "busy"); });
      bar("trSetupBar", null); msg("trSetupDetail", "");
    } catch (e) { bar("trSetupBar", null); msg("trSetupDetail", e.message, "err"); }
    $("trSetupBtn").disabled = false; refresh();
  });
  $("trCheck").addEventListener("click", refresh);

  async function translate() {
    const text = $("trIn").value.trim();
    if (!text) return msg("trMsg", "Type or paste some text first.", "err");
    if (!X.ready) return msg("trMsg", "Set up translation first.", "err");
    const from = $("trFrom").value, to = $("trTo").value;
    $("trGo").disabled = true; remember();
    try {
      const job = await api("/api/translate/text", { text, source: from, target: to });
      const r = await poll(job, j => { bar("trBar", j.percent); msg("trMsg", j.detail, "busy"); });
      $("trOut").value = r.text; X.detected = r.source; bar("trBar", null);
      msg("trMsg", from === "auto" ? "Translated from " + S.languages[r.source].name + "." : "");
      if (r.source === r.target) msg("trMsg", "The text is already in " + S.languages[r.target].name + ".");
    } catch (e) { bar("trBar", null); msg("trMsg", e.message, "err"); }
    $("trGo").disabled = !X.ready; updateStudioButton();
  }
  $("trGo").addEventListener("click", translate);
  $("trIn").addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.stopPropagation(); translate(); } });
  $("trTo").addEventListener("change", () => { remember(); updateStudioButton(); });
  $("trFrom").addEventListener("change", remember);
  $("trSwap").addEventListener("click", () => {
    const from = $("trFrom").value === "auto" ? (X.detected || "en") : $("trFrom").value;
    $("trFrom").value = $("trTo").value; $("trTo").value = from;
    [$("trIn").value, $("trOut").value] = [$("trOut").value, $("trIn").value]; remember(); updateStudioButton();
  });
  $("trCopy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("trOut").value); msg("trMsg", "Copied."); }
    catch { $("trOut").select(); msg("trMsg", "Press Cmd or Ctrl + C to copy."); }
  });
  $("trToStudio").addEventListener("click", () => { $("script").value = $("trOut").value; $("script").dispatchEvent(new Event("input")); show("studio"); });

  document.querySelector('#nav [data-view="translate"]').addEventListener("click", refresh);
  document.querySelector('#nav [data-view="settings"]').addEventListener("click", refresh);
  window.translationStatus = refresh;
  (async () => { for (let i = 0; i < 100 && !(S && S.languages); i++) await sleep(300); fill(); })();
})();
