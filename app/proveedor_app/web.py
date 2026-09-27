"""FastAPI app: server-rendered investigation screens over one gold export."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from . import dod, i18n, investigate
from .domain import LEGACY_ONTOLOGY, Domain
from .gold import GoldStore, Run, UnavailableStore, load_store, sniff_media_type

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent

@dataclass
class Settings:
    store: GoldStore | UnavailableStore
    case_dir: Path


def settings_from_env() -> Settings:
    try:
        store = load_store(REPO_ROOT)
    except (FileNotFoundError, ValueError) as exc:
        store = UnavailableStore(str(exc))
    return Settings(
        store=store,
        case_dir=Path(os.environ.get("PA_CASE_DIR", REPO_ROOT / "case")),
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


WHERE_LABELS = {"html": "Where on the page", "pdf": "Where in the document", "xlsx": "Cell or row in the file",
                "csv": "Row in the file", "json": "Field in the data", "api": "Field in the data"}


def host_of(url: str | None) -> str:
    if not url:
        return ""
    return urlsplit(url).hostname or url


PAGE_SIZE = 25  # browse list rows per page

STATUS_WORDS = {"gold": "Confirmed", "conflict": "Sources disagree", "missing": "Not found"}
TIER_WORDS = {"primary": "Primary source", "secondary": "Secondary source", "review": "Used after review",
              "unknown": "Tier not decided"}


def confidence_level(confidence) -> str:
    """Confidence in words for readers: high (>= 0.9), medium (>= 0.7), low, unknown."""
    if not isinstance(confidence, (int, float)):
        return "unknown"
    return "high" if confidence >= 0.9 else "medium" if confidence >= 0.7 else "low"


def dataset_stats(r: Run) -> dict:
    """Plain numbers for the home page: all recomputed from the gold export in hand."""
    d = r.domain
    complete = sum(dod.dod_ratio(e, d) >= d.dod_threshold for e in r.primary)
    sources, latest = set(), None
    for ref in r.values.values():
        for ev in ref.data.get("evidence") or []:
            if ev.get("source_id"):
                sources.add(ev["source_id"])
            ts = i18n.parse_ts(ev.get("captured_at"))
            if ts and (latest is None or ts > latest[0]):
                latest = (ts, ev["captured_at"])
    total = len(r.primary)
    return {"total": total, "complete": complete, "complete_ratio": complete / total if total else 0.0,
            "flagged": sum(1 for e in r.primary if e.get("flags")), "sources": len(sources),
            "latest": latest[1] if latest else None}


def safe_url(url: str | None) -> str | None:
    """Only http(s) evidence links become clickable."""
    return url if url and urlsplit(url).scheme in ("http", "https") else None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    app = FastAPI(title="Proveedor Abierto", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    env = templates.env
    env.globals.update(
        host_of=host_of,
        WHERE_LABELS=WHERE_LABELS,
        TIER_WORDS=TIER_WORDS,
        safe_url=safe_url,
    )
    env.filters["pct"] = lambda x: f"{round((x or 0) * 100)}%"
    env.filters["money"] = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else (x or "—")
    env.filters["brief"] = brief
    env.filters["sentence"] = lambda s: s[:1].upper() + s[1:] if s else s
    env.filters["date"] = pass_context(lambda ctx, v: i18n.date_label(v, ctx.get("lang", i18n.DEFAULT_LANG)))
    env.filters["datetime"] = pass_context(
        lambda ctx, v: i18n.date_label(v, ctx.get("lang", i18n.DEFAULT_LANG), with_time=True))

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
        asked = request.query_params.get("lang")
        lang = i18n.pick_lang(asked, request.cookies.get(i18n.COOKIE))
        _ = i18n.translator(lang)
        other = "en" if lang == "es" else "es"
        query = [(k, v) for k, v in request.query_params.multi_items() if k != "lang"] + [("lang", other)]
        ctx.update(lang=lang, other_lang=other, lang_href=f"{request.url.path}?{urlencode(query)}", _=_,
                   ngettext=i18n.ngettext(lang), status_word=lambda s: _(STATUS_WORDS.get(s or "missing", s or "")),
                   confidence_word=lambda c: _(confidence_level(c)), lang_param=asked in i18n.LANGS)
        ctx.setdefault("nav", "")
        r = ctx.get("run")
        ctx.setdefault("domain", (r.domain if r else current_domain()).localized(lang))
        labels = i18n.ONTOLOGY_LABELS.get(lang) or {}
        # a flag's title in the reader's language when the app knows its rule; its explanation stays as exported
        ctx["flag_label"] = lambda f: (labels.get(f.get("rule_id")) or {}).get("label") or f.get("label")
        ctx.setdefault("backend", r.inference_backend if r else None)
        ctx.setdefault("synthetic", bool(r and r.case_id.startswith("fixture")))
        ctx.setdefault("preview", bool(r and r.metrics.get("preview")))
        response = templates.TemplateResponse(request, name, ctx)
        if asked in i18n.LANGS and asked != request.cookies.get(i18n.COOKIE):
            response.set_cookie(i18n.COOKIE, asked, max_age=365 * 24 * 3600, samesite="lax")
        return response

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
        # "investigator" = read-only; kept so deploy checks keep working (operator and approver work is in the console)
        return {"ok": True, "role": "investigator", "run_id": run_id}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, q: str = "", show: str = "all", page: int = 1):
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
            conflicts = sum(1 for v in props.values() if isinstance(v, dict) and v.get("status") == "conflict")
            has_conflict = conflicts > 0
            if show == "signals" and not e.get("flags"):
                continue
            if show == "incomplete" and ratio >= d.dod_threshold:
                continue
            if show == "conflicts" and not has_conflict:
                continue
            rows.append({"e": e, "ratio": ratio, "props": props, "conflicts": conflicts,
                         "filled": sum(1 for p in d.dod_props() if dod.is_filled(props.get(p.id))),
                         "linked": sum(1 for link in e.get("links") or [] if link.get("target") in r.entities_by_id
                                       and r.entities_by_id[link["target"]].get("class") != d.primary_class)})
        rows.sort(key=lambda row: (-len(row["e"].get("flags") or []), r.title(row["e"])))
        pages = max(1, -(-len(rows) // PAGE_SIZE))
        page = min(max(page, 1), pages)
        return render(request, "index.html", nav="entities", run=r, rows=rows[(page - 1) * PAGE_SIZE: page * PAGE_SIZE],
                      matched=len(rows), page=page, pages=pages, q=q, show=show, stats=dataset_stats(r))

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
        filled = sum(1 for p in d.dod_props(e.get("class")) if dod.is_filled(props.get(p.id)))
        sources = {ev.get("source_id") or ev.get("url") for f in props.values() if isinstance(f, dict)
                   for ev in f.get("evidence") or []}
        return render(request, "dossier.html", nav="entities", run=r, e=e, props=props, order=order,
                      peers=peers, related=related, ratio=dod.dod_ratio(e, d), selected=selected, filled=filled,
                      source_count=len(sources - {None}), ptypes={p.id: p.datatype for p in d.props(e.get("class"))})

    @app.get("/fragments/evidence/{value_id}", response_class=HTMLResponse)
    def evidence_fragment(request: Request, value_id: str):
        r = run(request)
        ref = r.values.get(value_id)
        if not ref:
            raise HTTPException(404, f"no value {value_id}")
        return render(request, "_evidence.html", run=r, selected=ref)

    def completeness_model(r: Run, lang: str = i18n.DEFAULT_LANG) -> dict:
        d = r.domain.localized(lang)
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
        complete = sum(dod.dod_ratio(e, d) >= d.dod_threshold for e in r.primary)
        conflicts = sum(1 for e in r.primary for v in (e.get("properties") or {}).values()
                        if isinstance(v, dict) and v.get("status") == "conflict")
        return {
            "complete": complete, "complete_ratio": complete / total if total else 0.0,
            "gaps": sorted((f for f in fields if f["ratio"] < d.dod_threshold), key=lambda f: f["ratio"])[:3],
            "without_evidence": recomputed.get("values_without_evidence", 0), "conflicts": conflicts,
            "source_classes": recomputed.get("distinct_source_classes", 0),
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
        lang = i18n.pick_lang(request.query_params.get("lang"), request.cookies.get(i18n.COOKIE))
        return render(request, "completeness.html", nav="completeness", run=r, m=completeness_model(r, lang))

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
        lang = i18n.pick_lang(request.query_params.get("lang"), request.cookies.get(i18n.COOKIE))
        return render(request, "signal.html", nav="signals", run=r, e=e, flag=flag, refs=refs,
                      info=r.domain.localized(lang).rule(flag["rule_id"], flag["label"]), dispute=dispute)

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

    @app.get("/case-file", response_class=HTMLResponse)
    def case_file(request: Request, path: str):
        text = case.read(path, limit=200_000)
        if text is None:
            raise HTTPException(404, "not in the case package")
        return render(request, "case_file.html", nav="journal", run=None, path=path, text=text)

    @app.get("/about", response_class=HTMLResponse)
    def about(request: Request):
        try:
            r = settings.store.run(request.query_params.get("run"))
        except LookupError:
            r = None
        return render(request, "about.html", nav="about", run=r, sources=list(case.sources().values()),
                      latest=dataset_stats(r)["latest"] if r else None)

    @app.get("/como-se-hizo", response_class=HTMLResponse)
    @app.get("/how-it-was-made", response_class=HTMLResponse, include_in_schema=False)
    def how_it_was_made(request: Request):
        from . import method

        try:
            r = settings.store.run(request.query_params.get("run"))
        except LookupError:
            r = None
        lang = i18n.pick_lang(request.query_params.get("lang"), request.cookies.get(i18n.COOKIE))
        d = (r.domain if r else current_domain()).localized(lang)
        return render(request, "method.html", nav="method", run=r, m=method.build(r, case, d))

    @app.get("/fuentes", response_class=HTMLResponse)
    @app.get("/sources", response_class=HTMLResponse, include_in_schema=False)
    def source_directory(request: Request):
        from . import sources

        try:
            r = settings.store.run(request.query_params.get("run"))
        except LookupError:
            r = None
        lang = i18n.pick_lang(request.query_params.get("lang"), request.cookies.get(i18n.COOKIE))
        d = (r.domain if r else current_domain()).localized(lang)
        return render(request, "sources.html", nav="sources", run=r, m=sources.directory(r, case, d))

    @app.get("/data", response_class=HTMLResponse)
    def open_data(request: Request):
        from . import export as ex

        r = run(request)
        return render(request, "data.html", nav="data", run=r, ocds=ex.ocds_available(r))

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
