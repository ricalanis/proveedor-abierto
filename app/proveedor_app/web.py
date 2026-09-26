"""FastAPI app: server-rendered investigation screens over one gold export."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import dod, investigate, live
from .domain import LEGACY_ONTOLOGY, Domain
from .gold import GoldStore, Run, UnavailableStore, backend_of, load_store, sniff_media_type

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
ROLES = ("investigator", "approver")

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


def brief(value, limit: int = 240) -> str:
    """Readable one-liner for trace/proof fields, which the engine may write as strings or objects."""
    def fmt(v):
        if isinstance(v, dict):
            return ", ".join(f"{k}: {fmt(x)}" for k, x in v.items() if x not in (None, "", [], {}))
        if isinstance(v, list):
            shown = [fmt(x) for x in v[:4]]
            return "[" + ", ".join(shown) + (f", +{len(v) - 4}" if len(v) > 4 else "") + "]"
        if isinstance(v, str) and v.startswith("sha256:") and len(v) > 20:
            return v[:15] + "…"
        return str(v)

    text = "" if value is None else fmt(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


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
        host_of=host_of,
        safe_url=safe_url,
        role=settings.role,
    )
    env.filters["pct"] = lambda x: f"{round((x or 0) * 100)}%"
    env.filters["money"] = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else (x or "—")
    env.filters["brief"] = brief

    def run(request: Request) -> Run:
        try:
            return settings.store.run(request.query_params.get("run"))
        except LookupError as exc:
            raise NoGold(str(exc)) from exc

    if isinstance(settings.store, GoldStore):
        settings.store.case_dir = settings.case_dir  # the case's approved ontology describes the entities

    def current_domain() -> Domain:
        """Domain for pages without a gold run in hand: latest run's, else the case ontology, else legacy."""
        try:
            return settings.store.run(None).domain
        except LookupError:
            text = investigate.CaseDir(settings.case_dir).read("02-ontology/ontology.json", limit=10**7)
            try:
                onto = json.loads(text) if text else {}
            except ValueError:
                onto = {}
            if onto.get("primary_class"):
                return Domain.from_ontology(onto)
            return Domain.from_ontology(LEGACY_ONTOLOGY, legacy=True)

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        ctx.setdefault("nav", "")
        r = ctx.get("run")
        ctx.setdefault("domain", r.domain if r else current_domain())
        ctx.setdefault("backend", r.inference_backend if r else None)
        ctx.setdefault("synthetic", bool(r and r.case_id.startswith("fixture")))
        ctx.setdefault("preview", bool(r and r.metrics.get("preview")))
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
        d = r.domain
        searchable = [p for p in (d.title_property(), d.identifier_property()) if p]
        rows = []
        needle = q.strip().lower()
        for e in r.primary:
            props = e.get("properties") or {}
            if needle and not any(needle in str((props.get(k) or {}).get("value") or "").lower() for k in searchable) \
                    and needle not in e["id"].lower():
                continue
            ratio = dod.dod_ratio(e, d)
            has_conflict = any(isinstance(v, dict) and v.get("status") == "conflict" for v in props.values())
            if show == "signals" and not e.get("flags"):
                continue
            if show == "incomplete" and ratio >= d.dod_threshold:
                continue
            if show == "conflicts" and not has_conflict:
                continue
            rows.append({"e": e, "ratio": ratio, "props": props,
                         "linked": sum(1 for link in e.get("links") or [] if link.get("target") in r.entities_by_id
                                       and r.entities_by_id[link["target"]].get("class") != d.primary_class)})
        rows.sort(key=lambda row: (-len(row["e"].get("flags") or []), r.title(row["e"])))
        return render(request, "index.html", nav="entities", run=r, rows=rows, q=q, show=show)

    @app.get("/entities/{entity_id}", response_class=HTMLResponse)
    @app.get("/suppliers/{entity_id}", response_class=HTMLResponse, include_in_schema=False)
    def dossier(request: Request, entity_id: str, ev: str | None = None):
        r = run(request)
        e = r.entities_by_id.get(entity_id)
        if not e:
            raise HTTPException(404, f"no entity {entity_id} in run {r.run_id}")
        d = r.domain
        props = e.get("properties") or {}
        declared = [p.id for p in d.props(e.get("class"))]
        order = declared + sorted(k for k in props if k not in declared)
        peers, related = [], {}
        for link in e.get("links") or []:
            target = r.entities_by_id.get(link.get("target"))
            if not target:
                continue
            if target.get("class") == e.get("class"):
                peers.append({"link": link, "target": target})
            else:  # other classes (e.g. contracts) are listed as tables, grouped by relation
                related.setdefault(link.get("property"), {"cls": target.get("class"), "rows": []})["rows"].append(target)
        selected = r.values.get(ev) if ev else None
        if selected and selected.entity_id != entity_id:
            selected = None
        return render(request, "dossier.html", nav="entities", run=r, e=e, props=props, order=order,
                      peers=peers, related=related, ratio=dod.dod_ratio(e, d), selected=selected)

    @app.get("/fragments/evidence/{value_id}", response_class=HTMLResponse)
    def evidence_fragment(request: Request, value_id: str):
        r = run(request)
        ref = r.values.get(value_id)
        if not ref:
            raise HTTPException(404, f"no value {value_id}")
        return render(request, "_evidence.html", run=r, selected=ref)

    def completeness_model(r: Run) -> dict:
        d = r.domain
        recomputed = dod.compute(r.entities, d)
        engine = r.metrics or {}
        runs = settings.store.run_ids()
        prev_id = runs[runs.index(r.run_id) - 1] if r.run_id in runs and runs.index(r.run_id) > 0 else None
        prev_run = settings.store.run(prev_id) if prev_id else None
        prev = dod.compute(prev_run.entities, prev_run.domain) if prev_run else None
        total = recomputed["entities_total"].get(d.primary_class, 0)
        fields = []
        for p in d.dod_props():
            ratio = recomputed["per_property_completeness"][d.primary_class][p.id]
            before = (prev["per_property_completeness"].get(d.primary_class) or {}).get(p.id) if prev else None
            fields.append({"name": p.id, "label": p.label, "ratio": ratio, "count": round(ratio * total),
                           "delta": None if before is None else ratio - before})
        return {
            "run_id": r.run_id, "prev_run_id": prev_id, "total": total, "fields": fields,
            "primary_label": d.class_label(plural=True), "threshold": d.dod_threshold,
            "threshold_stated": d.threshold_stated, "recomputed": recomputed,
            "criteria": dod.criteria(recomputed, engine, d, r.inference_backend, r.dod_queries, r.entities),
            "mismatches": dod.cross_check(recomputed, engine, d) if engine else ["engine metrics.json not found"],
            "backend": r.inference_backend, "coverage": engine.get("level_ratio_coverage") or {},
            "modes": engine.get("mode_counts") or {}, "jobs": engine.get("jobs") or {},
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
        primary = {e["id"] for e in r.primary}
        return [i for i in dict.fromkeys(x.strip() for x in ids.split(",")) if i in primary]

    @app.get("/signals", response_class=HTMLResponse)
    def signals(request: Request):
        r = run(request)
        return render(request, "signals.html", nav="signals", run=r, groups=investigate.signals_by_rule(r))

    @app.get("/signals/{entity_id}/{index}", response_class=HTMLResponse)
    def signal_detail(request: Request, entity_id: str, index: int):
        r = run(request)
        e = r.entities_by_id.get(entity_id)
        flags = (e or {}).get("flags") or []
        if not e or not 0 <= index < len(flags):
            raise HTTPException(404, "no such signal")
        flag = flags[index]
        refs = [r.values[v] for v in flag.get("evidence_value_ids") or [] if v in r.values]
        dispute = json.dumps(investigate.dispute_record(r, e, flag), indent=2, ensure_ascii=False)
        return render(request, "signal.html", nav="signals", run=r, e=e, flag=flag, refs=refs,
                      info=r.domain.rule(flag["rule_id"], flag["label"]), dispute=dispute)

    @app.get("/relationships", response_class=HTMLResponse)
    def relationships(request: Request, focus: str = "", types: str = ""):
        r = run(request)
        available = r.domain.peer_relations()
        wanted = request.query_params.getlist("t") or [x for x in types.split(",") if x]
        default = [rel for rel in available if not r.domain.relations.get(rel, {}).get("dense")][:2] or available[:1]
        chosen = tuple(x for x in available if x in (wanted or default))
        found = investigate.clusters(r, chosen)
        if focus:
            found.sort(key=lambda c: focus not in c.members)
        return render(request, "relationships.html", nav="relationships", run=r, clusters=found, focus=focus,
                      chosen=chosen, LINK_TYPES=available, summarize=lambda c: investigate.cluster_summary(r, c))

    @app.get("/journal", response_class=HTMLResponse)
    def journal_index(request: Request):
        r = run(request)
        by_phase: dict[int, int] = {}
        for step in r.trace:
            by_phase[step.get("phase")] = by_phase.get(step.get("phase"), 0) + 1
        tdds = sorted({s["tdd_path"] for s in r.trace if s.get("tdd_path")})
        sample = next((v for v in r.values.values() if r.steps_by_value.get(v.value_id)), None)
        return render(request, "journal_index.html", nav="journal", run=r, by_phase=by_phase, anchors=case.anchors(),
                      sources=list(case.sources().values()),
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
                      e=r.entities_by_id.get(ref.entity_id), replays=investigate.journal_chain(r, case, value_id),
                      anchors=anchors)

    @app.get("/engine", response_class=HTMLResponse)
    def engine_report(request: Request):
        from . import report

        r = run(request)
        card = report.build(settings.store, r, case)
        return render(request, "engine.html", nav="engine", run=r, card=card, MODE_NAMES=live.MODE_NAMES)

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
        items = [{"e": r.entities_by_id[i],
                  "changes": investigate.diff_entity(prev.entities_by_id.get(i), r.entities_by_id[i]) if prev else []}
                 for i in chosen]
        from . import export as ex

        return render(request, "watchlist.html", nav="watchlist", run=r, items=items, ids=",".join(chosen),
                      prev_id=prev_id, ocds=ex.ocds_available(r))

    @app.get("/export/{name}")
    def export(request: Request, name: str, ids: str = ""):
        from . import export as ex

        r = run(request)
        subset = selected_ids(r, ids) if ids else None
        stem = f"{r.case_id}-{r.run_id}" + ("-watchlist" if subset else "")
        if name in ("entities.csv", "suppliers.csv"):
            body, media = ex.to_csv(r, subset), "text/csv; charset=utf-8"
        elif name == "ocds.json":
            if not ex.ocds_available(r):
                raise HTTPException(404, "OCDS export needs an ontology class aligned to OCDS contracts")
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

    @app.get("/spend", response_class=HTMLResponse)
    def spend(request: Request):
        """Operator billing view: reads the spend tracker's history file only; never calls billing APIs."""
        require_approver(request)
        path = Path(os.environ.get("PA_SPEND_HISTORY", REPO_ROOT.parent / ".cache" / "spend" / "history.jsonl"))
        history = []
        if path.is_file():
            for raw in path.read_text().splitlines():
                try:
                    history.append(json.loads(raw))
                except ValueError:
                    continue
        latest = history[-1] if history else None
        try:
            r = settings.store.run(None)
        except LookupError:
            r = None
        per_supplier = None
        eng = (latest or {}).get("engine") or {}
        if r and eng.get("reported") and r.run_id in (eng.get("runs") or {}):
            complete = sum(dod.dod_ratio(e, r.domain) >= r.domain.dod_threshold for e in r.primary)
            gold_values = sum(1 for v in r.values.values() if dod.is_filled(v.data))
            usd = eng["runs"][r.run_id]
            per_supplier = {"run_id": r.run_id, "usd": usd, "per_complete_supplier": usd / complete if complete else None,
                            "per_gold_value": usd / gold_values if gold_values else None}
        rows, prev = [], None
        for s in history[-48:]:
            dt = (datetime.fromisoformat(s["ts"]) - datetime.fromisoformat(prev["ts"])).total_seconds() / 3600 if prev else 0
            rate = (s["credit_used"] - prev["credit_used"]) / dt if prev and dt > 0 else None
            rows.append({"ts": s["ts"], "used": s["credit_used"], "left": s["credit_remaining"], "rate": rate})
            prev = s
        deadline = datetime(2026, 9, 27, 12, 0, tzinfo=timezone(timedelta(hours=-7)))
        hours_left = max(0.0, (deadline - datetime.fromisoformat(latest["ts"])).total_seconds() / 3600) if latest else 0
        rates = [x["rate"] for x in rows[-1:] if x["rate"] is not None] + [(latest or {}).get("resource_rate_usd_per_hour") or 0]
        projected = (latest["credit_used"] + max(rates) * hours_left) if latest else None
        return render(request, "spend.html", nav="spend", run=None, latest=latest, rows=rows[::-1],
                      projected=projected, hours_left=hours_left, per_supplier=per_supplier, history_path=str(path))

    @app.get("/approvals", response_class=HTMLResponse)
    def approvals(request: Request, done: str = "", error: str = ""):
        require_approver(request)
        items = investigate.approvals(case)
        return render(request, "approvals.html", nav="approvals", run=None, items=items, done=done, error=error)

    def review_page(request: Request, item, error: str = "", reason: str = "") -> HTMLResponse:
        docs = investigate.load_artifacts(case, item)
        paths = [{"path": p, "exists": case.exists(p)} for p in investigate.artifact_paths(item)]
        gen = item.meta.get("generated_by") or next((d.get("generated_by") for d in docs.values() if d.get("generated_by")), None)
        shot = item.meta.get("screenshot_key") if item.checkpoint == "action" else None
        has_screenshot = bool(shot) and settings.store.bronze(str(shot)) is not None
        return render(request, "approval.html", nav="approvals", run=None, a=item, docs=docs, paths=paths,
                      who=identity(request), error=error, gen=gen, backend=(gen or {}).get("backend"),
                      taxonomy_stats=investigate.taxonomy_stats, has_screenshot=has_screenshot,
                      history=investigate.revision_history(docs), drafts=investigate.archived_drafts(case, item),
                      reason=reason, reason_max=investigate.DENY_REASON_MAX)

    @app.get("/approvals/{phase_dir:path}", response_class=HTMLResponse)
    def approval_detail(request: Request, phase_dir: str, error: str = ""):
        require_approver(request)
        item = next((a for a in investigate.approvals(case) if a.phase_dir == phase_dir), None)
        if not item:
            raise HTTPException(404, f"no approval checkpoint in {phase_dir}")
        return review_page(request, item, error)

    @app.post("/approvals")
    async def approve(request: Request):
        require_approver(request)
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "cross-origin approval refused")
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        phase_dir = form.get("phase_dir", "")
        decisions = {k.removeprefix("decision."): v for k, v in form.items() if k.startswith("decision.")}
        try:
            investigate.approve(case, phase_dir, form.get("approver", ""), decisions=decisions or None,
                                decision=form.get("decision"), reason=form.get("reason"))
        except investigate.ReasonRequired as exc:  # v0.9.5: a deny without a reason is a bad request, nothing written
            item = next(a for a in investigate.approvals(case) if a.phase_dir == phase_dir)
            response = review_page(request, item, str(exc), reason=form.get("reason", "")[:5000])
            response.status_code = 400
            return response
        except ValueError as exc:
            back = f"/approvals/{quote(phase_dir)}" if phase_dir and case.exists(phase_dir) else "/approvals"
            return RedirectResponse(f"{back}?error={quote(str(exc))}", status_code=303)
        return RedirectResponse(f"/approvals?done={quote(phase_dir)}", status_code=303)

    def run_view_model(run_id: str, after: int = 0) -> dict:
        steps = live.annotate(settings.store.live_steps(run_id))
        status = settings.store.live_status(run_id)
        if not steps and status is None:
            raise HTTPException(404, f"no live feed for run {run_id}")
        jobs = settings.store.live_jobs(run_id)
        backend = backend_of((status or {}).get("metrics"), [*steps, status or {}])
        panel = live.summarize(steps, status, current_domain())
        known = case.sources()
        for src in panel["sources"]:
            src.setdefault("discovered_by", investigate.discovered_by(src)
                           or (known.get(src.get("source_id")) or {}).get("discovered_by"))
        return {"run_id": run_id, "steps": steps, "new": steps[after:][::-1], "panel": panel,
                "proof": live.proof(jobs, steps), "backend": backend}

    @app.get("/run")
    def run_latest():
        run_id = settings.store.live_run_id()
        if not run_id:
            raise NoGold("No live run feed yet: the engine writes runs/<case_id>/latest.json when a run starts.")
        return RedirectResponse(f"/run/{run_id}", status_code=307)

    @app.get("/run/{run_id}", response_class=HTMLResponse)
    def run_view(request: Request, run_id: str, limit: int = 150):
        m = run_view_model(run_id)
        limit = max(1, min(limit, 2000))
        status = settings.store.live_status(run_id) or {}
        return render(request, "run.html", nav="run", run=None, live_run_id=run_id, m=m, recent=m["new"][:limit],
                      limit=limit,
                      backend=m["backend"], synthetic=settings.store.case_id.startswith("fixture"),
                      preview=bool(status.get("preview") or (status.get("metrics") or {}).get("preview")),
                      PHASES=live.PHASES, MODE_NAMES=live.MODE_NAMES,
                      CHECKPOINT_PHASE=live.CHECKPOINT_PHASE, others=settings.store.live_run_ids())

    @app.get("/api/run/{run_id}")
    def run_api(request: Request, run_id: str, after: int = 0) -> dict:
        m = run_view_model(run_id, max(after, 0))
        env = templates.env
        d = current_domain()
        steps_html = env.get_template("_steps.html").render(steps=m["new"][:150], MODE_NAMES=live.MODE_NAMES)
        panel_html = env.get_template("_run_panel.html").render(
            m=m, PHASES=live.PHASES, CHECKPOINT_PHASE=live.CHECKPOINT_PHASE, MODE_NAMES=live.MODE_NAMES, domain=d)
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
