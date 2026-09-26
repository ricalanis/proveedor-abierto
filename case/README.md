# Case package

Everything the engine decides before and around data. Each phase adds to it.

| Path | Phase | Contents |
|------|-------|----------|
| `brief.md` | input | The open brief (only human input) |
| `01-scope/research-ledger/` | 1 | Sources, claims, evidence behind personas and jobs (links to bronze) |
| `01-scope/prd.md` | 1 | Global PRD: personas, jobs, journeys, requirements, non-goals, constraints, testable definition of done |
| `02-ontology/` | 2 | Factors, taxonomies, schema + SHACL shapes, alignment, DoD queries, recommendations, versions |
| `03-fanout/surface-map/` | 3 | Site graphs mapped onto the ontology, coverage estimates (raw graphs in lake) |
| `03-fanout/objectives.yaml` | 3 | Ranked (source, objective) pairs |
| `04-local/<source>__<objective>/` | 4 | Local PRD, technical definition document, negotiation log |
| `05-macros/<source>/` | 5 | Crystallized RPA macros, versioned with test results and source health |
| `runs/` | 5 | Run log and metric snapshots, case journal index (no data) |
