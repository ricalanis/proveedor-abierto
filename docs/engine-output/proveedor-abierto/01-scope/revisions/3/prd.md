---
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T00:34:24.584240+00:00'
---
# Global PRD

Brief: `brief.md`

## Personas

- **p1** Investigative analyst mapping Mexican public contract recipients and verifying their legitimacy.
- **p2** Oversight stakeholder needing evidence-backed supplier profiles to assess public spending integrity.

## Jobs to be done

- **j1** Identify suppliers receiving Mexican public contract money and link them to real public contracts.
- **j2** Build complete core profiles (identity, address, founding date, tax-list status, sanction status) for each linked supplier.
- **j3** Cross-check supplier legitimacy against sanctions and registry lists with traceable evidence.

## Requirements

- **r1** Link at least 50 suppliers to real public contracts from official Mexican procurement sources (CompraNet/compras públicas), treated as primary authorities.
- **r2** At least 80% of linked suppliers must have a complete core profile: identity, address, founding date, tax-list status (SAT incl. lista 69-B), and sanction status.
- **r3** Every recorded value must carry source evidence; 0 values without evidence. Use at least 4 distinct source classes.
- **r4** Use US sanctions and registry lists only as secondary cross-checks; Mexican public registries (registros públicos) are primary. Unknown domains go to human review.

## Definition of done

- Suppliers linked to real public contracts from official Mexican procurement sources >= 50 [basis: human]
- Linked suppliers with complete core profile (identity, address, founding date, tax-list status, sanction status) >= 80 [basis: proposed] (per-entity ratio: 0.8) — The stated numeric threshold lacks a matching brief or human quote.; At $2.00, feasibility and elapsed run time need validation after source discovery.
- Recorded values without source evidence <= 0 [basis: human]
- Distinct source classes used >= 4 [basis: human]

## Authority policy

- Mexican federal procurement authority (CompraNet/compras públicas) [primary]: Official Mexican public procurement records; primary source for contract-supplier links per human revision 2. Domains are proposed hypotheses pending human confirmation of exact hostnames.
- Mexican tax authority (SAT, incl. lista 69-B) [primary]: Official tax-list and 69-B status; primary for tax-list status per human revision 2.
- Mexican public registries (registros públicos) [primary]: Official public registries; primary for identity, address, and founding date per human revision 2. Broad domain is a hypothesis for human review.
- US sanctions and registry lists [secondary]: Human revision 1: US sanctions/registry lists are secondary cross-checks only, never auto authority.

## Human revisions

- 1. DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.
- 2. Las fuentes oficiales mexicanas (CompraNet/compras públicas, SAT incl. lista 69-B, registros públicos) son PRIMARIAS y deben listar sus dominios; las listas de sanciones y registros de EE. UU. son SECUNDARIAS (verificación cruzada); quitar la entrada duplicada de verificación cruzada. Mantener las 4 metas del DoD tal como están.

## Open issues for human review

- Material defects found in DoD2: (1) Basis is marked "proposed" with rationale claiming "the stated numeric threshold lacks a matching brief or human quote," but human revision 1 explicitly states ">=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status)." The basis must be "human" with the corresponding basis_quote; the artifact contradicts the trusted human direction. (2) Feasibility for DoD2 is inadequate: it states "feasibility and elapsed run time need validation after source discovery," which does not confirm feasibility against the USD 2.0 budget and unknown elapsed run time as required by the constraints. Additionally, the metric is internally inconsistent — target=80 with min_ratio=0.8 is ambiguous (count vs. percentage) and should be expressed as a single coherent threshold (e.g., ratio >=0.8) to match the human revision's ">=80%". Other criteria pass: DoD1, DoD3, DoD4 correctly cite human revision 1; authority_policy correctly lists domains for Mexican primary sources (CompraNet, SAT, registros públicos) and marks US sanctions/registry lists as secondary tier per human revision 2; no duplicate cross-check entry is present; brief coverage and per-entity core property requirements are addressed. Reject solely on the DoD2 basis/feasibility defects.
- Authority policy needs a primary publisher in the case jurisdiction
- Human secondary cross-check lacks a named publisher/domain: son SECUNDARIAS (verificación cruzada)
