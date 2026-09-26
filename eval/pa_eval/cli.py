"""`pa-eval`: score engine output against official references. Never run by, or wired into, the engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import REFERENCES, rubric, scorer
from .taxonomy import load_engine_taxonomies, load_reference, reference_as_engine


def load_mapping(path: Path) -> dict[str, str]:
    return yaml.safe_load(path.read_text()) or {}


def score_ontology(ontology: Path, mapping_path: Path = REFERENCES / "mapping.yaml", threshold: float = 0.6) -> dict:
    mapping = load_mapping(mapping_path)
    out = {}
    for factor_id, tree in load_engine_taxonomies(ontology):
        ref_file = mapping.get(factor_id)
        if ref_file:
            out[factor_id] = scorer.score(tree, load_reference(mapping_path.parent / ref_file), threshold)
            out[factor_id]["reference_file"] = ref_file
        else:
            out[factor_id] = scorer.soundness_only(tree)
    return out


def selfcheck(references: Path = REFERENCES) -> dict:
    results = {}
    for path in sorted(references.glob("*.yaml")):
        if path.name == "mapping.yaml":
            continue
        ref = load_reference(path)
        results[path.name] = scorer.score(reference_as_engine(ref), ref)["completeness"]
    return results


def _print_scores(scores: dict) -> None:
    for factor_id, s in scores.items():
        if s.get("reference") is None:
            print(f"{factor_id}: no official reference (conceptual or unmapped); critic soundness {s['soundness']:.2f}")
        else:
            print(f"{factor_id} vs {s['reference_file']}: completeness {s['completeness']:.2f} "
                  f"(per level {s['completeness_per_level']}), soundness {s['soundness']:.2f}, "
                  f"novelty {s['novelty']:.2f}, coverage {s['coverage']:.2f}")
            if s["gaps"]:
                print(f"  gaps: {', '.join(g['label'] for g in s['gaps'][:8])}{' …' if len(s['gaps']) > 8 else ''}")
        if s["flagged"]:
            print(f"  flagged by the critic: {', '.join(f['label'] + ' (' + f['critic_label'] + ')' for f in s['flagged'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa-eval", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("score", help="Simula completeness/soundness/novelty of an engine ontology.json")
    p.add_argument("--ontology", required=True, type=Path)
    p.add_argument("--mapping", type=Path, default=REFERENCES / "mapping.yaml")
    p.add_argument("--threshold", type=float, default=0.6)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("rubric", help="check an engine PRD (prd.json) against the 02 hypotheses")
    p.add_argument("--prd", required=True, type=Path)
    p.add_argument("--json", action="store_true")
    sub.add_parser("selfcheck", help="every reference scored against itself must reach completeness 1.0")
    args = parser.parse_args(argv)

    if args.cmd == "score":
        scores = score_ontology(args.ontology, args.mapping, args.threshold)
        print(json.dumps(scores, indent=2, ensure_ascii=False)) if args.json else _print_scores(scores)
        return 0
    if args.cmd == "rubric":
        report = rubric.evaluate(json.loads(args.prd.read_text()))
        print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else rubric.to_markdown(report))
        return 0
    results = selfcheck()
    for name, completeness in results.items():
        print(f"{name}: completeness {completeness:.2f}")
    return 0 if all(v == 1.0 for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
