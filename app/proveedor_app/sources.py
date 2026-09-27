"""'Directorio de fuentes': every public source behind published values, read from the gold export, with the
authority decision the case package states for it (Phase 3 `objectives[].authority_tier`, else the global PRD's
`authority_policy`). Nothing here is inferred: a source the case says nothing about is shown as such."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from . import i18n
from .domain import Domain
from .gold import Run
from .investigate import CaseDir

TIERS = ("primary", "secondary", "review", "unknown")


def _host(url: str | None) -> str | None:
    return urlsplit(url or "").hostname or None


def authority_policy(case: CaseDir) -> dict | None:
    """The global PRD's authority_policy, or None when the case has not published one."""
    raw = case.read("01-scope/prd.json", limit=10**6)
    try:
        doc = json.loads(raw) if raw else None
    except ValueError:
        return None
    policy = doc.get("authority_policy") if isinstance(doc, dict) else None
    return policy if isinstance(policy, dict) else None


def _publisher_for(host: str | None, policy: dict | None) -> dict | None:
    """The trusted publisher whose domains cover `host` (exact domain or a subdomain of it)."""
    if not host or not policy:
        return None
    for pub in policy.get("trusted_publishers") or []:
        if not isinstance(pub, dict):
            continue
        for domain in pub.get("domains") or []:
            domain = str(domain).lower().strip(".")
            if host == domain or host.endswith("." + domain):
                return pub
    return None


def authority(source_id: str | None, host: str | None, objectives: dict[str, dict], policy: dict | None) -> dict | None:
    """What the case says about trusting this source: {tier, basis, kind}. `basis` names where it says so:
    'objectives' (a Phase 3 tier), 'trusted' (on the PRD's trusted list), 'unlisted' (not on it: the PRD's
    unknown_source_action applies). None when the case states nothing."""
    tier = (objectives.get(source_id or "") or {}).get("authority_tier")
    pub = _publisher_for(host, policy)
    if tier in TIERS:
        return {"tier": tier, "basis": "objectives", "kind": (pub or {}).get("kind")}
    if pub:
        stated = pub.get("tier")
        return {"tier": stated if stated in TIERS else None, "basis": "trusted", "kind": pub.get("kind")}
    if policy:
        return {"tier": policy.get("unknown_source_action") or "review", "basis": "unlisted", "kind": None}
    return None


def directory(run: Run | None, case: CaseDir, domain: Domain) -> dict:
    """{sources: [...published, most values first], unused: [...found by the case, backing nothing yet],
    value_count: n published values with a receipt, policy: bool}."""
    policy = authority_policy(case)
    found = case.sources()  # source_id -> {url, source_type, discovered_by, objectives}
    objectives: dict[str, dict] = {}
    for o in case.objectives():
        sid = o.get("source_id")
        if sid and o.get("authority_tier") and sid not in objectives:
            objectives[sid] = o
    by_source: dict[str, dict] = {}
    published = set()
    for ref in (run.values.values() if run else []):
        if (ref.data.get("status") or "missing") == "missing":
            continue
        entity = run.entities_by_id.get(ref.entity_id) or {}
        cls = entity.get("class")
        for ev in ref.data.get("evidence") or []:
            host = _host(ev.get("url"))
            key = ev.get("source_id") or host
            if not key:
                continue
            published.add(ref.value_id)
            s = by_source.setdefault(key, {
                "source_id": ev.get("source_id"), "host": host, "url": None, "source_type": ev.get("source_type"),
                "value_ids": set(), "by_prop": {}, "first": None, "last": None, "example": None, "example_rank": (-1, -1),
            })
            s["host"] = s["host"] or host
            s["source_type"] = s["source_type"] or ev.get("source_type")
            if ref.value_id not in s["value_ids"]:
                s["value_ids"].add(ref.value_id)
                label = domain.prop_label(ref.prop, cls)
                if cls and cls != domain.primary_class and label != domain.class_label(cls):
                    label = f"{domain.class_label(cls)} · {label}"
                s["by_prop"][label] = s["by_prop"].get(label, 0) + 1
            ts = i18n.parse_ts(ev.get("captured_at"))
            if ts:
                if s["first"] is None or ts < s["first"][0]:
                    s["first"] = (ts, ev["captured_at"])
                if s["last"] is None or ts > s["last"][0]:
                    s["last"] = (ts, ev["captured_at"])
            rank = (cls == domain.primary_class, bool(ev.get("screenshot_key")))  # a dossier, with a screenshot
            if rank > s["example_rank"]:
                s["example"] = {"entity_id": ref.entity_id, "value_id": ref.value_id,
                                "title": run.title(entity), "prop": domain.prop_label(ref.prop, cls)}
                s["example_rank"] = rank
    rows = []
    for key, s in by_source.items():
        meta = found.get(s["source_id"] or "") or {}
        stype = s["source_type"] or meta.get("source_type")
        rows.append({
            "key": key, "source_id": s["source_id"], "host": s["host"] or _host(meta.get("url")) or key,
            "kind": domain.source_label(stype) if stype else None,
            "backs": len(s["value_ids"]),
            "by_prop": sorted(s["by_prop"].items(), key=lambda kv: (-kv[1], kv[0])),
            "first": s["first"][1] if s["first"] else None, "last": s["last"][1] if s["last"] else None,
            "example": s["example"],
            "authority": authority(s["source_id"], s["host"], objectives, policy),
        })
    rows.sort(key=lambda r: (-r["backs"], r["host"]))
    used = {r["source_id"] for r in rows if r["source_id"]} | {r["host"] for r in rows}
    unused = []
    for sid, meta in found.items():
        host = _host(meta.get("url"))
        if sid in used or (host and host in used):
            continue
        unused.append({"source_id": sid, "host": host or sid,
                       "kind": domain.source_label(meta["source_type"]) if meta.get("source_type") else None,
                       "authority": authority(sid, host, objectives, policy)})
    unused.sort(key=lambda r: r["host"])
    return {"sources": rows, "unused": unused, "value_count": len(published), "policy": bool(policy),
            "unknown_action": (policy or {}).get("unknown_source_action")}
