---
phase: 1
checkpoint: prd
requested_at: '2026-09-27T00:02:22.408154+00:00'
reason: Human review required for prd before continuing
artifact_paths:
- 01-scope/prd.json
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T00:02:13.811703+00:00'
---
# Approval pending: prd

Review these artifacts:

- `01-scope/prd.json`

To approve, create `APPROVED` next to this file with JSON content like `{"approver":"name","date":"YYYY-MM-DD","checkpoint":"prd"}`. To deny, set `decision` to `deny` and include a non-empty `reason`.

## Human revisions

- 1. DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks. (ricalanis (decision relayed by the orchestrator), 2026-09-26)

## Definition of done basis

- Suppliers linked to real public contracts with evidence-backed contract references >= 50: **human**
- Linked suppliers with complete core profile (identity, address, founding date, tax-list status, sanction status) >= 0.8: **human**
- Profile values without evidence <= 0: **human**
- Distinct source classes used for evidence >= 4: **human**

## Authority policy

- Mexican government contracting platforms (e.g., CompraNet) [secondary]: Official Mexican public contract records; authoritative source for contract links.
- Mexican business registries and tax authority (e.g., SAT, REPSE) [secondary]: Official registries authoritative for identity, address, founding date, tax-list status.
- US sanctions and registry lists (e.g., OFAC) [secondary]: Human revision: secondary cross-checks only, never primary authority.
- Reputable news and civil-society oversight outlets [review]: Supplementary context; uncertain authority, requires human review.
- Human-requested cross-check lists [secondary]: Supplementary cross-checks requested by human revision; never auto authority.
- Human-requested cross-check [secondary]: DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.
