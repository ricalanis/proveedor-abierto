---
phase: 2
checkpoint: ontology
requested_at: '2026-09-27T07:38:12.586420+00:00'
reason: Human review required for ontology before continuing
artifact_paths:
- 02-ontology/ontology.json
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-27T07:38:11.229722+00:00'
---
# Approval pending: ontology

Review these artifacts:

- `02-ontology/ontology.json`

To approve, create `APPROVED` next to this file with JSON content like `{"approver":"name","date":"YYYY-MM-DD","checkpoint":"ontology"}`. To deny, set `decision` to `deny` and include a non-empty `reason`.

## Human revisions

- 1. Three defects against the approved PRD. (1) The five core profile fields (identity, registered address, founding date, tax-list status, sanction status) sit on a separate core_profile class, but dod2 measures completeness on the primary class supplier, which then has no DoD properties, so dod2 can never be met. Make them properties of supplier (dod: true) and drop core_profile; keep evidence per value. (2) dod1 counts public_contract entities; the PRD says >=50 SUPPLIERS linked to real public contracts, so count suppliers with at least one awarded contract. (3) Rule r_dod4_source_class_diversity's predicate (authority_tier = primary_mexican_source) does not express its label (>=4 distinct source classes); fix or drop it, since dod4 is already measured by its query. Keep everything else. [Delegated decision by the orchestrator agent under the user's criteria, coord/briefs/approval-delegation.md] (group:approvers, 2026-09-27)
