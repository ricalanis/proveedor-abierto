"""Evaluation harness: references load with provenance, self-scores are perfect, fixture scores are sane, and the
harness stays out of the engine's reach."""

import json
import re
from pathlib import Path

import pytest
from pa_eval import REFERENCES, rubric, scorer
from pa_eval.cli import main, score_ontology, selfcheck
from pa_eval.taxonomy import REQUIRED_META, Tree, load_reference, reference_as_engine, similarity
from proveedor_app.fixture_case import ONTOLOGY, PRD

ROOT = Path(__file__).resolve().parents[1]
REF_FILES = sorted(p for p in REFERENCES.glob("*.yaml") if p.name != "mapping.yaml")


@pytest.mark.parametrize("path", REF_FILES, ids=lambda p: p.name)
def test_reference_metadata_and_ids(path):
    ref = load_reference(path)
    for key in REQUIRED_META:
        assert key in ref.meta or key == "nodes", key
    assert ref.meta["source_url"].startswith("https://")
    ids = [n.id for n in ref.all_nodes()]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"[a-z][a-z0-9_]*", i) for i in ids)
    assert all(n.code for n in ref.all_nodes())


def test_reference_contents():
    assert len(load_reference(REFERENCES / "scian_2023_sectors.yaml").nodes) == 20
    entities = load_reference(REFERENCES / "inegi_federal_entities.yaml").nodes
    assert len(entities) == 32 and {n.code for n in entities} == {f"{i:02d}" for i in range(1, 33)}
    assert len(load_reference(REFERENCES / "laassp_procedures.yaml").nodes) == 7


def test_mapping_points_at_existing_references():
    import yaml

    mapping = yaml.safe_load((REFERENCES / "mapping.yaml").read_text())
    assert all((REFERENCES / f).is_file() for f in mapping.values())


def test_selfcheck_is_perfect():
    assert selfcheck() and all(v == 1.0 for v in selfcheck().values())
    assert main(["selfcheck"]) == 0


def test_self_score_details():
    ref = load_reference(REFERENCES / "laassp_procedures.yaml")
    s = scorer.score(reference_as_engine(ref), ref)
    assert s["completeness"] == 1.0 and s["soundness"] == 1.0 and s["novelty"] == 0.0 and not s["gaps"]


def test_fixture_ontology_scores(tmp_path):
    path = tmp_path / "ontology.json"
    path.write_text(json.dumps(ONTOLOGY))
    scores = score_ontology(path)
    proc = scores["procedure_type"]
    # The fixture has the classic three procedures; the 2025 LAASSP (art. 35) lists seven.
    assert proc["completeness"] == pytest.approx(3 / 7, abs=1e-3)
    assert {m["reference"] for m in proc["matches"]} == {"licitacion_publica", "invitacion_tres", "adjudicacion_directa"}
    assert proc["soundness"] == 1.0 and proc["novelty"] == 0.0
    sector = scores["economic_sector"]
    assert 0 < sector["completeness"] < 0.5 and 0 < sector["soundness"] < 1
    assert {f["critic_label"] for f in sector["flagged"]} == {"Bad", "Redundant"}
    assert sector["coverage"] == pytest.approx(sector["completeness"] + sector["novelty"], abs=1e-3)
    assert main(["score", "--ontology", str(path), "--json"]) == 0


def test_unmapped_factor_gets_soundness_only(tmp_path):
    onto = dict(ONTOLOGY, taxonomies=[dict(ONTOLOGY["taxonomies"][0], factor_id="red_flag_type")])
    path = tmp_path / "o.json"
    path.write_text(json.dumps(onto))
    s = score_ontology(path)["red_flag_type"]
    assert s["reference"] is None and "completeness" not in s


def test_matcher_accents_aliases_and_threshold():
    from pa_eval.taxonomy import Node

    ref = Node(id="adjudicacion_directa", label="Adjudicación directa", level=1, aliases=["direct award"])
    assert similarity(Node(id="x", label="ADJUDICACION DIRECTA", level=1), ref) == (1.0, "exact")
    assert similarity(Node(id="y", label="Direct award", level=1), ref)[0] == 1.0
    assert similarity(Node(id="z", label="Obra pública", level=1), ref)[0] < 0.6
    assert scorer.score(Tree("e", []), Tree("r", [ref]))["completeness"] == 0.0


def test_rubric_on_fixture_prd():
    report = rubric.evaluate(PRD)
    p, s = report["personas"], report["signals"]
    for key in ("investigative_journalist", "civil_society_watchdog", "auditor_or_researcher"):
        assert p[key]["status"] == "found", key
    assert p["procurement_officer"]["status"] == "missing"
    for key in ("tax_authority_list", "sanctions", "shared_address_or_representative"):
        assert s[key]["status"] == "found", key
    assert s["new_company_before_award"]["status"] == "partial"  # only a founding-date field
    assert report["alternative_personas"] == []
    assert "consistent" in report["summary"]["verdict"]
    assert "| Sanctions | found |" in rubric.to_markdown(report)


def test_rubric_alternative_personas_are_not_failures():
    prd = dict(PRD, personas=[{"id": "compliance_bank", "description": "Bank compliance analyst screening clients"}])
    report = rubric.evaluate(prd)
    assert report["alternative_personas"][0]["id"] == "compliance_bank"
    assert "can still be a success" in report["summary"]["verdict"]


def test_harness_is_out_of_the_engines_reach():
    """case/ (what the engine reads and writes) never references the harness. In app/, only the read-only
    report card module may import it: the app is the judge's view, not the engine."""
    allowed = {"app/proveedor_app/report.py"}
    offenders = []
    for base in ("app", "case"):
        for path in (ROOT / base).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".html", ".js", ".toml"}:
                text = path.read_text(errors="ignore")
                rel = str(path.relative_to(ROOT))
                if re.search(r"\bpa_eval\b|eval/references", text) and rel not in allowed:
                    offenders.append(rel)
    assert not offenders, offenders
    report = (ROOT / "app/proveedor_app/report.py").read_text()
    assert "write_text" not in report and "open(" not in report  # read-only use
