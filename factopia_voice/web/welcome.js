"use strict";
/* First start: the model terms, agreed once, and bringing in work from 2.x. */
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const bar = (id, pct) => { const b = $(id); b.hidden = pct === null; if (pct !== null && pct !== undefined) b.firstElementChild.style.width = pct + "%"; };
  const say = (text, kind) => { const n = $("wMsg"); n.textContent = text; n.className = "hint" + (kind ? " " + kind : ""); };

  async function poll(job, onUpdate) {
    for (;;) {
      onUpdate(job);
      if (job.done) { if (job.error) throw new Error(job.error); return job.result; }
      await sleep(500);
      job = await api("/api/job?id=" + job.id);
    }
  }

  $("wAgree").addEventListener("change", () => { $("wGo").disabled = !$("wAgree").checked; });

  $("wImport").addEventListener("click", async () => {
    $("wImport").disabled = true;
    try {
      const job = await api("/api/import-earlier", {});
      if (job.cancelled) { $("wImport").disabled = false; return; }
      const r = await poll(job, j => { bar("wBar", j.percent); say(j.detail, "busy"); });
      bar("wBar", null);
      say(`Brought in ${r.clips} clips and ${r.words} pronunciation fixes.`);
    } catch (e) { bar("wBar", null); say(e.message, "err"); }
    $("wImport").disabled = false;
  });

  /* Shows the welcome card and resolves once the terms are agreed. */
  window.welcome = () => new Promise(resolve => {
    const t = S && S.translation && S.translation.qualities && S.translation.qualities.standard;
    if (t && t.size) $("wTrSize").textContent = t.size;
    $("wImportBox").hidden = !(S && S.shell === "native" && S.layout === "installed");
    $("welcome").hidden = false;
    $("wGo").onclick = async () => {
      $("wGo").disabled = true;
      try {
        S = await api("/api/welcome/accept", {});
        $("welcome").hidden = true;
        resolve();
      } catch (e) { say(e.message, "err"); $("wGo").disabled = false; }
    };
  });
})();
