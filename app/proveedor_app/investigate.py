"""Investigation logic behind the screens: signals, relationships, run diffs, the case journal, approvals."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from .gold import Run


def signals_by_rule(run: Run) -> list[dict]:
    """[{rule_id, label, info, hits: [(entity, index, flag)]}] sorted by number of hits. Rule text comes from the
    ontology's rules (CONTRACT §11a); unknown rule ids fall back to the flag's own label."""
    groups: dict[str, dict] = {}
    for e in run.primary:
        for i, f in enumerate(e.get("flags") or []):
            g = groups.setdefault(f["rule_id"], {"rule_id": f["rule_id"], "label": f["label"], "hits": []})
            g["hits"].append((e, i, f))
    out = sorted(groups.values(), key=lambda g: (-len(g["hits"]), g["rule_id"]))
    for g in out:
        g["info"] = run.domain.rule(g["rule_id"], g["label"])
    return out


def dispute_record(run: Run, entity: dict, flag: dict) -> dict:
    """What the entity's representative would send to contest a signal: the rule, the values and the captures."""
    values = []
    for vid in flag.get("evidence_value_ids") or []:
        ref = run.values.get(vid)
        if ref:
            values.append({"value_id": vid, "entity_id": ref.entity_id, "property": ref.prop,
                           "value": ref.data.get("value"),
                           "evidence": [{"url": e.get("url"), "bronze_key": e.get("bronze_key"),
                                         "captured_at": e.get("captured_at")} for e in ref.data.get("evidence") or []]})
    return {"case_id": run.case_id, "run_id": run.run_id, "entity_id": entity["id"], "rule_id": flag["rule_id"],
            "signal": flag["label"], "values": values,
            "correction": "<what is wrong, and the official document that shows the correct value>"}


# Relationships -------------------------------------------------------------------------------------------------

@dataclass
class Cluster:
    members: list[str]
    edges: list[dict] = field(default_factory=list)  # {a, b, type, via_value_id}

    def layout(self, size: int = 280) -> dict[str, tuple[float, float]]:
        """Deterministic circle layout for a small SVG."""
        n = len(self.members)
        r = 0 if n == 1 else size * 0.36
        c = size / 2
        return {m: (c + r * math.cos(2 * math.pi * i / n - math.pi / 2), c + r * math.sin(2 * math.pi * i / n - math.pi / 2))
                for i, m in enumerate(self.members)}


def cluster_summary(run: Run, cluster: Cluster) -> list[dict]:
    """What connects a group, one line per shared value: {type, value, value_id, entity_id, members: [1-based]}."""
    index = {m: i + 1 for i, m in enumerate(cluster.members)}
    lines: dict[tuple, dict] = {}
    for e in cluster.edges:
        ref = run.values.get(e.get("via_value_id") or "")
        shared = ref.data.get("value") if ref else None
        line = lines.setdefault((e["type"], shared), {
            "type": e["type"], "value": shared, "value_id": ref.value_id if ref and shared is not None else None,
            "entity_id": ref.entity_id if ref and shared is not None else None, "members": set(), "pairs": [],
        })
        line["members"].update((index[e["a"]], index[e["b"]]))
        line["pairs"].append((index[e["a"]], index[e["b"]]))
    out = []
    for line in lines.values():
        line["members"] = sorted(line["members"])
        line["pairs"].sort()
        out.append(line)
    order = {t: i for i, t in enumerate(run.domain.relations)}
    return sorted(out, key=lambda x: (order.get(x["type"], 99), x["members"]))


def clusters(run: Run, types: tuple[str, ...]) -> list[Cluster]:
    """Connected components over the chosen relations between primary entities, largest first. Edges are
    deduplicated (a-b == b-a)."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    primary = {e["id"] for e in run.primary}
    edges: dict[tuple, dict] = {}
    for e in run.primary:
        for link in e.get("links") or []:
            if link.get("property") not in types or link.get("target") not in primary:
                continue
            a, b = sorted((e["id"], link["target"]))
            key = (a, b, link["property"])
            if key not in edges:
                edges[key] = {"a": a, "b": b, "type": link["property"], "via_value_id": link.get("via_value_id")}
            parent[find(a)] = find(b)
    groups: dict[str, Cluster] = {}
    for e in edges.values():
        root = find(e["a"])
        cl = groups.setdefault(root, Cluster(members=[]))
        cl.edges.append(e)
        for m in (e["a"], e["b"]):
            if m not in cl.members:
                cl.members.append(m)
    for cl in groups.values():
        cl.members.sort()
    return sorted(groups.values(), key=lambda c: (-len(c.members), c.members[0]))


# Watchlist: what changed between two runs ------------------------------------------------------------------------

def diff_entity(old: dict | None, new: dict | None) -> list[dict]:
    """Human-readable changes for one entity between two runs."""
    if new is None:
        return [{"kind": "gone", "text": "No longer in the latest run"}]
    if old is None:
        return [{"kind": "new", "text": "First appears in this run"}]
    changes = []
    op, np_ = old.get("properties") or {}, new.get("properties") or {}
    for name in sorted(set(op) | set(np_)):
        a, b = op.get(name) or {}, np_.get(name) or {}
        if a.get("value") != b.get("value") or a.get("status") != b.get("status"):
            changes.append({"kind": "field", "field": name, "before": a.get("value"), "after": b.get("value"),
                            "status_before": a.get("status"), "status_after": b.get("status"),
                            "value_id": b.get("value_id")})
    old_rules = {f["rule_id"] for f in old.get("flags") or []}
    for f in new.get("flags") or []:
        if f["rule_id"] not in old_rules:
            changes.append({"kind": "signal", "text": f["label"]})
    new_rules = {f["rule_id"] for f in new.get("flags") or []}
    for f in old.get("flags") or []:
        if f["rule_id"] not in new_rules:
            changes.append({"kind": "signal_cleared", "text": f["label"]})
    old_links = {(x.get("property"), x.get("target")) for x in old.get("links") or []}
    added = [x for x in new.get("links") or [] if (x.get("property"), x.get("target")) not in old_links]
    if added:
        changes.append({"kind": "links", "text": f"{len(added)} new link{'s' if len(added) > 1 else ''}"})
    return changes


# Case journal ----------------------------------------------------------------------------------------------------

PHASE_NAMES = {1: "Scope", 2: "Ontology", 3: "Fan out", 4: "Local scoping", 5: "Execute"}


def discovered_by(record: dict | None) -> str | None:
    """How a source was found: `discovered_by` (contract), else the engine's earlier `discovery_provider`."""
    record = record or {}
    value = record.get("discovered_by") or record.get("discovery_provider")
    if isinstance(value, dict):  # tolerate a structured form, e.g. {"provider": ..., "detail": ...}
        value = value.get("provider") or value.get("name") or ", ".join(f"{k}: {v}" for k, v in value.items())
    return str(value) if value else None


class CaseDir:
    """Read-only, path-safe access to a case package directory."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def path(self, rel: str) -> Path | None:
        p = (self.root / rel).resolve()
        return p if p.is_relative_to(self.root) else None

    def read(self, rel: str | None, limit: int = 6000) -> str | None:
        p = self.path(rel) if rel else None
        if not p or not p.is_file():
            return None
        text = p.read_text(errors="replace")
        return text if len(text) <= limit else text[:limit] + "\n…"

    def exists(self, rel: str) -> bool:
        p = self.path(rel)
        return bool(p and p.exists())

    def latest(self, pattern: str) -> str | None:
        found = sorted(self.root.glob(pattern))
        return str(found[-1].relative_to(self.root)) if found else None

    def objectives(self) -> list[dict]:
        text = self.read("03-fanout/objectives.yaml", limit=10**7)
        if not text:
            return []
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return []
        items = data.get("objectives", []) if isinstance(data, dict) else data or []
        return [o for o in items if isinstance(o, dict)]

    def sources(self) -> dict[str, dict]:
        """source_id -> {url, source_type, discovered_by, objectives} from the Phase 3 objectives."""
        out: dict[str, dict] = {}
        for o in self.objectives():
            sid = o.get("source_id")
            if not sid:
                continue
            s = out.setdefault(sid, {"source_id": sid, "url": o.get("source_url"), "source_type": o.get("source_type"),
                                     "discovered_by": discovered_by(o), "objectives": []})
            s["objectives"].append(o.get("id"))
        return out

    def objective(self, objective_id: str | None, source_id: str | None = None) -> dict | None:
        text = self.read("03-fanout/objectives.yaml", limit=10**6)
        if not text or not objective_id:
            return None
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return None
        items = data.get("objectives", []) if isinstance(data, dict) else data or []
        matches = [o for o in items if isinstance(o, dict) and o.get("id") == objective_id]
        return next((o for o in matches if o.get("source_id") == source_id), matches[0] if matches else None)

    def anchors(self) -> list[dict]:
        """The documents every value ultimately rests on, newest version where versioned."""
        docs = [("Brief", "brief.md"), ("Global PRD", "01-scope/prd.md")]
        onto = self.latest("02-ontology/versions/*")
        if onto:
            docs.append(("Ontology", onto))
        docs.append(("Objectives", "03-fanout/objectives.yaml"))
        return [{"label": label, "path": rel, "exists": self.exists(rel)} for label, rel in docs]


def journal_chain(run: Run, case: CaseDir, value_id: str) -> list[dict]:
    """One replay per producing step: value -> steps (phase 5 .. 1) with their TDD / objective documents."""
    replays = []
    for chain in run.lineage(value_id):
        stops = []
        for step in chain:
            stop = {"step": step, "phase_name": PHASE_NAMES.get(step.get("phase"), "?"), "docs": []}
            if step.get("tdd_path") and step.get("phase") == 4:
                stop["docs"].append({"label": "Technical definition document", "path": step["tdd_path"],
                                     "text": case.read(step["tdd_path"], limit=1800)})
            if step.get("phase") == 3 and step.get("objective_id"):
                stop["objective"] = case.objective(step["objective_id"], step.get("source_id"))
                stop["discovered_by"] = discovered_by(stop["objective"])
            stops.append(stop)
        replays.append(stops)
    return replays


# Approvals -------------------------------------------------------------------------------------------------------

CHECKPOINTS = ("prd", "factors", "ontology")
_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class Approval:
    phase_dir: str  # relative to the case dir, e.g. "01-scope"
    pending_text: str
    meta: dict
    approved: dict | None

    @property
    def checkpoint(self) -> str | None:
        cp = self.meta.get("checkpoint")
        if cp in CHECKPOINTS:
            return cp
        return {"01-scope": "prd", "02-ontology": "ontology"}.get(self.phase_dir)


def _front_matter(text: str) -> dict:
    """Structured metadata inside APPROVAL_PENDING.md: YAML front matter or a ```json block."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            try:
                data = yaml.safe_load(text[3:end])
                if isinstance(data, dict):
                    return data
            except yaml.YAMLError:
                pass
    m = _JSON_BLOCK.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    return {}


def approvals(case: CaseDir) -> list[Approval]:
    out = []
    if not case.root.is_dir():
        return out
    for pending in sorted(case.root.glob("*/APPROVAL_PENDING.md")) + sorted(case.root.glob("*/*/APPROVAL_PENDING.md")):
        rel_dir = str(pending.parent.relative_to(case.root))
        text = pending.read_text(errors="replace")
        approved_path = pending.parent / "APPROVED"
        approved = None
        if approved_path.is_file():
            try:
                approved = json.loads(approved_path.read_text())
            except ValueError:
                approved = {"approver": approved_path.read_text().strip()[:200], "date": None}
        out.append(Approval(rel_dir, text, _front_matter(text), approved))
    return out


DEFAULT_ARTIFACTS = {"prd": ["01-scope/prd.json"], "factors": ["02-ontology/factors/factors.json"],
                     "ontology": ["02-ontology/ontology.json"]}


def artifact_paths(item: Approval) -> list[str]:
    return list(item.meta.get("artifact_paths") or DEFAULT_ARTIFACTS.get(item.checkpoint or "", []))


def load_artifacts(case: CaseDir, item: Approval) -> dict:
    """The JSON documents a checkpoint asks the approver to review, keyed by kind (prd | factors | ontology)."""
    docs: dict = {}
    for rel in artifact_paths(item):
        if not rel.endswith(".json"):
            continue
        text = case.read(rel, limit=10**7)
        try:
            doc = json.loads(text) if text else None
        except ValueError:
            doc = None
        if not isinstance(doc, dict):
            continue
        if "definition_of_done" in doc:
            docs["prd"] = doc
        elif "taxonomies" in doc:
            docs["ontology"] = doc
        elif "factors" in doc:
            docs["factors"] = doc
    return docs


def taxonomy_stats(tax: dict) -> dict:
    """Nodes per level and critic-label counts for one taxonomy (the numbers the approver signs off on)."""
    levels: dict[int, int] = {}
    critic: dict[str, int] = {}

    def walk(nodes):
        for n in nodes or []:
            levels[n.get("level", 0)] = levels.get(n.get("level", 0), 0) + 1
            critic[n.get("critic_label", "?")] = critic.get(n.get("critic_label", "?"), 0) + 1
            walk(n.get("children"))

    walk(tax.get("children"))
    return {"levels": dict(sorted(levels.items())), "critic": critic, "nodes": sum(levels.values())}


def approve(case: CaseDir, phase_dir: str, approver: str, today: date | None = None,
            decisions: dict[str, str] | None = None) -> dict:
    """Write the APPROVED marker next to a pending checkpoint. Raises ValueError when the request is invalid."""
    approver = " ".join(approver.split())[:120]
    if not approver:
        raise ValueError("approver name is required")
    target = case.path(phase_dir)
    if not target or target == case.root or not (target / "APPROVAL_PENDING.md").is_file():
        raise ValueError(f"no pending approval in {phase_dir!r}")
    marker = target / "APPROVED"
    if marker.exists():
        raise ValueError(f"{phase_dir} is already approved")
    item = next(a for a in approvals(case) if a.phase_dir == phase_dir)
    record: dict = {"approver": approver, "date": (today or datetime.now(UTC).date()).isoformat()}
    if item.checkpoint:
        record["checkpoint"] = item.checkpoint
    if decisions:
        if item.checkpoint != "factors":
            raise ValueError("per-factor decisions only apply to the factors checkpoint")
        factors = (load_artifacts(case, item).get("factors") or {}).get("factors") or []
        known = {f["id"] for f in factors if isinstance(f, dict) and f.get("id")}
        if set(decisions) != known:
            raise ValueError("decide every proposed factor, and only those")
        if any(v not in ("accept", "reject") for v in decisions.values()):
            raise ValueError("each factor decision must be accept or reject")
        if "accept" not in decisions.values():
            raise ValueError("accept at least one factor, or ask the engine to propose new ones")
        record["decisions"] = dict(sorted(decisions.items()))
    elif item.checkpoint == "factors" and (load_artifacts(case, item).get("factors") or {}).get("factors"):
        raise ValueError("decide each factor (accept or reject) before approving")
    with marker.open("x") as fh:  # never overwrite a concurrent approval
        json.dump(record, fh)
        fh.write("\n")
    return record
