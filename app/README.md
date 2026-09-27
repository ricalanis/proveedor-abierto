# Proveedor Abierto: the consumer app

The B2C product (CONTRACT §14): a reader of ONE case's published gold export, for citizens and journalists.
Spanish first (`?lang=en` switches to English and a cookie keeps it). Every value shows its receipt: the public
page it came from, a screenshot of that page, and when it was captured. Signals are shown as signals to verify,
never as accusations, and each has a dispute path. Operator and approver work lives in the Ontofill Console.

The app is generic over the case's ontology (CONTRACT v0.7 §11): `domain.py` reads `ontology.json` (primary class,
labels, DoD properties, relations, rules, source classes). Any label may carry a per-language twin (`label_es`,
`label_plural_es`, `checks_es`, `verify_es`, and `label_es` / `explanation_es` on flags); the Spanish UI uses it
when present. The app's own copy is in `i18n.py`; `tests/test_product.py` fails when a template string has no
Spanish entry.

Run it: `uv run pa-app serve --fixtures` (synthetic data), or point `PA_GOLD_DIR` / `lake.yaml` at a real export.

| Screen | Route | Template |
|--------|-------|----------|
| Search-first lookup, dataset tally, browse list | `/` | `index.html` |
| Dossier: every value with its receipt inline, signals, related records, connections | `/entities/<id>` (`/suppliers/<id>` alias) | `dossier.html`, `_evidence.html` |
| Signals: rule, records, how to verify, dispute | `/signals`, `/signals/<id>/<n>` | `signals.html`, `signal.html` |
| Connections (shared address, representative, procedure) | `/relationships` | `relationships.html` |
| Case journal: value → step → TDD → objective → ontology → PRD → brief | `/journal`, `/journal/<value_id>` | `journal_index.html`, `journal.html` |
| My list (kept in the browser) + its downloads | `/watchlist` | `watchlist.html` |
| Open data: CSV, OCDS JSON, RDF | `/data`, `/export/{entities.csv,ocds.json,gold.ttl}` | `data.html`, `export.py` |
| How complete is this data (plain language) | `/completeness`, `/api/completeness` | `completeness.html`, `dod.py` |
| How it works, how to read a profile, disputes | `/about` | `about.html` |
