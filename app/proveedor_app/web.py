"""FastAPI app: server-rendered investigation screens over one gold export."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import CORE_FIELDS, dod
from .gold import GoldStore, Run, load_store, sniff_media_type

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
    store: GoldStore
    case_dir: Path
    role: str = "investigator"

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"PA_ROLE must be one of {ROLES}, got {self.role!r}")


def settings_from_env() -> Settings:
    return Settings(
        store=load_store(REPO_ROOT),
        case_dir=Path(os.environ.get("PA_CASE_DIR", REPO_ROOT / "case")),
        role=os.environ.get("PA_ROLE", "investigator"),
    )


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
            raise HTTPException(503, str(exc)) from exc

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        ctx.setdefault("nav", "")
        return templates.TemplateResponse(request, name, ctx)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "role": settings.role, "case_id": settings.store.case_id}

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

    @app.get("/bronze/{key}")
    def bronze(key: str):
        data = settings.store.bronze(key)
        if data is None:
            raise HTTPException(404, "bronze object not found")
        return Response(
            data,
            media_type=sniff_media_type(data),
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",  # content-addressed
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return app
