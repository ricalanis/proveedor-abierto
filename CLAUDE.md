# Notes for coding agents

- Read `docs/planning/02-anticorruption-definition.md` first, then `01-engine-definition.md`.
- `case/` is produced by the engine phases. Don't hand-author sources: the engine must discover them
  (no seed dataset, no hard-coded source list). `case/brief.md` is the only human input.
- Never commit data. Captures and refined data live in the external lake; `case/` only links to them.
- Profiles are of legal entities; flags are signals needing verification, not accusations.
- The main feature is investigation, not a dashboard. No Streamlit.
