---
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T15:45:07.918983+00:00'
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
- ComprasMX / Buen Gobierno federal public-procurement publisher [primary]: Human revision 5 names ComprasMX/Buen Gobierno as the federal procurement publisher for contract awards (supplier, RFC, agency, amount, date), replacing dead compranet.hacienda.gob.mx; historic CompraNet retained.

## Human revisions

- 1. DoD must be the case's: >=50 suppliers linked to real public contracts; >=80% of them with a complete core profile (identity, address, founding date, tax-list status, sanction status); 0 values without evidence; >=4 source classes. Keep US sanctions/registry lists as secondary cross-checks.
- 2. Las fuentes oficiales mexicanas (CompraNet/compras públicas, SAT incl. lista 69-B, registros públicos) son PRIMARIAS y deben listar sus dominios; las listas de sanciones y registros de EE. UU. son SECUNDARIAS (verificación cruzada); quitar la entrada duplicada de verificación cruzada. Mantener las 4 metas del DoD tal como están.
- 3. The >=80% complete-profile target comes from my reason (basis human, quote '>=80% of them with a complete core profile'). Mexican official publishers (CompraNet/compras públicas, SAT incl. 69-B, public registries) are tier PRIMARY with their domains; US sanctions/registry lists are SECONDARY. [Delegated decision by the orchestrator agent under the user's criteria, coord/briefs/approval-delegation.md]
- 4. Keep dod1-dod4, the tiers and the secondary US publishers exactly as they are. One defect: the primary procurement publisher domain comprar.gob.mx does not exist (no DNS record), so no CompraNet/compras publicas source could ever match it. Replace it with the actual, resolvable domain(s) of Mexico's federal public procurement publisher. [Delegated decision by the orchestrator agent under the user's criteria, coord/briefs/approval-delegation.md]
- 5. The federal public-procurement publisher is now ComprasMX / Buen Gobierno: comprasmx.buengobierno.gob.mx (open data at /datos-abiertos) together with the historic CompraNet at historico-compranet.buengobierno.gob.mx; tier PRIMARY for contract awards (supplier name, RFC, contracting agency, amount, date). Replace the dead compranet.hacienda.gob.mx (no DNS). Keep dod1-dod4, the other publishers and tiers as they are. [User decision relayed by the orchestrator, Sun 08:10]

## Open issues for human review

- Material defect in authority_policy.trusted_publishers[0]: the rationale states "comprar.gob.mx hosts CompraNet contract data," but human revision 4 explicitly identified comprar.gob.mx as a dead domain (no DNS record), and human revision 5 replaced it with comprasmx.buengobierno.gob.mx / historico-compranet.buengobierno.gob.mx (already present as trusted_publishers[5]). The listed domain datos.gob.mx is the Mexican open-data portal, not the federal procurement publisher, so the rationale is both factually wrong (references a non-existent domain) and inconsistent with the domain actually listed. This entry is effectively a stale duplicate of the procurement tier already correctly captured by trusted_publishers[5] (ComprasMX/Buen Gobierno, tier primary, per revision 5). Fix: either remove trusted_publishers[0] entirely (it is the duplicate cross-check/procurement entry that revision 2 ordered removed and that revision 5 superseded), or repurpose it solely as the datos.gob.mx open-data channel with a corrected rationale that names datos.gob.mx and does not reference comprar.gob.mx. All DoD criteria (dod1-dod4) are correctly grounded with basis "human" and matching basis_quotes from revisions 1 and 3; feasibility notes appropriately flag the USD 15 budget and unknown elapsed time; per-entity completeness (identity, address, founding date, tax-list status, sanction status) is covered via j2/dod2; US sanctions/registry are correctly tiered secondary; and the prior open_issue on dod2 is resolved in the current artifact.
