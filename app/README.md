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

Visual identity "Comprobante" (`static/tokens.css`, `static/app.css`): every value is a receipt slip with a perforated
bottom edge, mono receipt lines and a stamp whose shape is the status (solid confirmed, dashed sources disagree,
dotted not found); `static/mark.svg` is the mark and favicon. `tests/test_contrast.py` checks the token pairs for AA.

Run it: `uv run pa-app serve --fixtures` (synthetic data), or point `PA_GOLD_DIR` / `lake.yaml` at a real export.

| Screen | Route | Template |
|--------|-------|----------|
| Search-first lookup, dataset tally, browse list | `/` | `index.html` |
| Dossier: every value with its receipt inline, signals, related records, connections | `/entities/<id>` (`/suppliers/<id>` alias) | `dossier.html`, `_evidence.html` |
| Signals: rule, records, how to verify, dispute | `/signals`, `/signals/<id>/<n>` | `signals.html`, `signal.html` |
| Connections (shared address, representative, procedure) | `/relationships` | `relationships.html` |
| Case journal: value → step → TDD → objective → ontology → PRD → brief | `/journal`, `/journal/<value_id>` | `journal_index.html`, `journal.html` |
| My list (kept in the browser) + its downloads | `/watchlist` | `watchlist.html` |
| Source directory: every source behind published values, facts it backs, capture dates, the PRD's authority decision, one receipt each | `/fuentes` (`/sources` alias) | `sources.html`, `sources.py` |
| Open data: CSV, OCDS JSON, RDF | `/data`, `/export/{entities.csv,ocds.json,gold.ttl}` | `data.html`, `export.py` |
| How complete is this data (plain language) | `/completeness`, `/api/completeness` | `completeness.html`, `dod.py` |
| How it works, how to read a profile, disputes | `/about` | `about.html` |

## Screenshot kit (demo and judges)

`uv run pa-app screens --product <url> --console <url> --target case[:run]` captures the key views of this product and
of the Ontofill Console (tour, inbox, operation, definition, discovery, pages, site graph, output, entity graph,
inference, failures, summary, watch, new case) at 1280 and 390 px in light and dark. It writes them to
`docs/evidence/screens/<UTC date>/` with a `manifest.json`. It never signs in and never stores a session: point it at
the services' NetBird mesh addresses, where the console refuses every decision, so the capture is read-only by
construction. Before each capture, e-mail addresses and self-declared names are replaced with placeholders.
Set `PA_CONSOLE_URL` on the product so empty states link judges to the console `/tour`.
