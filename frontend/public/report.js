(function () {
  const btn = document.getElementById("gen-report");
  if (!btn) return;

  const el = id => document.getElementById(id);

  function fillList(ul, items) {
    ul.textContent = "";
    items.forEach(text => {
      const li = document.createElement("li");
      li.textContent = text;
      ul.appendChild(li);
    });
  }

  function render(r) {
    el("report-body").hidden = false;
    el("r-observed").textContent = r.observed_pattern;
    fillList(el("r-evidence"), r.supporting_evidence.map(e => `${e.evidence_id}: ${e.statement}`));
    fillList(el("r-hypotheses"), r.hypotheses.map(h => `${h.explanation} Check: ${h.what_would_distinguish_it}`));
    fillList(el("r-checks"), r.recommended_checks);
    fillList(el("r-limits"), r.limitations);
  }

  btn.addEventListener("click", async () => {
    const status = el("report-status");
    const started = Date.now();
    btn.disabled = true;
    status.className = "muted";
    status.textContent = "Generating report...";
    const timer = setInterval(() => {
      status.textContent = `Generating report... ${Math.round((Date.now() - started) / 1000)}s`;
    }, 1000);

    try {
      const res = await fetch("/api/reports", { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(body.detail || body));
      render(body.report);
      status.textContent = `Saved to Firestore. Document ID: ${body.id}`;
    } catch (err) {
      status.className = "error";
      status.textContent = `Not saved. ${err.message}`;
    } finally {
      clearInterval(timer);
      btn.disabled = false;
    }
  });
})();
