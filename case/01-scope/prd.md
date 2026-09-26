---
generated_by:
  backend: vultr
  model: qwen3.8-flash-next
  at: '2026-09-26T23:18:21.522098+00:00'
---
# Global PRD

Brief: `brief.md`

## Personas

- **p1** Public-integrity journalist investigating Mexican government contract awards.
- **p2** Compliance analyst screening suppliers for procurement due diligence.

## Jobs to be done

- **j1** Identify who receives public money via Mexican government contracts.
- **j2** Assess whether a recipient is a legitimate, registered operating company.

## Requirements

- **r1** Ingest public procurement award records (e.g., CompraNet) with contractor name, RFC, amount, and contracting entity.
- **r2** Normalize and deduplicate contractor identities across sources into a single canonical entity record.
- **r3** Attach authority-sourced legitimacy signals: RFC/SAT registration, SAT 69-B EFOS list status, and registry data.
- **r4** Render a transparent legitimacy scorecard per entity with per-signal source citation and retrieval timestamp.

## Definition of done

- entities_with_canonical_record >= 1000
- percent_records_with_authoritative_source >= 95
- unresolved_unknown_source_quarantines <= 0
