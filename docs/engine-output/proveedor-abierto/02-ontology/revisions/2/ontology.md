---
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-27T07:38:11.229722+00:00'
---
# Ontology v1

Primary class: `supplier`

Properties: rfc, legal_name, registry_status, registered_address, founding_date, tax_list_status, sanction_status, contract_id, contract_title, supplier_rfc, agency_name, award_date, contract_amount, evidence_id, source_name, source_class, source_url, authority_tier, cited_property, cited_value

## Supplier-contract linkage

- Awarded contract record in CompraNet/compras publicas (`contract_award_record`)
- Supplier name/RFC match to contract party (`supplier_name_match`)
- Contract amount and date details (`contract_amount_date`)
- Government agency counterparty (`agency_counterparty`)

## Corporate identity legitimacy

- Legal name and registration in public commercial registry (`legal_name_registration`)
- Founding date on record (`founding_date_record`)
- RFC/tax identifier (`rfc_tax_id`)
- Registry status (active/dissolved) (`registry_status_active`)

## Tax-list status (SAT lista 69-B)

- Presence on SAT lista 69-B (`lista_69b_presence`)
- Presence on other SAT compliance lists (`other_sat_lists`)
- No adverse tax-list findings (`tax_status_clear`)

## Sanction status

- OFAC SDN list check (secondary) (`ofac_sdn_check`)
- Other US sanctions list checks (secondary) (`other_us_sanctions`)
- No sanctions findings recorded (`no_sanctions_found`)

## Address verification

- Registered address present in profile (`registered_address_present`)
- Address matches official source record (`address_source_match`)
- Address field completeness (street, city, state, ZIP) (`address_completeness`)

## Source authority tier

- Primary Mexican official source (`primary_mexican_source`)
- Secondary US cross-check source (`secondary_us_crosscheck`)
- Review-tier/unknown source (`review_tier_source`)

## Evidence citation completeness

- Every recorded value cites evidence (`value_has_citation`)
- Citation resolves to a retrievable source (`citation_resolves_source`)
- Distinct source classes used (>=4) (`source_class_diversity`)

## Core profile completeness

- Identity field complete (`identity_field_complete`)
- Address field complete (`address_field_complete`)
- Founding date complete (`founding_date_complete`)
- Tax-list status complete (`tax_list_field_complete`)
- Sanction status complete (`sanction_field_complete`)
