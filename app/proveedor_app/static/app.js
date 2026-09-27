// Progressive enhancement only: every link works without JS (server renders ?ev=... into the panel).
(() => {
  const panel = document.getElementById("evidence-panel");
  const aside = document.getElementById("evidence");

  async function showEvidence(link) {
    const valueId = link.dataset.evidence;
    const target = new URL(link.href, location.href);
    if (!panel || target.pathname !== location.pathname) return false; // evidence of another entity: navigate
    aside.setAttribute("aria-busy", "true");
    try {
      const run = new URLSearchParams(location.search).get("run");
      const url = `/fragments/evidence/${encodeURIComponent(valueId)}` + (run ? `?run=${encodeURIComponent(run)}` : "");
      const res = await fetch(url);
      if (!res.ok) return false;
      panel.innerHTML = await res.text();
    } catch {
      return false;
    } finally {
      aside.removeAttribute("aria-busy");
    }
    document.querySelectorAll(".is-selected").forEach((row) => row.classList.remove("is-selected"));
    document.getElementById(`row-${valueId}`)?.classList.add("is-selected");
    history.replaceState(null, "", `${target.pathname}${target.search}#evidence`);
    if (window.matchMedia("(max-width: 960px)").matches) aside.scrollIntoView({ block: "start" });
    aside.focus({ preventScroll: true });
    return true;
  }

  document.addEventListener("click", async (event) => {
    const link = event.target.closest("a[data-evidence]");
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    if (!(await showEvidence(link))) location.href = link.href;
  });
})();

// Completeness: follow the latest run so the bars climb while the engine works.
(() => {
  const root = document.querySelector("[data-live-src]");
  const toggle = document.getElementById("live");
  if (!root || !toggle) return;
  const pct = (x) => `${Math.round(x * 100)}%`;
  async function tick() {
    if (!toggle.checked || document.hidden) return;
    try {
      const res = await fetch(root.dataset.liveSrc, { headers: { Accept: "application/json" } });
      if (!res.ok) return;
      const m = await res.json();
      document.getElementById("live-status").textContent =
        `run ${m.run_id}${m.prev_run_id ? ` · compared with ${m.prev_run_id}` : ""} · updated ${new Date().toLocaleTimeString()}`;
      for (const f of m.fields) {
        const row = document.querySelector(`#field-bars tr[data-field="${f.name}"]`);
        if (!row) continue;
        row.querySelector(".bar").style.setProperty("--v", `${(f.ratio * 100).toFixed(1)}%`);
        row.querySelector('[data-bind="ratio"]').textContent = pct(f.ratio);
        row.querySelector('[data-bind="count"]').textContent = `${f.count}/${m.total}`;
        row.querySelector('[data-bind="delta"]').textContent =
          f.delta === null ? "" : `${f.delta >= 0 ? "+" : ""}${Math.round(f.delta * 100)} pts`;
      }
      for (const c of m.criteria || []) {
        const item = document.querySelector(`.dod__item[data-key="${CSS.escape(c.criterion_id)}"]`);
        if (!item) continue;
        const actual = c.recomputed ? c.actual : c.engine_actual;
        item.querySelector('[data-bind="actual"]').textContent = actual === null || actual === undefined ? "—" : actual;
        const state = item.querySelector(".dod__state");
        state.dataset.met = String(c.met);
        state.textContent = c.mock ? "Not counted (mock)" : c.met ? "Met" : "Not yet";
      }
      const cc = document.getElementById("crosscheck");
      cc.classList.toggle("crosscheck--bad", m.mismatches.length > 0);
      cc.textContent = m.mismatches.length
        ? `Engine metrics disagree with the export: ${m.mismatches.join("; ")}`
        : "Recomputed from gold: matches the engine's metrics.json.";
    } catch {
      /* keep the last good numbers on screen */
    }
  }
  setInterval(tick, 5000);
})();

// Watchlist: kept in this browser only (the investigator URL is read-only on the server).
(() => {
  const KEY = "pa.watchlist";
  const read = () => {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
  };
  const write = (ids) => {
    try { localStorage.setItem(KEY, JSON.stringify(ids)); } catch { /* private mode: nothing to keep */ }
  };

  for (const btn of document.querySelectorAll("[data-watch]")) {
    const id = btn.dataset.watch;
    const sync = () => {
      const on = read().includes(id);
      btn.setAttribute("aria-pressed", String(on));
      btn.textContent = on ? btn.dataset.on || "On my list" : btn.dataset.off || "Add to my list";
    };
    sync();
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      const ids = read();
      write(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);
      sync();
    });
  }

  const list = document.getElementById("watchlist");
  if (list) {
    const ids = read();
    const shown = list.dataset.ids ? list.dataset.ids.split(",") : [];
    if (!new URLSearchParams(location.search).has("ids") && ids.length) {
      location.replace(`/watchlist?ids=${encodeURIComponent(ids.join(","))}`);
    } else if (shown.length && !ids.length) {
      write(shown); // arrived through a shared link: adopt it
    }
    list.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-unwatch]");
      if (!btn) return;
      const next = read().filter((x) => x !== btn.dataset.unwatch);
      write(next);
      location.replace(`/watchlist?ids=${encodeURIComponent(next.join(","))}`);
    });
  }

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-copy]");
    if (!btn) return;
    const text = document.querySelector(btn.dataset.copy)?.textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = btn.dataset.done || "Copied";
    } catch {
      btn.textContent = btn.dataset.fail || "Select the text to copy";
    }
  });
})();

// Live run: poll the feed, prepend new steps, update the panel in place so bars glide instead of jumping.
(() => {
  const view = document.getElementById("runview");
  if (!view) return;
  const steps = document.getElementById("steps");
  const panel = document.getElementById("run-panel");
  const timeline = document.getElementById("timeline");
  const state = document.getElementById("run-state");
  const proof = document.getElementById("proof");
  let count = Number(view.dataset.count || 0);
  let busy = false;

  function morph(target, html) {
    const next = document.createElement("div");
    next.innerHTML = html;
    const keys = (root) => [...root.querySelectorAll("[data-k]")].map((el) => el.dataset.k).join("|");
    if (keys(next) !== keys(target)) {
      target.innerHTML = html;
      return;
    }
    for (const el of next.querySelectorAll("[data-k]")) {
      const cur = target.querySelector(`[data-k="${CSS.escape(el.dataset.k)}"]`);
      if (!cur) continue;
      if (el.getAttribute("style") !== cur.getAttribute("style")) cur.setAttribute("style", el.getAttribute("style") || "");
      if (el.className !== cur.className) cur.className = el.className;
      if (el.innerHTML !== cur.innerHTML) cur.innerHTML = el.innerHTML;
    }
  }

  async function tick() {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const res = await fetch(`${view.dataset.api}?after=${count}`, { headers: { Accept: "application/json" } });
      if (!res.ok) return;
      const data = await res.json();
      if (data.count > count && data.steps_html.trim()) {
        const tmp = document.createElement("ol");
        tmp.innerHTML = data.steps_html;
        for (const li of tmp.children) li.classList.add("step--new");
        steps.prepend(...tmp.children);
        while (steps.children.length > 150) steps.lastElementChild.remove();
      }
      // A loop thread that gained iterations is re-rendered in place, keeping whether the reader had it open.
      for (const t of data.threads_html || []) {
        const tmp = document.createElement("ol");
        tmp.innerHTML = t.html;
        const next = tmp.firstElementChild;
        if (!next) continue;
        const cur = document.getElementById(t.id);
        if (cur) {
          const was = cur.querySelector("details");
          const now = next.querySelector("details");
          if (was && now) now.open = was.open;
          cur.replaceWith(next);
        } else {
          steps.prepend(next);
        }
      }
      count = data.count;
      morph(panel, data.panel_html);
      morph(timeline, data.timeline_html);
      if (proof && proof.innerHTML !== data.proof_html) proof.innerHTML = data.proof_html;
      state.textContent = data.state;
      state.className = `run-state run-state--${data.state}`;
      view.dataset.state = data.state;
      view.dataset.count = String(count);
    } catch {
      /* keep what is on screen; try again next tick */
    } finally {
      busy = false;
    }
  }
  setInterval(() => {
    if (view.dataset.state !== "done" && view.dataset.state !== "failed") tick();
  }, 1200);
})();
