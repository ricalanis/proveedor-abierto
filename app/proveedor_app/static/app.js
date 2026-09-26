// Progressive enhancement only: every link works without JS (server renders ?ev=... into the panel).
(() => {
  const panel = document.getElementById("evidence-panel");
  const aside = document.getElementById("evidence");

  async function showEvidence(link) {
    const valueId = link.dataset.evidence;
    const target = new URL(link.href, location.href);
    if (!panel || target.pathname !== location.pathname) return false; // evidence of another supplier: navigate
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
    document.querySelectorAll("tr.is-selected").forEach((tr) => tr.classList.remove("is-selected"));
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
