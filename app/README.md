# App layer

Investigation, not a dashboard. Reads gold from the lake. Served behind NetBird (one gated URL, zero open ports).

- `dossier/`: one page per company, every field with evidence (screenshot + link) and confidence
- `red-flags/`: each flag with its rule, evidence and plain-language explanation; dispute path
- `relationships/`: suppliers linked by shared address, representative or procedure
- `case-journal/`: replay from brief -> PRD -> ontology -> source -> TDD negotiation -> value
- `watchlist-export/`: follow entities; export gold as OCDS JSON, CSV, RDF
- `completeness/`: per-field completeness bars and taxonomy coverage (demo view)
