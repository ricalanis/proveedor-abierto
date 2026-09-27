---
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-27T07:39:21.010682+00:00'
---
# Ontology v1

Primary class: `supplier`

Properties: supplier_name, supplier_rfc, registered_address, founding_date, tax_list_status, sanction_status, contract_id, contract_title, contract_rfc, awarding_agency, contract_value, award_date, evidence_id, evidence_label, source_class, authority_tier, source_url, retrieved_at

## Supplier-contract linkage

- CompraNet contract award record (`compranet_contract_award`)
- Awarding agency / dependency (`contract_awarding_agency`)
- Contract value and date (`contract_value_and_date`)
- Supplier RFC identifier on contract (`supplier_rfc_on_contract`)

## Corporate identity legitimacy

- Legal name and registration record (`legal_name_registration`)
- Founding date record (`founding_date_record`)
- Public commercial registry entry (`public_commercial_registry_entry`)
- US registry cross-check (secondary) (`us_registry_cross_check`)

## Tax-list status (SAT lista 69-B)

- SAT lista 69-B listing status (`sat_lista_69b_status`)
- SAT RFC verification (`sat_rfc_verification`)
- Listing date and reason (`sat_listing_date_and_reason`)

## Sanction status

- OFAC SDN list status (secondary) (`ofac_sdn_list_status`)
- Name-matching confidence (`ofac_name_matching`)
- Mexican primary-source confirmation (`mexican_primary_confirmation`)

## Address verification

- Registered address record (`registered_address_record`)
- Address source citation (`address_source_citation`)
- Cross-check against secondary sources (`address_cross_check`)

## Source authority tier

- Primary Mexican official source (`primary_mexican_source`)
- Secondary US cross-check source (`secondary_us_cross_check`)
- Review-tier / unknown source (`review_tier_source`)

## Evidence citation completeness

- Per-value evidence citation (`per_value_evidence_citation`)
- Absence of unsourced values (`unsourced_value_absence`)
- Distinct source classes used (`source_class_diversity`)

## Core profile completeness

- Identity field present (`identity_field_present`)
- Address field present (`address_field_present`)
- Founding date field present (`founding_date_field_present`)
- Tax-list status field present (`tax_list_status_field_present`)
- Sanction status field present (`sanction_status_field_present`)
