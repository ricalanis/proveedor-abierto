---
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T06:55:33.015010+00:00'
---
# Global PRD

Brief: `brief.md`

## Personas

- **p1** Investigative journalist examining who receives public money in Mexico via government contracts and whether they are legitimate companies.
- **p2** Civic transparency researcher auditing supplier legitimacy, tax-list status, and sanction status.

## Jobs to be done

- **j1** Identify suppliers receiving public money through Mexican government contracts and verify each is a legitimate company.
- **j2** Build a complete core profile per supplier (identity, address, founding date, tax-list status, sanction status) with evidence for every value.

## Requirements

- **r1** Link at least 50 suppliers to real public contracts from Mexican official procurement sources (primary).
- **r2** At least 80% of linked suppliers must have a complete core profile covering identity, address, founding date, tax-list status, and sanction status.
- **r3** Every recorded value must cite evidence; no unsourced values. Use at least 4 distinct source classes.
- **r4** Use US sanctions and registry lists only as secondary cross-checks; Mexican official sources are primary authority.

## Definition of done

- Suppliers linked to real public contracts from Mexican official procurement sources >= 50 [basis: human]
- Ratio of linked suppliers with a complete core profile (identity, address, founding date, tax-list status, sanction status) >= 0.8 [basis: human] (per-entity ratio: 0.8)
- Recorded values without evidence <= 0 [basis: human]
- Distinct source classes used >= 4 [basis: human]

## Authority policy

- Mexican public procurement records (CompraNet/compras publicas) [primary]: Human revision 2 designates Mexican procurement records as primary; comprar.gob.mx hosts CompraNet contract data.
- Mexican tax authority incl. lista 69-B (SAT) [primary]: Human revision 2 designates SAT, including 69-B tax-list status, as primary.
- Mexican public commercial registries (registros publicos) [primary]: Human revision 2 designates public registries as primary; Registro Publico de Comercio sits under Secretaria de Economia.
- US sanctions lists (OFAC) cross-check [secondary]: Human revisions 1-3 keep US sanctions lists as secondary cross-checks only.
- US company registry lists cross-check [secondary]: Human revisions keep US registry lists as secondary cross-checks only.

## Human revisions

- 1. DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.
- 2. Las fuentes oficiales mexicanas (CompraNet/compras públicas, SAT incl. lista 69-B, registros públicos) son PRIMARIAS y deben listar sus dominios; las listas de sanciones y registros de EE. UU. son SECUNDARIAS (verificación cruzada); quitar la entrada duplicada de verificación cruzada. Mantener las 4 metas del DoD tal como están.
- 3. The >=80% complete-profile target comes from my reason (basis human, quote '>=80% of them with a complete core profile'). Mexican official publishers (CompraNet/compras públicas, SAT incl. 69-B, public registries) are tier PRIMARY with their domains; US sanctions/registry lists are SECONDARY. [Delegated decision by the orchestrator agent under the user's criteria, coord/briefs/approval-delegation.md]

## Open issues for human review

- Prior objection subject unchanged: Material defect in dod2: Human revision 3 explicitly states "The >=80% complete-profile target comes from my reason (basis human, quote '>=80% of them with a complete core profile')", but the artifact marks dod2 basis as "proposed" with no basis_quote and a rationale that falsely claims "The stated numeric threshold lacks a matching brief or human quote." This directly contradicts the trusted human revision. Additionally, dod2 has an internal inconsistency: target=80 (80 suppliers) vs min_ratio=0.8 (80% of linked suppliers). The human revision says ">=80% of them", which is a ratio, so the target field should express 0.8/80%, not 80 absolute suppliers. All other DoD criteria (dod1, dod3, dod4) correctly carry basis "human" with matching quotes from revision 1, and the trusted_publishers correctly tier Mexican official sources as primary with domains and US sanctions/registry as secondary per revisions 2-3. Per-entity completeness (identity, address, founding date, tax-list status, sanction status) is covered via j2 and dod2's metric. Feasibility notes appropriately flag unknown elapsed time. Fix required: change dod2 basis to "human", add basis_quote ">=80% of them with a complete core profile", correct the rationale, and reconcile target/min_ratio to express the 80% ratio consistently.
