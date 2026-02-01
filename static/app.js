(() => {
  const $ = (id) => document.getElementById(id);

  // Upload UI (A)
  const dropzone = $("dropzone");
  const fileInput = $("fileInput");
  const uploadBtn = $("uploadBtn");
  const statusEl = $("status");
  const runSummary = $("runSummary");

  // Compare UI (B)
  const compareToggle = $("compareToggle");
  const dropzoneBWrap = $("dropzoneBWrap");
  const dropzoneB = $("dropzoneB");
  const fileInputB = $("fileInputB");
  const statusB = $("statusB");
  const comparePanel = $("comparePanel");

  // Results UI
  const profileLink = $("profileLink");
  const copyJsonBtn = $("copyJsonBtn");
  const reportText = $("reportText");

  // Overview UI
  const overviewText = $("overviewText");
  const overviewPill = $("overviewPill");
  const rowCount = $("rowCount");
  const colCount = $("colCount");
  const dupCount = $("dupCount");
  const insightCount = $("insightCount");
  const riskList = $("riskList");
  const oppList = $("oppList");
  const dqNotes = $("dqNotes");

  // Insights UI
  const insightCards = $("insightCards");
  const severityFilter = $("severityFilter");
  const sortFilter = $("sortFilter");

  // Charts UI
  const charts = $("charts");

  // Agent Run UI
  const stepsEl = $("steps");
  const jobBadge = $("jobBadge");
  const progBar = $("progBar");
  const appStatus = $("appStatus");

  // Footer year
  const year = $("year");
  if (year) year.textContent = new Date().getFullYear();

  // Export UI
  const dlMdBtn = $("dlMdBtn");
  const dlPdfBtn = $("dlPdfBtn");
  const shareBtn = $("shareBtn");

  let selectedFile = null;
  let selectedFileB = null;
  let evtSrc = null;
  let lastReport = null;
  let lastJobId = null;
  let jobStartMs = null;

  const STEP_ORDER = ["ingest", "profile", "ydata_profile", "plan", "run_packs", "hypotheses", "verify", "narrate"];
  const stepMap = new Map(); // step -> {el, status, detail}

  const chartFilter = $("chartFilter");
  const chartViews = new Map(); // chartId -> vega view
  chartFilter?.addEventListener("change", () => renderCharts(lastReport || {}));

  /* ---------------------------
   * Theme (dark / light)
   * --------------------------- */
  (function initTheme() {
    const btn = document.getElementById("themeToggle");
    const root = document.documentElement;

    const saved = localStorage.getItem("theme");
    const systemPrefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;

    const initialTheme = saved || (systemPrefersLight ? "light" : "dark");
    root.setAttribute("data-theme", initialTheme);

    if (btn) {
      btn.textContent = initialTheme === "light" ? "🌞 Light" : "🌙 Dark";

      btn.addEventListener("click", () => {
        const current = root.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";

        root.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
        btn.textContent = next === "light" ? "🌞 Light" : "🌙 Dark";

        // ✅ re-render charts so axis/legend colors update immediately
        if (lastReport) {
          renderCharts(lastReport);
        }
      });
    }
  })();

  /* ---------------------------
   * Vega theme (ONE function only)
   * --------------------------- */
  function applyVegaTheme(spec) {
    // Deep clone to avoid mutating backend payload
    const s = JSON.parse(JSON.stringify(spec || {}));

    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    const isLight = theme === "light";

    const axisText = isLight ? "#111827" : "#e5e7eb";
    const grid = isLight ? "#e5e7eb" : "rgba(255,255,255,0.14)";
    const viewStroke = isLight ? "rgba(17,24,39,0.18)" : "rgba(255,255,255,0.10)";

    s.background ??= "transparent";
    s.config ??= {};
    s.config.view ??= {};
    s.config.axis ??= {};
    s.config.legend ??= {};
    s.config.title ??= {};

    // Apply readable config for both themes
    s.config.view.stroke = viewStroke;

    s.config.axis.domainColor = grid;
    s.config.axis.tickColor = grid;
    s.config.axis.gridColor = grid;
    s.config.axis.labelColor = axisText;
    s.config.axis.titleColor = axisText;

    s.config.legend.labelColor = axisText;
    s.config.legend.titleColor = axisText;

    s.config.title.color = axisText;

    // IMPORTANT: do NOT override mark color if pack already set it.
    // (Your packs use #4f46e5. Keep it.)
    if (typeof s.mark === "string") {
      s.mark = { type: s.mark };
    }

    return s;
  }

  /* ---------------------------
   * Exports
   * --------------------------- */
  function enableExports(jobId) {
    lastJobId = jobId;
    if (dlMdBtn) dlMdBtn.disabled = false;
    if (dlPdfBtn) dlPdfBtn.disabled = false;
    if (shareBtn) shareBtn.disabled = false;
    if (copyJsonBtn) copyJsonBtn.disabled = false;
  }

  function disableExports() {
    lastJobId = null;
    if (dlMdBtn) dlMdBtn.disabled = true;
    if (dlPdfBtn) dlPdfBtn.disabled = true;
    if (shareBtn) shareBtn.disabled = true;
    if (copyJsonBtn) copyJsonBtn.disabled = true;
  }

  dlMdBtn?.addEventListener("click", () => {
    if (!lastJobId) return;
    window.open(`/export/${lastJobId}.md`, "_blank");
  });

  dlPdfBtn?.addEventListener("click", () => {
    if (!lastJobId) return;
    window.open(`/export/${lastJobId}.pdf`, "_blank");
  });

  shareBtn?.addEventListener("click", async () => {
    if (!lastJobId) return;
    const url = `${window.location.origin}/result/${lastJobId}`;
    try {
      await navigator.clipboard.writeText(url);
      setAppStatus("link copied", "ok");
      setTimeout(() => setAppStatus("ready", "ok"), 1200);
    } catch {
      setAppStatus("copy failed", "err");
      setTimeout(() => setAppStatus("ready", "ok"), 1200);
    }
  });

  /* ---------------------------
   * Status helpers (top-right + badge)
   * --------------------------- */
  function setRunSummary(text, kind) {
    if (!runSummary) return;
    runSummary.textContent = text || "—";
    runSummary.classList.remove("info", "warn", "err");
    if (kind) runSummary.classList.add(kind);
  }

  function fmtDuration(ms) {
    if (typeof ms !== "number" || !isFinite(ms)) return "—";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function setAppStatus(text, kind) {
    if (!appStatus) return;
    appStatus.textContent = text || "";
    appStatus.classList.remove("ok", "warn", "err", "info");
    if (kind) appStatus.classList.add(kind);
  }

  function setBadge(text) {
    if (!jobBadge) return;
    jobBadge.textContent = text;
  }

  function setProgress(pct) {
    if (progBar) progBar.style.width = `${pct}%`;
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function setStatusB(msg) {
    if (statusB) statusB.textContent = msg;
  }

  function closeEventSource() {
    if (evtSrc) {
      evtSrc.close();
      evtSrc = null;
    }
  }

  /* ---------------------------
   * Steps UI
   * --------------------------- */
  function resetSteps() {
    stepMap.clear();
    if (stepsEl) stepsEl.innerHTML = "";
    setProgress(0);
    setBadge("idle");
    STEP_ORDER.forEach((s) => addOrUpdateStep(s, "queued", "Waiting"));
  }

  function addOrUpdateStep(step, status, detail) {
    if (!stepsEl) return;

    let item = stepMap.get(step);
    if (!item) {
      const el = document.createElement("div");
      el.className = "step";
      el.innerHTML = `
        <div class="step-top">
          <div>${escapeHtml(step)}</div>
          <span class="pill">${escapeHtml(status)}</span>
        </div>
        <div class="step-detail">${escapeHtml(detail || "")}</div>
      `;
      stepsEl.appendChild(el);
      item = { el, status, detail };
      stepMap.set(step, item);
    } else {
      const pill = item.el.querySelector(".pill");
      const det = item.el.querySelector(".step-detail");
      if (pill) {
        pill.textContent = status;
        pill.className =
          "pill " +
          (status === "running"
            ? "running"
            : status === "done"
            ? "done"
            : status === "error"
            ? "error"
            : status === "skipped"
            ? "skipped"
            : "");
      }
      if (det) det.textContent = detail || "";
      item.status = status;
      item.detail = detail;
    }
  }

  /* ---------------------------
   * Tabs
   * --------------------------- */
  function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    const panels = document.querySelectorAll(".tab-panel");
    if (!tabs.length || !panels.length) return;

    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabs.forEach((b) => b.classList.remove("active"));
        panels.forEach((p) => p.classList.add("hidden"));

        btn.classList.add("active");
        const panel = $("tab-" + btn.dataset.tab);
        if (panel) panel.classList.remove("hidden");
      });
    });
  }

  initTabs();

  /* ---------------------------
   * Rendering helpers
   * --------------------------- */
  function safeText(el, text) {
    if (!el) return;
    el.textContent = text ?? "—";
  }

  function fillList(ul, items) {
    if (!ul) return;
    ul.innerHTML = "";
    const arr = Array.isArray(items) ? items : [];
    if (!arr.length) {
      const li = document.createElement("li");
      li.textContent = "—";
      ul.appendChild(li);
      return;
    }
    arr.slice(0, 6).forEach((x) => {
      const li = document.createElement("li");
      li.textContent = String(x);
      ul.appendChild(li);
    });
  }

  /* ---------------------------
   * Overview (FIXED for new snapshot_pack shape)
   * --------------------------- */
  function renderOverview(report) {
    const summary = report?.summary || {};
    const snap = report?.pack_results?.snapshot || {};

    // ✅ backward compatible: new packs use snap.summary.shape, old used snap.shape
    const shape = snap?.summary?.shape || snap?.shape || null;
    const dup = snap?.summary?.duplicate_rows ?? snap?.duplicate_rows ?? null;

    safeText(overviewText, summary.dataset_overview || "No overview available.");
    safeText(rowCount, shape?.rows ?? "—");
    safeText(colCount, shape?.cols ?? "—");
    safeText(dupCount, dup ?? "—");

    const insights = Array.isArray(report?.insights) ? report.insights : [];
    safeText(insightCount, insights.length);

    const errCount = Array.isArray(report?.errors) ? report.errors.length : 0;
    if (overviewPill) {
      overviewPill.textContent = errCount ? `warnings: ${errCount}` : "clean";
      overviewPill.className = "pill " + (errCount ? "warn" : "ok");
    }

    fillList(riskList, summary.key_risks);
    fillList(oppList, summary.key_opportunities);

    const dq = Array.isArray(report?.data_quality_notes) ? report.data_quality_notes : [];
    if (dqNotes) {
      if (!dq.length) {
        dqNotes.textContent = "—";
      } else {
        dqNotes.innerHTML = dq
          .slice(0, 4)
          .map((n) => {
            const cols = Array.isArray(n.columns) ? n.columns.join(", ") : "—";
            return `<div style="margin-bottom:10px;">
              <b>${escapeHtml(n.issue || "Issue")}</b><br/>
              <span class="muted">Columns:</span> ${escapeHtml(cols)}<br/>
              <span class="muted">Impact:</span> ${escapeHtml(n.impact || "—")}<br/>
              <span class="muted">Suggestion:</span> ${escapeHtml(n.suggestion || "—")}
            </div>`;
          })
          .join("");
      }
    }
  }

  /* ---------------------------
   * Insights
   * --------------------------- */
  function normalizeSeverity(s) {
    const v = (s || "info").toLowerCase();
    if (["risk", "warning", "opportunity", "info"].includes(v)) return v;
    return "info";
  }

  function renderInsights(report) {
    if (!insightCards) return;
    insightCards.innerHTML = "";

    let list = Array.isArray(report?.insights) ? report.insights.slice() : [];

    const sev = severityFilter ? severityFilter.value : "all";
    if (sev !== "all") list = list.filter((x) => normalizeSeverity(x.severity) === sev);

    const sort = sortFilter ? sortFilter.value : "confidence_desc";
    const confVal = (x) => (typeof x.confidence === "number" ? x.confidence : -1);

    if (sort === "confidence_desc") list.sort((a, b) => confVal(b) - confVal(a));
    if (sort === "confidence_asc") list.sort((a, b) => confVal(a) - confVal(b));
    if (sort === "severity") {
      const order = { risk: 0, warning: 1, opportunity: 2, info: 3 };
      list.sort((a, b) => (order[normalizeSeverity(a.severity)] ?? 9) - (order[normalizeSeverity(b.severity)] ?? 9));
    }

    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No insights to display for this filter.";
      insightCards.appendChild(empty);
      return;
    }

    list.forEach((ins, idx) => {
      const sev2 = normalizeSeverity(ins.severity);
      const conf = typeof ins.confidence === "number" ? ins.confidence : null;

      const card = document.createElement("div");
      card.className = "insight";

      const title = ins.title || `Insight ${idx + 1}`;
      const desc = ins.description || "";
      const action = ins.recommended_action || "—";
      const evidenceText = JSON.stringify(ins.evidence || {}, null, 2);

      card.innerHTML = `
        <div class="insight-head">
          <div>
            <div class="insight-title">${escapeHtml(title)}</div>
          </div>
          <span class="pill ${sev2}">${escapeHtml(sev2)}</span>
        </div>

        <div class="insight-desc">${escapeHtml(desc)}</div>

        <div class="meta-row">
          <div class="conf">Confidence: ${conf === null ? "—" : (conf * 100).toFixed(0) + "%"}</div>
          <div class="confbar"><div style="width:${conf === null ? 0 : clamp01(conf) * 100}%"></div></div>
        </div>

        <div class="meta-row">
          <div class="conf"><b>Action:</b> ${escapeHtml(action)}</div>
        </div>

        <div class="details">
          <details>
            <summary>Evidence</summary>
            <pre class="report" style="min-height:auto;margin-top:8px;">${escapeHtml(evidenceText)}</pre>
          </details>
        </div>
      `;

      insightCards.appendChild(card);
    });
  }

  /* ---------------------------
   * Charts
   * --------------------------- */
    function downloadBlob(filename, blob) {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 500);
    }

    function jsonToCsv(rows) {
        if (!Array.isArray(rows) || !rows.length) return "";
        const cols = Array.from(rows.reduce((s, r) => {
            Object.keys(r || {}).forEach(k => s.add(k));
            return s;
        }, new Set()));
        const esc = (v) => {
            const x = v === null || v === undefined ? "" : String(v);
            return `"${x.replaceAll('"', '""')}"`;
        };
        const head = cols.map(esc).join(",");
        const body = rows.map(r => cols.map(c => esc(r?.[c])).join(",")).join("\n");
        return head + "\n" + body;
    }

    function renderChartsEmptyState(message, details = []) {
        if (!charts) return;
        charts.innerHTML = "";

        const box = document.createElement("div");
        box.className = "chart-empty";

        box.innerHTML = `
            <div class="empty-icon">📊</div>
            <div class="empty-title">${escapeHtml(message)}</div>
            ${
            details.length
                ? `<ul class="empty-details">
                    ${details.map(d => `<li>${escapeHtml(d)}</li>`).join("")}
                </ul>`
                : ""
            }
        `;

        charts.appendChild(box);
    }

    function renderCharts(report) {
        if (!charts) return;

        charts.innerHTML = "";
        chartViews.clear();

        const themeFilter = chartFilter ? chartFilter.value : "all";
        const packResults = report?.pack_results || {};

        // Preferred path: flattened report.charts
        const flatCharts = Array.isArray(report?.charts) ? report.charts : [];

        // Fallback path: legacy pack_results[].vega_lite
        const legacyCharts = Object.entries(packResults)
            .filter(([_, pack]) => pack && pack.vega_lite)
            .map(([packName, pack]) => ({
            id: `legacy_${packName}`,
            pack: packName,
            title: packName,
            spec: pack.vega_lite,
            tags: [packName],
            }));

        const items = flatCharts.length
            ? flatCharts.map((ch) => ({
                id: ch.id || `${ch.pack || "chart"}_${Math.random().toString(16).slice(2)}`,
                pack: ch.pack || "",
                title: ch.title || ch.pack || "Chart",
                spec: ch.spec,
                tags: Array.isArray(ch.tags) ? ch.tags : [],
                priority: typeof ch.priority === "number" ? ch.priority : 50,
            }))
            : legacyCharts;

        // Collect skipped reasons (for empty state)
        const skippedReasons = [];
        Object.entries(packResults).forEach(([packName, pack]) => {
            if (pack?.skipped) skippedReasons.push(`${packName}: ${pack.skipped}`);
        });

        // ✅ If no charts exist at all
        if (!items.length) {
            if (skippedReasons.length) {
            renderChartsEmptyState("Charts were skipped for this dataset.", skippedReasons);
            } else {
            renderChartsEmptyState(
                "No charts available for this dataset.",
                ["Try uploading a dataset with numeric, categorical, or datetime columns."]
            );
            }
            return;
        }

        // Apply filter
        const filtered = items.filter((it) => {
            if (themeFilter === "all") return true;

            const tags = new Set([...(it.tags || []), it.pack]);

            if (themeFilter === "quality") return tags.has("quality") || tags.has("snapshot");
            if (themeFilter === "time") return tags.has("time") || tags.has("timeseries");

            return tags.has(themeFilter); // categorical / numeric
        });

        // ✅ If charts exist but this filter hides all of them
        if (!filtered.length) {
            renderChartsEmptyState(
            "No charts match the selected filter.",
            ["Switch filter to “All” to view available charts."]
            );
            return;
        }

        // Render charts
        filtered.forEach(({ id, title, spec }) => {
            if (!spec) return;

            const wrapper = document.createElement("div");
            wrapper.className = "chart-card";

            const head = document.createElement("div");
            head.style.display = "flex";
            head.style.alignItems = "center";
            head.style.justifyContent = "space-between";
            head.style.gap = "10px";

            const t = document.createElement("div");
            t.className = "chart-title";
            t.textContent = title;

            const actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "8px";

            const btnPng = document.createElement("button");
            btnPng.className = "btn btn-small";
            btnPng.textContent = "PNG";

            const btnCsv = document.createElement("button");
            btnCsv.className = "btn btn-small";
            btnCsv.textContent = "CSV";

            actions.appendChild(btnPng);
            actions.appendChild(btnCsv);

            head.appendChild(t);
            head.appendChild(actions);
            wrapper.appendChild(head);

            const plot = document.createElement("div");
            wrapper.appendChild(plot);
            charts.appendChild(wrapper);

            if (typeof vegaEmbed !== "function") {
            const warn = document.createElement("div");
            warn.className = "muted";
            warn.textContent = "Vega-Embed not loaded.";
            wrapper.appendChild(warn);
            return;
            }

            const themed = applyVegaTheme(spec);

            vegaEmbed(plot, themed, {
            actions: false,
            renderer: "canvas",
            width: "container",
            })
            .then((res) => {
                chartViews.set(id, res.view);

                btnPng.onclick = async () => {
                try {
                    const url = await res.view.toImageURL("png");
                    const blob = await (await fetch(url)).blob();
                    downloadBlob(`${id}.png`, blob);
                } catch (e) {
                    console.error(e);
                }
                };

                btnCsv.onclick = async () => {
                try {
                    const rows = res.view.data("source_0") || [];
                    const csv = jsonToCsv(rows);
                    downloadBlob(`${id}.csv`, new Blob([csv], { type: "text/csv;charset=utf-8" }));
                } catch (e) {
                    console.error(e);
                }
                };
            })
            .catch((err) => {
                console.error("Vega render error:", err);
                const warn = document.createElement("div");
                warn.className = "muted";
                warn.textContent = String(err);
                wrapper.appendChild(warn);
            });
        });
    }

  /* ---------------------------
   * Compare panel
   * --------------------------- */
  function renderCompare(report) {
    if (!comparePanel) return;

    const c = report?.comparison || {};
    const m = c.metrics || {};

    const missA = Array.isArray(c.top_missing_a)
      ? c.top_missing_a.map(([k, v]) => `${k}: ${v}`).join("<br/>")
      : "—";
    const missB = Array.isArray(c.top_missing_b)
      ? c.top_missing_b.map(([k, v]) => `${k}: ${v}`).join("<br/>")
      : "—";

    comparePanel.innerHTML = `
      <div class="overview-top">
        <div>
          <h3 class="h3">Comparison</h3>
          <p class="muted" style="margin:6px 0 0 0;">
            A: <b>${escapeHtml(c.dataset_a || "A")}</b> &nbsp; vs &nbsp; B: <b>${escapeHtml(c.dataset_b || "B")}</b>
          </p>
        </div>
        <span class="pill">compare</span>
      </div>

      <div class="overview-grid">
        <div class="metric"><div class="metric-value">${m.rows?.a ?? "—"}</div><div class="metric-label">Rows (A)</div></div>
        <div class="metric"><div class="metric-value">${m.rows?.b ?? "—"}</div><div class="metric-label">Rows (B)</div></div>
        <div class="metric"><div class="metric-value">${m.cols?.a ?? "—"}</div><div class="metric-label">Cols (A)</div></div>
        <div class="metric"><div class="metric-value">${m.cols?.b ?? "—"}</div><div class="metric-label">Cols (B)</div></div>
      </div>

      <div class="two-col" style="margin-top:12px;">
        <div>
          <h4 class="h4">Top Missing (A)</h4>
          <div class="dq-notes muted">${missA || "—"}</div>
        </div>
        <div>
          <h4 class="h4">Top Missing (B)</h4>
          <div class="dq-notes muted">${missB || "—"}</div>
        </div>
      </div>

      <div class="dq" style="margin-top:12px;">
        <h4 class="h4">Insights Count</h4>
        <div class="dq-notes muted">
          A: ${m.insights_count?.a ?? "—"} &nbsp; | &nbsp;
          B: ${m.insights_count?.b ?? "—"} &nbsp; | &nbsp;
          Diff: ${m.insights_count?.diff ?? "—"}
        </div>
      </div>
    `;
    comparePanel.classList.remove("hidden");
  }

  function clearComparePanel() {
    if (!comparePanel) return;
    comparePanel.innerHTML = "";
    comparePanel.classList.add("hidden");
  }

  /* ---------------------------
   * Profile link / Raw JSON / RenderAll
   * --------------------------- */
  function setProfileLink(url) {
    if (!profileLink) return;
    if (url) {
      profileLink.href = url;
      profileLink.classList.remove("hidden");
      profileLink.textContent = "Open Profiling Report (HTML)";
    } else {
      profileLink.classList.add("hidden");
      profileLink.href = "#";
    }
  }

  function setRawJson(report) {
    if (!reportText) return;
    reportText.textContent = JSON.stringify(report, null, 2);
  }

  function renderAll(report) {
    lastReport = report;

    setProfileLink(report?.profiling_report_url);
    setRawJson(report);

    if (report?.mode === "compare") renderCompare(report);
    else clearComparePanel();

    renderOverview(report);
    renderInsights(report);
    renderCharts(report);
  }

  /* ---------------------------
   * Copy JSON
   * --------------------------- */
  async function copyJson() {
    if (!lastReport) return;
    const text = JSON.stringify(lastReport, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setAppStatus("copied", "ok");
      setTimeout(() => setAppStatus("ready", "ok"), 1000);
    } catch {
      try {
        if (reportText) {
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(reportText);
          sel.removeAllRanges();
          sel.addRange(range);
          document.execCommand("copy");
          sel.removeAllRanges();
          setAppStatus("copied", "ok");
          setTimeout(() => setAppStatus("ready", "ok"), 1000);
        }
      } catch {
        setAppStatus("copy failed", "err");
        setTimeout(() => setAppStatus("ready", "ok"), 1200);
      }
    }
  }

  if (copyJsonBtn) copyJsonBtn.addEventListener("click", copyJson);

  if (severityFilter) severityFilter.addEventListener("change", () => renderInsights(lastReport || {}));
  if (sortFilter) sortFilter.addEventListener("change", () => renderInsights(lastReport || {}));

  /* ---------------------------
   * File A / File B handlers
   * --------------------------- */
  function setFile(file) {
    selectedFile = file;
    if (!uploadBtn) return;

    const compareOn = !!compareToggle?.checked;
    if (file) setStatus(`Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`);
    else setStatus("No file selected");

    uploadBtn.disabled = compareOn ? !(selectedFile && selectedFileB) : !selectedFile;
  }

  function setFileB(file) {
    selectedFileB = file;
    setStatusB(file ? `Selected B: ${file.name} (${Math.round(file.size / 1024)} KB)` : "No file B selected");
    if (compareToggle?.checked && uploadBtn) {
      uploadBtn.disabled = !(selectedFile && selectedFileB);
    }
  }

  /* ---------------------------
   * Compare toggle
   * --------------------------- */
  compareToggle?.addEventListener("change", () => {
    const on = !!compareToggle.checked;
    dropzoneBWrap?.classList.toggle("hidden", !on);
    if (uploadBtn) uploadBtn.textContent = on ? "Compare Insights" : "Generate Insights";
    clearComparePanel();

    if (uploadBtn) uploadBtn.disabled = on ? !(selectedFile && selectedFileB) : !selectedFile;
  });

  /* ---------------------------
   * Dropzones
   * --------------------------- */
  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const file = e.dataTransfer.files?.[0];
      if (file) setFile(file);
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      setFile(file || null);
    });
  }

  if (dropzoneB) {
    dropzoneB.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzoneB.classList.add("dragover");
    });
    dropzoneB.addEventListener("dragleave", () => dropzoneB.classList.remove("dragover"));
    dropzoneB.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzoneB.classList.remove("dragover");
      const file = e.dataTransfer.files?.[0];
      if (file) setFileB(file);
    });
  }

  if (fileInputB) {
    fileInputB.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      setFileB(file || null);
    });
  }

  /* ---------------------------
   * Upload / Compare run
   * --------------------------- */
  if (uploadBtn) {
    uploadBtn.addEventListener("click", async () => {
      const compareOn = !!compareToggle?.checked;
      if (!selectedFile) return;
      if (compareOn && !selectedFileB) return;

      closeEventSource();
      resetSteps();
      disableExports();
      clearComparePanel();

      setAppStatus("running", "info");
      jobStartMs = performance.now();
      setRunSummary("Running…", "info");

      setBadge("starting");
      setProgress(0);
      setProfileLink(null);
      lastReport = null;

      const fd = new FormData();
      let url = "/upload_async";

      if (!compareOn) {
        fd.append("file", selectedFile);
      } else {
        fd.append("file_a", selectedFile);
        fd.append("file_b", selectedFileB);
        url = "/compare_async";
      }

      let jobId = null;

      try {
        const res = await fetch(url, { method: "POST", body: fd });
        const data = await res.json();

        if (!res.ok) {
          if (reportText) reportText.textContent = data.error || "Upload failed.";
          setBadge("idle");
          setAppStatus("ready", "ok");
          uploadBtn.disabled = false;
          return;
        }

        jobId = data.job_id;
        setBadge("running • 0%");
        uploadBtn.disabled = true;
      } catch (err) {
        if (reportText) reportText.textContent = `Error: ${err}`;
        setBadge("idle");
        setAppStatus("ready", "ok");
        uploadBtn.disabled = false;
        return;
      }

      evtSrc = new EventSource(`/progress/${jobId}`);

      evtSrc.addEventListener("meta", (e) => {
        const evt = JSON.parse(e.data);
        if (typeof evt.progress_pct === "number") {
          setProgress(evt.progress_pct);
          setBadge(`running • ${evt.progress_pct}%`);
        }
      });

      evtSrc.addEventListener("step", (e) => {
        const evt = JSON.parse(e.data);
        addOrUpdateStep(evt.step, evt.status, evt.detail);

        if (typeof evt.progress_pct === "number") {
          setProgress(evt.progress_pct);
          setBadge(`running • ${evt.progress_pct}%`);
        }
      });

      evtSrc.addEventListener("done", async () => {
        closeEventSource();
        const elapsed = jobStartMs ? performance.now() - jobStartMs : null;

        setBadge("finalizing");
        setProgress(100);
        setAppStatus("finalizing", "warn");

        try {
          const res = await fetch(`/result/${jobId}`);
          const data = await res.json();

          if (data.status === "done") {
            renderAll(data.report || {});
            enableExports(jobId);
            setBadge("done • 100%");
            setAppStatus("ready", "ok");
            setRunSummary(`Done • ${fmtDuration(elapsed)}`, null);
          } else if (data.status === "error") {
            if (reportText) reportText.textContent = `Job error: ${data.error || "unknown error"}`;
            setBadge("error");
            setAppStatus("error", "err");
            setRunSummary(`Error • ${fmtDuration(elapsed)}`, "err");
          } else {
            if (reportText) reportText.textContent = "Job finished but result not ready.";
            setBadge("unknown");
            setAppStatus("ready", "ok");
          }
        } catch (err) {
          if (reportText) reportText.textContent = `Result fetch error: ${err}`;
          setBadge("error");
          setAppStatus("error", "err");
          setRunSummary("Failed", "err");
        } finally {
          uploadBtn.disabled = false;
          const on = !!compareToggle?.checked;
          uploadBtn.disabled = on ? !(selectedFile && selectedFileB) : !selectedFile;
        }
      });
    });
  }

  /* ---------------------------
   * Utilities
   * --------------------------- */
  function clamp01(x) {
    if (typeof x !== "number") return 0;
    return Math.max(0, Math.min(1, x));
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
