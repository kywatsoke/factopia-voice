"use strict";
/* Settings: translation engine, performance, storage, updates, about. */
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const bar = (id, pct) => { const b = $(id); b.hidden = pct === null; if (pct !== null && pct !== undefined) b.firstElementChild.style.width = pct + "%"; };
  const say = (id, text, kind) => { const n = $(id); n.textContent = text; n.className = "hint" + (n.classList.contains("left") ? " left" : "") + (kind ? " " + kind : ""); };
  const size = n => n >= 1e9 ? (n / 1e9).toFixed(1) + " GB" : n >= 1e6 ? Math.round(n / 1e6) + " MB" : n > 0 ? Math.max(1, Math.round(n / 1e3)) + " KB" : "Empty";
  async function poll(job, onUpdate) {
    for (;;) {
      onUpdate(job);
      if (job.done) { if (job.error) throw new Error(job.error); return job.result; }
      await sleep(500);
      job = await api("/api/job?id=" + job.id);
    }
  }

  /* In the app window, links open in the normal web browser. */
  document.addEventListener("click", e => {
    const a = e.target.closest('a[target="_blank"]');
    if (a && a.href && native()) { e.preventDefault(); api("/api/open-url", { url: a.href }).catch(() => {}); }
  });

  /* ---------- translation ---------- */
  function fillTranslation() {
    if (!S || !S.translation) return;
    const t = S.translation;
    $("sTrEngine").replaceChildren(...Object.entries(t.engines).map(([k, v]) => el("option", { value: k, textContent: v })));
    $("sTrEngine").value = t.setting;
    $("sQuality").replaceChildren(...Object.entries(t.qualities).map(([k, v]) =>
      el("option", { value: k, textContent: `${k === "standard" ? "Standard" : "High quality"}: ${v.model}, ${v.size}` })));
    $("sQuality").value = (S.profile && S.profile.translation_quality) || "standard";
  }
  window.fillTranslation = fillTranslation;
  $("sTrEngine").addEventListener("change", async () => {
    try { S = await api("/api/settings", { translation_engine: $("sTrEngine").value }); } catch {}
    fillTranslation(); if (window.translationStatus) window.translationStatus();
  });
  $("sQuality").addEventListener("change", async () => {
    await api("/api/translate/setup", { quality: $("sQuality").value, check_only: true }).catch(() => {});
    if (S && S.profile) S.profile.translation_quality = $("sQuality").value;
    if (window.translationStatus) window.translationStatus();
  });

  /* ---------- performance ---------- */
  async function performance() {
    try {
      const p = await api("/api/performance");
      $("sAccel").checked = p.acceleration !== "off";
      $("pTranslation").textContent = p.translation; $("pVideo").textContent = p.video; $("pVoice").textContent = p.voice;
    } catch {}
  }
  $("sAccel").addEventListener("change", async () => {
    try { S = await api("/api/settings", { acceleration: $("sAccel").checked ? "auto" : "off" }); } catch {}
    performance();
  });

  /* ---------- storage ---------- */
  async function storage() {
    let st;
    try { st = await api("/api/storage"); } catch { return; }
    const box = $("stItems"); box.replaceChildren();
    for (const it of st.items) {
      const actions = [];
      if (it.removable && it.bytes) {
        const b = el("button", { className: "btn ghost", textContent: "Remove" });
        b.addEventListener("click", async () => {
          if (b.dataset.sure !== "1") { b.dataset.sure = "1"; b.textContent = "Really remove?"; b.classList.add("danger");
            setTimeout(() => { b.dataset.sure = ""; b.textContent = "Remove"; b.classList.remove("danger"); }, 3000); return; }
          try { await api("/api/storage/remove", { id: it.id }); say("stMsg", it.label + " removed."); } catch (e) { say("stMsg", e.message, "err"); }
          storage();
        });
        actions.push(b);
      }
      box.append(el("div", { className: "item" }, [
        el("div", {}, [el("div", { className: "item-title", textContent: it.label }), el("div", { className: "item-sub", textContent: it.note || "" })]),
        el("div", { className: "size", textContent: size(it.bytes) }),
        el("div", { className: "item-actions" }, actions)]));
    }
    $("stModels").textContent = st.models_folder;
    $("stFree").textContent = st.free_bytes == null ? "Unknown" : size(st.free_bytes);
    $("stMove").hidden = $("stImport").hidden = !native();
  }
  $("stOpenModels").addEventListener("click", () => api("/api/open", { what: "models" }).catch(() => {}));
  async function runJob(button, path, done) {
    button.disabled = true;
    try {
      const job = await api(path, {});
      if (!job.cancelled) {
        const r = await poll(job, j => { bar("stBar", j.percent); say("stMsg", j.detail, "busy"); });
        bar("stBar", null); say("stMsg", done(r));
      }
    } catch (e) { bar("stBar", null); say("stMsg", e.message, "err"); }
    button.disabled = false; storage();
  }
  $("stMove").addEventListener("click", () => runJob($("stMove"), "/api/storage/move",
    r => `Models copied to ${r.folder}. Quit and open Factopia Voice again to finish the move.`));
  $("stImport").addEventListener("click", () => runJob($("stImport"), "/api/import-earlier", r => {
    refresh().catch(() => {});
    return `Brought in ${r.clips} clips and ${r.words} pronunciation fixes from ${r.from}.`;
  }));

  /* ---------- updates ---------- */
  window.checkUpdate = async force => {
    if (!S || !S.profile) return;
    $("sUpdates").checked = S.profile.check_updates !== false;
    if (S.profile.check_updates === false && !force) { $("sUpdateText").textContent = "Automatic checks are off."; return; }
    let u;
    try { u = await api("/api/update" + (force ? "?force=1" : "")); } catch { return; }
    if (u.disabled) { $("sUpdateText").textContent = "Automatic checks are off."; return; }
    if (u.error) { $("sUpdateText").textContent = u.error; return; }
    if (u.newer) {
      $("sUpdateText").textContent = `Version ${u.latest} is available.`;
      $("updText").textContent = `Factopia Voice ${u.latest} is available.`;
      $("updGet").href = u.url; $("updBanner").hidden = false;
    } else {
      $("sUpdateText").textContent = u.latest ? `You have the latest version (${u.current}).` : "No releases found yet.";
    }
  };
  $("sUpdates").addEventListener("change", async () => {
    try { S = await api("/api/settings", { check_updates: $("sUpdates").checked }); } catch {}
    window.checkUpdate(false);
  });
  $("sCheckNow").addEventListener("click", () => window.checkUpdate(true));
  $("updLater").addEventListener("click", () => { $("updBanner").hidden = true; });

  /* ---------- about ---------- */
  let aboutDone = false;
  async function about() {
    if (aboutDone) return;
    let a;
    try { a = await api("/api/about"); } catch { return; }
    const row = (name, url, sub) => el("div", { className: "item" }, [el("div", {}, [
      el("div", { className: "item-title" }, [url ? el("a", { href: url, target: "_blank", rel: "noopener", textContent: name }) : name]),
      el("div", { className: "item-sub", textContent: sub })])]);
    $("aModels").replaceChildren(...a.models.map(m => row(m.name, m.url, `${m.role} · ${m.licence}` + (m.notice ? `. ${m.notice}.` : ""))));
    $("aSoftware").replaceChildren(...a.software.map(s => row(s.name, s.url, `${s.role} · ${s.licence}`)));
    $("aSource").href = a.source;
    aboutDone = true;
  }
  $("aLicences").addEventListener("click", () => api("/api/open", { what: "licences" }).catch(() => {}));
  $("aLogs").addEventListener("click", () => api("/api/open", { what: "logs" }).catch(() => {}));

  function open() { fillTranslation(); performance(); storage(); about(); window.checkUpdate(false); }
  document.querySelector('#nav [data-view="settings"]').addEventListener("click", open);
})();
