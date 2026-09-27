---
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T00:02:13.811703+00:00'
---
# Global PRD

Brief: `brief.md`

## Personas

- **p1** Investigative analyst researching recipients of Mexican public contracts and their legitimacy.
- **p2** Oversight stakeholder verifying supplier integrity against registries and sanctions lists.

## Jobs to be done

- **j1** Identify who receives public money in Mexico through government contracts.
- **j2** Assess whether contract recipients are legitimate companies using public evidence.
- **j3** Cross-check supplier profiles against registries and sanctions lists.

## Requirements

- **r1** Link at least 50 suppliers to real public contracts, each with evidence-backed contract references.
- **r2** Build a core profile per supplier: identity, address, founding date, tax-list status, sanction status.
- **r3** Ensure at least 80% of linked suppliers have a complete core profile.
- **r4** Use US sanctions and registry lists only as secondary cross-checks, never as primary authority.
- **r5** Record zero profile values without evidence; every field must cite a source.
- **r6** Draw evidence from at least 4 distinct source classes (e.g., contracts, registries, sanctions, news).

## Definition of done

- Suppliers linked to real public contracts with evidence-backed contract references >= 50 [basis: human]
- Linked suppliers with complete core profile (identity, address, founding date, tax-list status, sanction status) >= 0.8 [basis: human] (per-entity ratio: 0.8)
- Profile values without evidence <= 0 [basis: human]
- Distinct source classes used for evidence >= 4 [basis: human]

## Authority policy

- Mexican government contracting platforms (e.g., CompraNet) [secondary]: Official Mexican public contract records; authoritative source for contract links.
- Mexican business registries and tax authority (e.g., SAT, REPSE) [secondary]: Official registries authoritative for identity, address, founding date, tax-list status.
- US sanctions and registry lists (e.g., OFAC) [secondary]: Human revision: secondary cross-checks only, never primary authority.
- Reputable news and civil-society oversight outlets [review]: Supplementary context; uncertain authority, requires human review.
- Human-requested cross-check lists [secondary]: Supplementary cross-checks requested by human revision; never auto authority.
- Human-requested cross-check [secondary]: DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.

## Human revisions

- 1. DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.
