"""FastAPI app: server-rendered investigation screens over one gold export."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import CORE_FIELDS, dod, investigate, live
from .gold import GoldStore, Run, UnavailableStore, backend_of, load_store, sniff_media_type

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
ROLES = ("investigator", "approver")

FIELD_LABELS = {
    "legal_name": "Legal name",
    "tax_id": "Tax ID (RFC)",
    "address": "Address",
    "founding_date": "Founding date",
    "tax_list_status": "Tax-list status",
    "sanction_status": "Sanction status",
    "legal_representative": "Legal representative",
}
SOURCE_TYPE_LABELS = {
    "procurement_portal": "Procurement portal",
    "tax_authority_list": "Tax authority list",
    "sanctions_registry": "Sanctions registry",
    "company_registry": "Company registry",
    "official_gazette": "Official gazette",
}
LINK_LABELS = {
    "shared_address": "Shared address",
    "shared_representative": "Shared legal representative",
    "same_procedure": "Same procedure",
}


@dataclass
class Settings:
    store: GoldStore | UnavailableStore
    case_dir: Path
    role: str = "investigator"
    identity_header: str | None = None  # header the NetBird proxy sets with the signed-in user, if any

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"PA_ROLE must be one of {ROLES}, got {self.role!r}")


def settings_from_env() -> Settings:
    try:
        store = load_store(REPO_ROOT)
    except (FileNotFoundError, ValueError) as exc:
        store = UnavailableStore(str(exc))
    return Settings(
        store=store,
        case_dir=Path(os.environ.get("PA_CASE_DIR", REPO_ROOT / "case")),
        role=os.environ.get("PA_ROLE", "investigator"),
        identity_header=os.environ.get("PA_IDENTITY_HEADER") or None,
    )


class NoGold(Exception):
    """No gold export can be read yet."""


def supplier_name(supplier: dict | None) -> str:
    if not supplier:
        return "Unknown supplier"
    f = (supplier.get("fields") or {}).get("legal_name") or {}
    return f.get("value") or supplier["id"]


def host_of(url: str) -> str:
    return urlsplit(url).hostname or url


def safe_url(url: str) -> str | None:
    """Only http(s) evidence links become clickable."""
    return url if urlsplit(url).scheme in ("http", "https") else None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    app = FastAPI(title="Proveedor Abierto", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    env = templates.env
    env.globals.update(
        CORE_FIELDS=CORE_FIELDS,
        FIELD_LABELS=FIELD_LABELS,
        SOURCE_TYPE_LABELS=SOURCE_TYPE_LABELS,
        LINK_LABELS=LINK_LABELS,
        supplier_name=supplier_name,
        host_of=host_of,
        safe_url=safe_url,
        role=settings.role,
    )
    env.filters["pct"] = lambda x: f"{round((x or 0) * 100)}%"
    env.filters["money"] = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else (x or "—")
    env.filters["field_label"] = lambda name: FIELD_LABELS.get(name, name.replace("_", " ").capitalize())

    def run(request: Request) -> Run:
        try:
            return settings.store.run(request.query_params.get("run"))
        except LookupError as exc:
            raise NoGold(str(exc)) from exc

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        ctx.setdefault("nav", "")
        r = ctx.get("run")
        ctx.setdefault("backend", r.inference_backend if r else None)
        ctx.setdefault("synthetic", bool(r and r.case_id.startswith("fixture")))
        return templates.TemplateResponse(request, name, ctx)

    @app.exception_handler(NoGold)
    def no_gold(request: Request, exc: NoGold) -> HTMLResponse:
        response = render(request, "no_gold.html", run=None, reason=str(exc))
        response.status_code = 503
        return response

    @app.get("/healthz")
    def healthz() -> dict:
        try:
            run_id = settings.store.latest_run_id() if isinstance(settings.store, GoldStore) else None
        except LookupError:
            run_id = None
        return {"ok": True, "role": settings.role, "run_id": run_id}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, q: str = "", show: str = "all"):
        r = run(request)
        rows = []
        needle = q.strip().lower()
        for s in r.suppliers:
            fields = s.get("fields") or {}
            if needle and not any(
                needle in str((fields.get(k) or {}).get("value") or "").lower() for k in ("legal_name", "tax_id")
            ) and needle not in s["id"].lower():
                continue
            ratio = dod.core_ratio(s)
            has_conflict = any(f.get("status") == "conflict" for f in fields.values())
            if show == "signals" and not s.get("flags"):
                continue
            if show == "incomplete" and ratio >= 0.8:
                continue
            if show == "conflicts" and not has_conflict:
                continue
            rows.append({"s": s, "ratio": ratio, "fields": fields})
        rows.sort(key=lambda row: (-len(row["s"].get("flags") or []), supplier_name(row["s"])))
        return render(request, "index.html", nav="suppliers", run=r, rows=rows, q=q, show=show)

    @app.get("/suppliers/{supplier_id}", response_class=HTMLResponse)
    def dossier(request: Request, supplier_id: str, ev: str | None = None):
        r = run(request)
        s = r.suppliers_by_id.get(supplier_id)
        if not s:
            raise HTTPException(404, f"no supplier {supplier_id} in run {r.run_id}")
        fields = s.get("fields") or {}
        order = [f for f in CORE_FIELDS] + sorted(k for k in fields if k not in CORE_FIELDS)
        contracts = [r.contracts_by_id[c] for c in s.get("contract_ids") or [] if c in r.contracts_by_id]
        selected = r.values.get(ev) if ev else None
        if selected and selected.supplier_id != supplier_id:
            selected = None
        return render(
            request, "dossier.html", nav="suppliers", run=r, s=s, fields=fields, order=order,
            contracts=contracts, ratio=dod.core_ratio(s), selected=selected,
        )

    @app.get("/fragments/evidence/{value_id}", response_class=HTMLResponse)
    def evidence_fragment(request: Request, value_id: str):
        r = run(request)
        ref = r.values.get(value_id)
        if not ref:
            raise HTTPException(404, f"no value {value_id}")
        return render(request, "_evidence.html", run=r, selected=ref)

    def completeness_model(r: Run) -> dict:
        recomputed = dod.compute(r.suppliers)
        engine = r.metrics or {}
        runs = settings.store.run_ids()
        prev_id = runs[runs.index(r.run_id) - 1] if r.run_id in runs and runs.index(r.run_id) > 0 else None
        prev = settings.store.run(prev_id).metrics if prev_id else {}
        total = recomputed["suppliers_total"]
        fields = []
        for name in CORE_FIELDS:
            ratio = recomputed["per_field_completeness"][name]
            before = (prev.get("per_field_completeness") or {}).get(name)
            fields.append({
                "name": name, "label": FIELD_LABELS.get(name, name), "ratio": ratio,
                "count": round(ratio * total), "delta": None if before is None else ratio - before,
            })
        return {
            "run_id": r.run_id, "prev_run_id": prev_id, "total": total, "fields": fields,
            "recomputed": recomputed, "engine": engine, "mismatches": dod.cross_check(recomputed, engine) if engine else
            ["engine metrics.json not found for this run"], "met": dod.dod_met(recomputed, r.inference_backend),
            "targets": dod.TARGETS, "backend": r.inference_backend,
            "coverage": engine.get("level_ratio_coverage") or {}, "modes": engine.get("mode_counts") or {},
            "jobs": engine.get("jobs") or {},
        }

    @app.get("/completeness", response_class=HTMLResponse)
    def completeness(request: Request):
        r = run(request)
        return render(request, "completeness.html", nav="completeness", run=r, m=completeness_model(r))

    @app.get("/api/completeness")
    def completeness_api(request: Request) -> dict:
        settings.store.refresh()  # pick up a new latest.json while a run is in progress
        return completeness_model(run(request))

    case = investigate.CaseDir(settings.case_dir)

    def selected_ids(r: Run, ids: str) -> list[str]:
        return [i for i in dict.fromkeys(x.strip() for x in ids.split(",")) if i in r.suppliers_by_id]

    @app.get("/signals", response_class=HTMLResponse)
    def signals(request: Request):
        r = run(request)
        return render(request, "signals.html", nav="signals", run=r, groups=investigate.signals_by_rule(r))

    @app.get("/signals/{supplier_id}/{index}", response_class=HTMLResponse)
    def signal_detail(request: Request, supplier_id: str, index: int):
        r = run(request)
        s = r.suppliers_by_id.get(supplier_id)
        flags = (s or {}).get("flags") or []
        if not s or not 0 <= index < len(flags):
            raise HTTPException(404, "no such signal")
        flag = flags[index]
        refs = [r.values[v] for v in flag.get("evidence_value_ids") or [] if v in r.values]
        dispute = json.dumps(investigate.dispute_record(r, s, flag), indent=2, ensure_ascii=False)
        return render(request, "signal.html", nav="signals", run=r, s=s, flag=flag, refs=refs,
                      info=investigate.rule_info(flag["rule_id"], flag["label"]), dispute=dispute)

    @app.get("/relationships", response_class=HTMLResponse)
    def relationships(request: Request, focus: str = "", types: str = "shared_address,shared_representative"):
        r = run(request)
        wanted = request.query_params.getlist("t") or types.split(",")
        chosen = tuple(t for t in investigate.LINK_TYPES if t in wanted) or ("shared_address",)
        found = investigate.clusters(r, chosen)
        if focus:
            found.sort(key=lambda c: focus not in c.members)
        return render(request, "relationships.html", nav="relationships", run=r, clusters=found, focus=focus,
                      chosen=chosen, LINK_TYPES=investigate.LINK_TYPES,
                      summarize=lambda c: investigate.cluster_summary(r, c))

    @app.get("/journal", response_class=HTMLResponse)
    def journal_index(request: Request):
        r = run(request)
        by_phase: dict[int, int] = {}
        for step in r.trace:
            by_phase[step.get("phase")] = by_phase.get(step.get("phase"), 0) + 1
        tdds = sorted({s["tdd_path"] for s in r.trace if s.get("tdd_path")})
        sample = next((v for v in r.values.values() if r.steps_by_value.get(v.value_id)), None)
        return render(request, "journal_index.html", nav="journal", run=r, by_phase=by_phase, anchors=case.anchors(),
                      tdds=[{"path": p, "exists": case.exists(p)} for p in tdds], sample=sample,
                      PHASE_NAMES=investigate.PHASE_NAMES)

    @app.get("/journal/{value_id}", response_class=HTMLResponse)
    def journal(request: Request, value_id: str):
        r = run(request)
        ref = r.values.get(value_id)
        if not ref:
            raise HTTPException(404, f"no value {value_id}")
        anchors = case.anchors()
        for a in anchors:
            a["text"] = case.read(a["path"], limit=1500) if a["exists"] else None
        return render(request, "journal.html", nav="journal", run=r, ref=ref,
                      s=r.suppliers_by_id.get(ref.supplier_id), replays=investigate.journal_chain(r, case, value_id),
                      anchors=anchors)

    @app.get("/case-file", response_class=HTMLResponse)
    def case_file(request: Request, path: str):
        text = case.read(path, limit=200_000)
        if text is None:
            raise HTTPException(404, "not in the case package")
        return render(request, "case_file.html", nav="journal", run=None, path=path, text=text)

    @app.get("/watchlist", response_class=HTMLResponse)
    def watchlist(request: Request, ids: str = ""):
        r = run(request)
        chosen = selected_ids(r, ids)
        runs = settings.store.run_ids()
        prev_id = runs[runs.index(r.run_id) - 1] if r.run_id in runs and runs.index(r.run_id) > 0 else None
        prev = settings.store.run(prev_id) if prev_id else None
        items = [{"s": r.suppliers_by_id[i],
                  "changes": investigate.diff_supplier(prev.suppliers_by_id.get(i), r.suppliers_by_id[i]) if prev else []}
                 for i in chosen]
        return render(request, "watchlist.html", nav="watchlist", run=r, items=items, ids=",".join(chosen),
                      prev_id=prev_id)

    @app.get("/export/{name}")
    def export(request: Request, name: str, ids: str = ""):
        from . import export as ex

        r = run(request)
        subset = selected_ids(r, ids) if ids else None
        stem = f"{r.case_id}-{r.run_id}" + ("-watchlist" if subset else "")
        if name == "suppliers.csv":
            body, media = ex.to_csv(r, subset), "text/csv; charset=utf-8"
        elif name == "ocds.json":
            body, media = json.dumps(ex.to_ocds(r, subset), ensure_ascii=False, indent=2), "application/json"
        elif name == "gold.ttl":
            body, media = ex.to_turtle(r, subset), "text/turtle; charset=utf-8"
        else:
            raise HTTPException(404, "unknown export")
        ext = name.rsplit(".", 1)[1]
        return Response(body, media_type=media,
                        headers={"Content-Disposition": f'attachment; filename="{stem}.{ext}"'})

    def require_approver(request: Request) -> None:
        if settings.role != "approver":
            raise HTTPException(403, "approvals are only available on the approver URL")

    def identity(request: Request) -> str:
        return request.headers.get(settings.identity_header, "") if settings.identity_header else ""

    @app.get("/approvals", response_class=HTMLResponse)
    def approvals(request: Request, done: str = "", error: str = ""):
        require_approver(request)
        items = investigate.approvals(case)
        for a in items:
            paths = a.meta.get("artifact_paths") or {"prd": ["01-scope/prd.md"]}.get(a.checkpoint or "", [])
            a.artifacts = [{"path": p, "exists": case.exists(p)} for p in paths]
        try:
            r = settings.store.run(None)
        except LookupError:
            r = None
        return render(request, "approvals.html", nav="approvals", run=r, items=items, who=identity(request),
                      done=done, error=error)

    @app.post("/approvals")
    async def approve(request: Request):
        require_approver(request)
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "cross-origin approval refused")
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        who = identity(request) or form.get("approver", "")
        try:
            investigate.approve(case, form.get("phase_dir", ""), who)
        except ValueError as exc:
            return RedirectResponse(f"/approvals?error={exc}", status_code=303)
        return RedirectResponse(f"/approvals?done={form.get('phase_dir', '')}", status_code=303)

    def run_view_model(run_id: str, after: int = 0) -> dict:
        steps = live.annotate(settings.store.live_steps(run_id))
        status = settings.store.live_status(run_id)
        if not steps and status is None:
            raise HTTPException(404, f"no live feed for run {run_id}")
        jobs = settings.store.live_jobs(run_id)
        backend = backend_of((status or {}).get("metrics"), [*steps, status or {}])
        return {"run_id": run_id, "steps": steps, "new": steps[after:][::-1], "panel": live.summarize(steps, status),
                "proof": live.proof(jobs), "backend": backend}

    @app.get("/run")
    def run_latest():
        run_id = settings.store.live_run_id()
        if not run_id:
            raise NoGold("No live run feed yet: the engine writes runs/<case_id>/latest.json when a run starts.")
        return RedirectResponse(f"/run/{run_id}", status_code=307)

    @app.get("/run/{run_id}", response_class=HTMLResponse)
    def run_view(request: Request, run_id: str):
        m = run_view_model(run_id)
        return render(request, "run.html", nav="run", run=None, live_run_id=run_id, m=m, recent=m["new"][:150],
                      backend=m["backend"], synthetic=settings.store.case_id.startswith("fixture"),
                      PHASES=live.PHASES, MODE_NAMES=live.MODE_NAMES,
                      CHECKPOINT_PHASE=live.CHECKPOINT_PHASE, others=settings.store.live_run_ids())

    @app.get("/api/run/{run_id}")
    def run_api(request: Request, run_id: str, after: int = 0) -> dict:
        m = run_view_model(run_id, max(after, 0))
        env = templates.env
        steps_html = env.get_template("_steps.html").render(steps=m["new"][:150], MODE_NAMES=live.MODE_NAMES)
        panel_html = env.get_template("_run_panel.html").render(
            m=m, PHASES=live.PHASES, CHECKPOINT_PHASE=live.CHECKPOINT_PHASE, MODE_NAMES=live.MODE_NAMES)
        proof_html = env.get_template("_proof.html").render(m=m)
        timeline_html = env.get_template("_timeline.html").render(
            m=m, PHASES=live.PHASES, CHECKPOINT_PHASE=live.CHECKPOINT_PHASE)
        return {"count": len(m["steps"]), "state": m["panel"]["state"], "steps_html": steps_html,
                "panel_html": panel_html, "timeline_html": timeline_html,
                "proof_html": proof_html}

    @app.get("/bronze/{key}")
    def bronze(key: str):
        data = settings.store.bronze(key)
        if data is None:
            raise HTTPException(404, "bronze object not found")
        declared = str(settings.store.bronze_meta(key).get("content_type") or "")
        media_type = declared if declared.startswith(("image/", "application/pdf")) else sniff_media_type(data)
        return Response(
            data,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",  # content-addressed
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return app
