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

// Receipts: a screenshot that cannot be loaded gives way to a plain note (the link and saved copy still work).
document.addEventListener("error", (event) => {
  const img = event.target;
  if (!(img instanceof HTMLImageElement) || !img.matches("img[data-shot]")) return;
  const figure = img.closest("figure");
  figure?.querySelector(".shot__frame")?.remove();
  figure?.querySelector("figcaption")?.remove();
  figure?.querySelector(".shot__missing")?.removeAttribute("hidden");
}, true);

// My list: kept in this browser only (the site is read-only on the server).
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
