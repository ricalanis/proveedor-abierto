# Notes for coding agents

- Read `docs/planning/02-anticorruption-definition.md` first, then `01-engine-definition.md`.
- `case/` is produced by the engine phases. Don't hand-author sources: the engine must discover them
  (no seed dataset, no hard-coded source list). `case/brief.md` is the only human input.
- Never commit data. Captures and refined data live in the external lake; `case/` only links to them.
- Profiles are of legal entities; flags are signals needing verification, not accusations.
- The main feature is investigation, not a dashboard. No Streamlit.

## Commands

```bash
uv sync --all-extras                      # Python 3.13 venv: app + dev deps (+ boto3 for S3)
uv run pytest -q                          # all tests (UI smoke tests need Playwright Chromium: `uv run playwright install chromium`)
uv run pytest -q -m "not ui"              # fast tests only
uv run ruff check app tests               # lint
uv run pa-app serve --fixtures            # app on http://127.0.0.1:8400 over the synthetic fixture export
uv run pa-app serve --role approver       # approver instance (phase sign-off); default role is read-only investigator
uv run pa-app fixtures [OUT]              # write synthetic lake/ + case/ (default .cache/fixtures)
uv run pa-app dod [--gold-dir DIR]        # recompute DoD keys from gold, cross-check the engine's metrics.json
```

Gold source: `PA_GOLD_DIR` (local dir in bucket layout) wins; otherwise `lake.yaml` (`bronze.kind: s3` over the
standard `AWS_*` credentials, or `bronze.kind: local` + `path`). `PA_CASE_ID` if the bucket holds several cases,
`PA_CASE_DIR` (default `case/`), `PA_BRONZE_KEY_TEMPLATE` (default `bronze/sha256/{hex}`).

Code: `app/proveedor_app/` (FastAPI + Jinja, no JS framework; `static/app.js` is progressive enhancement only).
Fixtures are synthetic ("Proveedor Ejemplo NN", RFCs starting `ZZZ`, `.example` hosts) and generated, never committed.
