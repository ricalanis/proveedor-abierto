"""Simula-style taxonomy evaluation (Davidson et al., Simula, TMLR 2026, App. B.1-B.3; see
docs/planning/01-engine-definition.md, "2c. Taxonomy evaluation") of an engine taxonomy against an official
reference classification.

Paper definitions, with the reference taken as all-good:
  completeness = Good-Overlapping / Total-Good(reference)
  soundness    = Total-Good(generated) / Total-Nodes(generated)
  novelty      = Good-Exclusive(generated) / Total-Good(reference)
  coverage     = completeness + novelty

"Good" comes from the engine's own critic labels (Good-Overlapping / Good-Exclusive). "Overlapping" is decided
here, deterministically, by matching against the reference (taxonomy.similarity), and completeness counts
distinct reference nodes hit, so two engine nodes matching one reference node count once. Where the engine's
critic and this matcher disagree on overlap, the disagreement is listed rather than resolved.
"""

from __future__ import annotations

from .taxonomy import Node, Tree, similarity

GOOD = ("Good-Overlapping", "Good-Exclusive")


def _is_good(node: Node) -> bool:
    return node.critic_label in GOOD or node.critic_label is None  # unlabelled nodes are counted, and reported


def score(engine: Tree, reference: Tree, threshold: float = 0.6) -> dict:
    eng_nodes = engine.all_nodes()
    ref_nodes = reference.all_nodes()
    matches = []
    hit: dict[str, list[str]] = {}
    matched_engine: set[str] = set()
    for e in eng_nodes:
        best, best_ref, method = 0.0, None, "none"
        for r in ref_nodes:
            s, m = similarity(e, r)
            if s > best:
                best, best_ref, method = s, r, m
        if best_ref is not None and best >= threshold:
            matched_engine.add(e.id)
            matches.append({"engine": e.id, "engine_label": e.label, "reference": best_ref.id,
                            "reference_label": best_ref.label, "code": best_ref.code, "score": round(best, 3),
                            "method": method, "critic_label": e.critic_label})
            if _is_good(e):
                hit.setdefault(best_ref.id, []).append(e.id)

    total_ref = len(ref_nodes) or 1
    good = [e for e in eng_nodes if _is_good(e)]
    good_exclusive = [e for e in good if e.id not in matched_engine]
    levels = sorted({r.level for r in ref_nodes})
    per_level = []
    for lv in levels:
        at = [r for r in ref_nodes if r.level == lv]
        per_level.append(round(sum(r.id in hit for r in at) / len(at), 4))
    completeness = len(hit) / total_ref
    novelty = len(good_exclusive) / total_ref
    disagreements = [
        {"engine": e.id, "label": e.label, "critic_label": e.critic_label,
         "matcher": "overlaps reference" if e.id in matched_engine else "no reference match"}
        for e in eng_nodes
        if (e.critic_label == "Good-Overlapping" and e.id not in matched_engine)
        or (e.critic_label == "Good-Exclusive" and e.id in matched_engine)
    ]
    return {
        "reference": reference.name,
        "threshold": threshold,
        "engine_nodes": len(eng_nodes),
        "reference_nodes": len(ref_nodes),
        "completeness": round(completeness, 4),
        "completeness_per_level": per_level,
        "soundness": round(len(good) / len(eng_nodes), 4) if eng_nodes else 0.0,
        "grounded_soundness": round(
            sum(1 for e in eng_nodes if e.id in matched_engine or _is_good(e)) / len(eng_nodes), 4
        ) if eng_nodes else 0.0,
        "novelty": round(novelty, 4),
        "coverage": round(completeness + novelty, 4),
        "unlabelled_nodes": sum(1 for e in eng_nodes if e.critic_label is None),
        "matches": matches,
        "gaps": [{"id": r.id, "label": r.label, "code": r.code, "level": r.level}
                 for r in ref_nodes if r.id not in hit],
        "flagged": [{"id": e.id, "label": e.label, "critic_label": e.critic_label}
                    for e in eng_nodes if e.critic_label in ("Bad", "Redundant")],
        "critic_disagreements": disagreements,
        "engine_reported": engine.meta or {},
    }


def soundness_only(engine: Tree) -> dict:
    """For conceptual or unmapped factors: no reference, so only the critic's soundness and flagged nodes."""
    nodes = engine.all_nodes()
    good = [e for e in nodes if _is_good(e)]
    return {
        "reference": None,
        "engine_nodes": len(nodes),
        "soundness": round(len(good) / len(nodes), 4) if nodes else 0.0,
        "flagged": [{"id": e.id, "label": e.label, "critic_label": e.critic_label}
                    for e in nodes if e.critic_label in ("Bad", "Redundant")],
        "engine_reported": engine.meta or {},
    }
