# Evaluation harness

Judges the engine's output against official public classifications and the case hypotheses. **It never feeds the
engine:** nothing here is placed in `case/`, passed to `ontofill run`, or imported by the app. A test
(`tests/test_eval.py`) fails if `app/` or `case/` references it. If the engine could see these references, the
grounded-factor scores would measure copying instead of discovery.

```bash
uv run pa-eval selfcheck                                   # each reference scored against itself: completeness 1.0
uv run pa-eval score --ontology case/02-ontology/ontology.json [--json] [--threshold 0.6]
uv run pa-eval rubric --prd case/01-scope/prd.json [--json]
```

## References (grounded factors)

| File | Classification | Publisher | Source | Terms | Verified |
|------|----------------|-----------|--------|-------|----------|
| `laassp_procedures.yaml` | Procurement procedures, LAASSP art. 35 (7 types) | Cámara de Diputados | [LAASSP.pdf](https://www.diputados.gob.mx/LeyesBiblio/pdf/LAASSP.pdf) (new law, DOF 16-04-2025) | Official law text; public-domain status per LFDA art. 14 fr. VIII is our reading, unverified | yes (PDF read) |
| `scian_2023_sectors.yaml` | SCIAN México 2023, 20 sectors | INEGI | [SCIAN 2023](https://www.inegi.org.mx/scian/), structure from the SCIAN 2023 publication PDF | [INEGI free-use terms](https://www.inegi.org.mx/inegi/terminos.html): reuse and adapt with credit "Fuente: INEGI" | yes (PDF read); English aliases unverified |
| `inegi_federal_entities.yaml` | 32 federal entities with official codes | INEGI | [Catálogo Único, wscatgeo](https://gaia.inegi.org.mx/wscatgeo/mgee/) | INEGI free-use terms | yes (service queried) |
| `cff_69b_list_stages.yaml` | Tax-authority list stages (art. 69-B CFF) | Cámara de Diputados; SAT | [CFF.pdf](https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf) (reform DOF 09-04-2026), [SAT open data](https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html) | Law text as above; SAT terms unverified | presunto / desvirtuado / definitivo: yes (law text); sentencia favorable: search result only |

`mapping.yaml` maps engine factor ids to references. Conceptual factors, and grounded factors without a reference
here (e.g. buying government level), get the critic's soundness only.

**Note on procedure types:** the 2000 LAASSP (art. 26) had three procedures. The law in force since April 2025
(art. 35) has seven. An engine taxonomy with only the classic three scores completeness 3/7 = 0.43. That is a
real finding for a current-law review, not a matcher error.

## Method

The metrics follow Simula (Davidson et al., *Reasoning-Driven Synthetic Data Generation and Evaluation*, TMLR 2026,
arXiv 2603.29791, App. B.1–B.3), as summarised in `docs/planning/01-engine-definition.md` (2c):

- completeness = Good-Overlapping ÷ Total-Good(reference)
- soundness = Total-Good ÷ Total-Nodes(generated)
- novelty = Good-Exclusive ÷ Total-Good(reference)
- coverage = completeness + novelty

"Good" comes from the engine's own critic labels in `ontology.json`. Every reference node counts as good.
"Overlapping" is decided here by a deterministic matcher: normalized exact match on labels, ids and aliases, then
token Jaccard ≥ threshold. Completeness counts distinct reference nodes hit, and is also reported per level (a
Level-Ratio-Coverage-style vector). The report lists:

- gaps: reference nodes nobody matched
- flagged nodes: the critic labelled them Bad or Redundant
- disagreements: the critic's overlap label contradicts the matcher

The rubric checks the engine's PRD (personas, jobs, requirements, DoD) against the hypotheses in
`docs/planning/02-anticorruption-definition.md`, using English and Spanish keywords. Personas that match no
hypothesis are reported as *alternative*, never as failures (02: different personas with good evidence count as
success).

## Limits

- The matcher is a proxy for Simula's LLM critic. It has no embeddings and no translation beyond the listed
  aliases, so a sound engine node worded differently ("Public works" vs "Construcción") can show up as a gap plus
  a novel node. Read the gaps; don't auto-grade on them.
- References are simplified: SCIAN at sector level only, procedure types and 69-B stages as flat lists.
- The rubric only sees the PRD. Whether an alternative persona is well evidenced is in the research ledger, which
  a human checks.
