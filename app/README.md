# App layer

Investigation, not a dashboard. Reads the gold export (CONTRACT section 4) from the lake over the S3 API, or from
a local directory with the same layout. Served behind NetBird: one gated URL per role, zero open ports.

Run it: `uv run pa-app serve --fixtures` (synthetic data), or point `PA_GOLD_DIR` / `lake.yaml` at a real export.

| Screen | Route | Module / template |
|--------|-------|-------------------|
| Supplier index | `/` | `web.py`, `templates/index.html` |
| Supplier dossier: every field with value, confidence, status and evidence (link + screenshot) | `/suppliers/<id>` | `templates/dossier.html`, `_evidence.html` |
| Red-flag explainer: rule, evidence, plain-language explanation, dispute path | `/signals` | planned (P3) |
| Relationship view: shared address, representative or procedure | `/relationships` | planned (P3) |
| Case journal: value → step → TDD → objective → ontology → PRD → brief | `/journal/<value_id>` | planned (P3) |
| Watchlist + export (OCDS JSON, CSV, RDF) | `/watchlist`, `/export/*` | planned (P3) |
| Per-field completeness + taxonomy coverage | `/completeness` | planned (P2) |

Roles (`PA_ROLE`, one process per role): `investigator` is read-only; `approver` adds phase sign-off
(PRD, factors, ontology) that writes the engine's `APPROVED` file.
