---
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-27T18:33:45.732789+00:00'
---
# Ontology v1

Primary class: `library_branch`

Properties: branch_id, branch_name, address, address_evidence_url, weekly_opening_hours, hours_evidence_url, has_free_wifi, wifi_evidence_url, address_id, street_address, publisher, record_evidence_url

## Branch coverage completeness

- All library_branch entities listed (`branch_entity_completeness`)
- All four required properties present per branch (`required_property_completeness`)
- Branches missing from final output (`missing_branch_gap`)

## Per-value evidence citation

- Address value carries cited source (`address_evidence`)
- Weekly opening hours value carries cited source (`hours_evidence`)
- Free Wi-Fi yes/no value carries cited source (`wifi_evidence`)
- Evidence URL attached to each value (`evidence_url_present`)

## Publisher authority tiering

- Values sourced from sfpl.org primary publisher (`primary_publisher_use`)
- Addresses cross-checked against data.sfgov.org (`secondary_crosscheck`)
- Address mismatches flagged for review (`mismatch_flagging`)

## Source legality and jurisdiction

- Sources are public and read-only (`public_readonly_sources`)
- Sources within San Francisco, California, USA jurisdiction (`jurisdiction_scope`)
- Unknown sources routed to review (`unknown_source_review`)

## Nearby open branch with Wi-Fi

- Branch open-now status derivable (`open_now_status`)
- Free Wi-Fi availability derivable (`free_wifi_status`)
- Proximity/near-me relevance supported (`nearby_relevance`)
