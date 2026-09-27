"""/evidence renders the track checklist with proof from saved files only (no API calls, no probing)."""

from proveedor_app import evidence

VERIFY_OUT = """remote checks
  PASS  VM port 22 closed
  PASS  VM port 8400 closed
  PASS  unauthenticated https://inv.example refused (HTTP 401, no app content)
  WARN  PA_INVESTIGATOR_COOKIE not set: skipped the authenticated role-boundary check (covered by local mode)
RESULT: PASS
"""


def test_checklist_rows_parse_the_requirement_table():
    rows, src = evidence.load_checklist()
    assert src and len(rows) >= 10
    reqs = [r["requirement"] for r in rows]
    assert any("Secret hygiene" in r for r in reqs) and all("**" not in r for r in reqs)


def test_verify_file_is_parsed(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_EVIDENCE_DIR", str(tmp_path))
    assert evidence.load_verify().source is None
    (tmp_path / "verify-remote.txt").write_text(VERIFY_OUT)
    v = evidence.load_verify()
    assert v.result == "PASS" and len(v.ports) == 2 and len(v.auth) == 1
    assert ("WARN", v.lines[-1][1]) == v.lines[-1]


def test_page_both_roles_with_proof(make_client, tmp_path, monkeypatch):
    monkeypatch.setenv("PA_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setenv("PA_SPEND_HISTORY", str(tmp_path / "missing.jsonl"))
    (tmp_path / "verify-remote.txt").write_text(VERIFY_OUT)
    for role in ("investigator", "approver"):
        page = make_client(role=role).get("/evidence")
        assert page.status_code == 200
        html = page.text
        assert "Requirement by requirement" in html and "Saved remote verification" in html
        assert "PASS · VM port 22 closed" in html
        assert "ev-status--proven" in html  # the fixture run's sandbox jobs prove the pod-level rows
        assert "Secret hygiene: " in html and "No spend snapshot yet" in html
        assert "not all jobs ran under gVisor runsc" in html  # fixture jobs are runc: process isolation stays partial
        assert "synthetic fixture data" in html


def test_page_without_saved_files_says_so(make_client, tmp_path, monkeypatch):
    monkeypatch.setenv("PA_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setenv("PA_SPEND_HISTORY", str(tmp_path / "missing.jsonl"))
    html = make_client().get("/evidence").text
    assert "No saved output yet" in html and "No saved verify.sh remote output." in html


def test_spend_shows_totals_only(tmp_path, monkeypatch):
    hist = tmp_path / "history.jsonl"
    hist.write_text('{"ts": "t1", "credit_total": 200.0, "credit_used": 0.34, "credit_remaining": 199.66, '
                    '"items": [{"id": "secret-looking-resource"}], "resources": {"x": 1}}\n')
    monkeypatch.setenv("PA_SPEND_HISTORY", str(hist))
    totals = evidence.load_spend()
    assert totals == {"ts": "t1", "credit_total": 200.0, "credit_used": 0.34, "credit_remaining": 199.66}
