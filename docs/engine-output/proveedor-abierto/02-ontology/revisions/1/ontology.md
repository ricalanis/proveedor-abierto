---
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-27T07:36:07.080217+00:00'
---
# Ontology v1

Primary class: `supplier`

Properties: rfc, supplier_name, contract_id, contract_title, award_date, award_amount, contracting_agency, supplier_rfc, profile_id, profile_supplier_rfc, identity_status, registered_address, founding_date, tax_list_status, sanction_status, evidence_id, evidence_profile_id, field_name, source_uri, source_class, authority_tier

## Supplier-contract linkage

- Matched to a CompraNet/compras publicas contract record (`compranet_contract_match`)
- Contract award details present (amount, date, agency) (`contract_award_details`)
- No contract linkage found in official records (`unlinked_supplier`)

## Corporate identity legitimacy

- Verified in Mexican public commercial registry (Registro Publico de Comercio) (`registry_verified`)
- Founding date confirmed from registry (`founding_date_confirmed`)
- Identity not verifiable in public registries (`identity_unverified`)

## Tax-list status (SAT lista 69-B)

- Active taxpayer per SAT (`sat_active`)
- Listed on SAT lista 69-B (non-compliant) (`sat_69b_listed`)
- SAT status not determinable (`sat_status_unknown`)

## Sanction status

- No OFAC match (secondary cross-check) (`ofac_clear`)
- OFAC match found (secondary cross-check) (`ofac_match`)
- Sanction check inconclusive (`sanction_check_unresolved`)

## Address verification

- Registered address complete and verifiable (`address_complete`)
- Address partially recorded or unverifiable (`address_partial`)
- Address missing (`address_missing`)

## Source authority tier

- Primary Mexican official source (CompraNet, SAT, registries) (`primary_mexican_source`)
- Secondary US cross-check source (OFAC, SEC) (`secondary_us_crosscheck`)
- Review-tier / unclassified source (`review_tier_source`)

## Evidence citation completeness

- Value cites evidence (`value_cited`)
- Value lacks evidence citation (`value_uncited`)
- Distinct source classes used (target >=4) (`source_class_diversity`)

## Core profile completeness

- All five core fields present with evidence (`profile_complete`)
- Some core fields missing or uncited (`profile_partial`)
- No core profile fields recorded (`profile_empty`)
