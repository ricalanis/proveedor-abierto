"""Reproducible screenshot kit for the demo and judges (R13): the key views of Proveedor Abierto and the Ontofill
Console, captured from a running deploy at 1280 and 390 px, light and dark.

Read-only by construction: the kit never signs in and never stores a session. Point it at the services directly over
the NetBird mesh (an admin peer reaches them without the proxy). The console refuses every decision from direct mesh
peers, so nothing captured this way can act. The masthead then reads "not in group … · read-only", which is honest for
screenshots. Before each capture, personal data is redacted in the page: e-mail addresses and self-declared names
become placeholders. A `manifest.json` lists every file with its URL, status and time.

    uv run pa-app screens --product http://<mesh-ip>:8400 --console http://<mesh-ip>:8410 \
        --target library-demo --target library-demo:<run-id>
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urljoin

MODES = ((1280, "dark"), (1280, "light"), (390, "dark"), (390, "light"))

# Replaces e-mail addresses and "<name> (self-declared)" with placeholders in every text node and input value.
REDACT_JS = r"""
() => {
  const email = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
  const declared = /([^\s·,()][^·,()]{0,60}?)\s+\((self-declared)\)/g;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n = 0;
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const before = node.nodeValue;
    const after = before.replace(email, "[e-mail]").replace(declared, "[name] ($2)");
    if (after !== before) { node.nodeValue = after; n++; }
  }
  for (const el of document.querySelectorAll("input, textarea")) {
    if (el.type === "password") { el.value = ""; continue; }
    if (email.test(el.value || "")) { el.value = el.value.replace(email, "[e-mail]"); n++; }
  }
  return n;
}
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "page"


def console_views(page, base: str, target: str) -> list[tuple[str, str]]:
    """The console views for one case[:run], with concrete deep links resolved from the console's own JSON twins."""
    case, _, run = target.partition(":")
    q = f"?run={quote(run)}" if run else ""
    views = [("tour", f"/tour?case={quote(case)}" + (f"&run={quote(run)}" if run else "")), ("inbox", "/inbox"),
             ("hub", f"/cases/{case}"), ("operation", f"/cases/{case}/operation{q}"),
             ("definition", f"/cases/{case}/definition{q}"), ("discovery", f"/cases/{case}/discovery{q}"),
             ("pages", f"/cases/{case}/pages{q}"), ("sites", f"/cases/{case}/sites{q}"),
             ("output", f"/cases/{case}/output{q}"), ("graph", f"/cases/{case}/graph{q}"),
             ("inference", f"/cases/{case}/inference{q}"), ("failures", f"/cases/{case}/failures{q}"),
             ("summary", f"/cases/{case}/summary{q}"), ("watch", "/watch"), ("new-case", "/cases/new")]
    try:  # the first site graph, if the case has one
        sites = page.request.get(urljoin(base, f"/cases/{case}/api/viz/sites{q}")).json()
        rows = sites.get("rows") if isinstance(sites.get("rows"), list) else []
        first = next((s for s in rows if isinstance(s, dict) and s.get("source_id")), None)
        sid = (first or {}).get("source_id")
        if sid:
            views.insert(8, ("site-graph", f"/cases/{case}/sites/{quote(sid)}{q}"))
    except Exception as exc:  # noqa: BLE001 — an older console or no graphs: the list page is still captured
        print(f"no site graph deep link for {target}: {type(exc).__name__}")
    run_id = run
    if not run_id:
        try:
            run_id = page.request.get(urljoin(base, f"/cases/{case}/api/viz/operation")).json().get("run_id")
        except Exception:  # noqa: BLE001
            run_id = None
    if run_id:
        views.insert(4, ("run", f"/cases/{case}/runs/{quote(run_id)}"))
    return [(f"{_slug(target)}-{name}", path) for name, path in views]


def product_views(page, base: str) -> list[tuple[str, str]]:
    views = [("home", "/"), ("signals", "/signals"), ("como-se-hizo", "/como-se-hizo"), ("como-leer", "/como-leer"),
             ("fuentes", "/fuentes"), ("completeness", "/completeness")]
    page.goto(urljoin(base, "/"))
    dossier = page.locator("a.roster__name").first
    if dossier.count():
        href = dossier.get_attribute("href")
        views.insert(1, ("dossier", href))
        page.goto(urljoin(base, href))
        receipt = page.locator("a.ev-link[data-evidence]").first
        if receipt.count():
            views.insert(2, ("dossier-receipt", receipt.get_attribute("href")))
    page.goto(urljoin(base, "/signals"))
    signal = page.locator(".hits a").first
    if signal.count():
        views.insert(3, ("signal", signal.get_attribute("href")))
    return views


def capture(out: Path, *, product: str | None, console: str | None, targets: list[str],
            only: str | None = None, log=print) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    manifest = {"captured_at": datetime.now(UTC).isoformat(timespec="seconds"), "files": [], "redactions": 0,
                "product": product, "console": console, "targets": targets}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        sites = [("product", product), ("console", console)]
        for site, base in sites:
            if not base or (only and only != site):
                continue
            opts: dict = {}  # never a stored session: the capture must not be able to act as anyone
            probe = browser.new_context(**opts).new_page()
            views = product_views(probe, base) if site == "product" else \
                [v for t in (targets or ["library-demo"]) for v in console_views(probe, base, t)]
            probe.context.close()
            for width, scheme in MODES:
                ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, **opts)
                page = ctx.new_page()
                for name, path in views:
                    url = urljoin(base, path)
                    resp = page.goto(url, wait_until="networkidle")
                    page.wait_for_timeout(400)  # fonts and the live chip settle
                    manifest["redactions"] += int(page.evaluate(REDACT_JS) or 0)
                    file = out / f"{site}-{name}-{width}-{scheme}.png"
                    page.screenshot(path=str(file), full_page=True)
                    manifest["files"].append({"file": file.name, "url": url, "status": resp.status if resp else None,
                                              "width": width, "scheme": scheme})
                    log(f"{file.name}  {resp.status if resp else '?'}  {url}")
                ctx.close()
        browser.close()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
