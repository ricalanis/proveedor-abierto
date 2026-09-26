# Proveedor Abierto

Anti-corruption investigation app built on the [Ontofill](../ontofill) engine. It starts from one open question and
no dataset:

> "Who receives public money in Mexico through government contracts, and are they legitimate companies?"

The engine researches the problem, writes a PRD, discovers an ontology and the public sources for it, and uses
sandboxed computer-use agents to fill supplier profiles with evidence. This repo holds the **case package** that run
produces (`case/`) and the **investigation app** that reads the result (`app/`). Collected data lives in an external
lake on Vultr Object Storage, never in git.

| Folder | What goes there |
|--------|-----------------|
| `case/` | The case package: brief (the only human input), PRD, ontology, objectives, technical definition documents, macros. Written by the engine, forkable. |
| `app/` | Investigation app: dossier, signal explainer, relationships, case journal, watchlist and open export, completeness, approvals |
| `lake.example.yaml` | Pointer to the external lake (copy to `lake.yaml`; secrets only in env vars) |
| `docs/` | Definition docs and the demo script |

Code: Apache-2.0 (`LICENSE`). Case package: CC BY 4.0 (`case/LICENSE`). No data in git. Public sources only, no logins.

## The app

Investigation, not a dashboard. Every screen reads the engine's gold export and nothing else.

- **Supplier dossier** (`/suppliers/<id>`): every field with its value, confidence, status (gold, conflict,
  missing) and captures. Click a value's captures to see the source link, the screenshot and the selector the
  agent read.
- **Signal explainer** (`/signals`): each red flag with its rule, the evidence it was computed from, a
  plain-language explanation, steps to verify it, and a dispute path. Signals are prompts to check, not accusations.
- **Relationships** (`/relationships`): suppliers linked by a shared address, a shared legal representative or
  a procedure, each link backed by the value that creates it.
- **Case journal** (`/journal/<value_id>`): a replay from any value back to the brief, through the capture
  step, the technical definition, the objective, the ontology and the PRD.
- **Watchlist and open export** (`/watchlist`, `/export/*`): follow suppliers and see what changed since the
  previous run. Export gold as OCDS 1.1 JSON, CSV or RDF Turtle.
- **Completeness** (`/completeness`): the definition of done recomputed from gold and cross-checked against the
  engine's own `metrics.json`. It shows per-field bars against the 80% line and taxonomy coverage per level, and
  can follow a run live.
- **Approvals** (`/approvals`, approver role only): sign off the PRD, the factors and the ontology. Approving
  writes the `APPROVED` marker the engine waits for.

```bash
uv sync --all-extras
uv run pa-app serve --fixtures              # synthetic data, http://127.0.0.1:8400
uv run pa-app serve                         # real gold, via lake.yaml or PA_GOLD_DIR
uv run pa-app serve --role approver --port 8401
uv run pa-app dod                           # recompute the DoD from gold, cross-check metrics.json
uv run pytest -q                            # unit, HTTP, schema and headless-browser tests
```

Fixtures are synthetic and obviously fake: "Proveedor Ejemplo NN", RFC-shaped IDs starting with `ZZZ`, and
hosts on the reserved `.example` domain. They validate against the engine's contract JSON Schemas.

## Access: two roles, two gated URLs

The app runs as one process per role, and NetBird exposes each role on its own URL with its own access policy.
Neither VM opens an inbound port.

| Role | Process | Can | NetBird access policy |
|------|---------|-----|-----------------------|
| Investigator | `PA_ROLE=investigator` (default) | Read everything and export. Server side is read-only; the watchlist lives in the browser. | investigators group → investigator URL |
| Approver | `PA_ROLE=approver` | Everything above, plus phase sign-off in `/approvals`, which writes `case/<phase>/APPROVED` | approvers group → approver URL |

The role boundary is enforced in the app as well as at the gateway: the investigator process returns 403 for
approval routes, refuses cross-origin approval posts, and never writes files. When the proxy forwards the
signed-in user (`PA_IDENTITY_HEADER`), the approval is recorded under that identity.

### NetBird evidence

*Pending: added once the gateway is live on the Vultr VMs.*

- [ ] Reverse-proxy configuration for the two URLs (screenshot)
- [ ] Access policies: investigators → investigator URL, approvers → approver URL (screenshot)
- [ ] Peer list showing the control-plane and sandbox VMs, connected peer to peer (screenshot)
- [ ] `ss -tlnp` / firewall listing on both VMs showing zero inbound ports

## Built during the event

Built during the Vultr Agent Arena (Sat 11:30 → Sun 12:00 PT). The git history is granular and honest; run
`git log --format='%h %ad %s' --date=iso` to check any claim here.

**Pre-existing** (commit `e008b0d`, the first commit): the definition documents in `docs/planning/` and
`docs/reference/`, and the empty scaffold: folder layout, placeholder READMEs, `case/brief.md` and
`lake.example.yaml`. The full license texts were added in the same commit.

**Built during the event** (every later commit):
- The whole `app/` package: the gold-export reader (S3 API or a local directory), all investigation screens, the
  approver role, the OCDS, CSV and RDF exports, and the DoD evaluator
- The synthetic fixture generator and the test suite, including schema validation against the engine contract
  and headless-browser tests
- Everything the engine writes into `case/` during the live run

## Guardrails

- Profiles are of **legal entities**. Data about people is limited to what public records publish in their role
  (for example a legal representative), and is never enriched from social media.
- Flags are signals needing verification, with a documented way for a company to dispute them.
- Non-goals: accusing anyone, or scoring a "corruption probability".
