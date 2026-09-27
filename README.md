# Proveedor Abierto

**The reference case for [Ontofill](https://github.com/ricalanis/ontofill).** Ontofill is the engine: give it an
open question and it plans on Vultr models, dispatches disposable sandboxes, and returns a dataset where every value
has a receipt. It is generic by construction; a different brief gives a different PRD, ontology and sources with
zero code changes. Proveedor Abierto is its hard, real test case, and this repo holds that case package (`case/`)
and the investigation app that reads the engine's gold export.

**The engine runs itself; people only approve.** Once a run starts, every decision in it is a Vultr inference call
made by the engine through its gateway. People act only at the edges: they write the one-sentence brief, approve or
deny each checkpoint in the Ontofill Console, and can start, pause or stop a run. Nobody edits the case, picks
sources or fixes values by hand; a defect is fixed in code and the run is resumed or rerun (CONTRACT §16).

**The question:** *"Who receives public money in Mexico through government contracts, and are they legitimate
companies?"*. There is no dataset and no list of sources. From that sentence, Ontofill researches the problem, writes
a PRD with a testable definition of done, and derives an ontology that a person approves. It then finds the public
sources on its own and sends sandboxed computer-use agents on Vultr to fill every field. Each value keeps its
capture: the source link, a screenshot and the selector. The app turns the result into dossiers, explained red
flags, relationships and a journal that traces any value back to the brief. Flags are signals to verify, never
accusations.

This is the track's own **"Research with Receipts"** example: every claim in the app links to a screenshot of its
source.

## For judges

Three live URLs, one public password. All are read-only for you: nothing you click can change a case or a run.

| URL | What you see |
|-----|--------------|
| **https://ontofill-console-judges.eu1.netbird.services** | The Ontofill Console, read-only: every case, its runs, checkpoints and the decision log, discovery and source reviews, sandbox jobs with their proof checks, failures, gold completeness, spend and every inference call. Approvals, case edits, start/pause and the kill switch are refused (403). |
| **https://proveedor-harness.eu1.netbird.services** | Proveedor Abierto over the **harness-assisted** dataset (394 real suppliers, see below): dossiers with receipts, red flags, connections, the journal. Every page carries the banner "Harness-assisted run (Claude Code), not engine-authored". Spanish first; add `?lang=en` for English. |
| **https://proveedor.eu1.netbird.services** | The same product over the engine's own export. Until the engine lands gold it serves a **synthetic** fixture (obviously fake: "Proveedor Ejemplo NN", RFCs starting with `ZZZ`), so you can see how an engine-authored dossier reads. |

**Password (all three URLs): `pas89-auar7-gju9z-msyn9`**

The password is shared on purpose and will be rotated after the hackathon. It is not used anywhere else. Decisions
happen on a fourth URL, `https://ontofill-console.eu1.netbird.services`, which only members of the approvers group
can open through NetBird SSO. All four are NetBird reverse-proxy services. The VMs behind them have no open inbound
port, SSH included ([`deploy/verify.sh`](deploy/verify.sh) `remote` checks this from outside, along with the refusals
above).

**What you will see** (screenshots over the public URLs, Sun 27 Sep ~17:45 UTC, in [`docs/evidence/screens/2026-09-27-final/`](docs/evidence/screens/2026-09-27-final/)):

| | |
|---|---|
| ![A harness-assisted dossier with its receipt open](docs/evidence/screens/2026-09-27-final/harness-dossier-receipt-1440-dark.png) | ![The containment run in the read-only console](docs/evidence/screens/2026-09-27-final/console-library-demo-containment-1440-dark.png) |
| A dossier on the harness-assisted instance with a value's receipt open: source, capture, locator, confidence | The recorded containment run: hostile page quarantined, code attempt stopped by a limit, isolation and secrets checkpoints blocked |
| ![Connections on the harness-assisted instance](docs/evidence/screens/2026-09-27-final/harness-relationships-1440-dark.png) | ![Inference view of the live run](docs/evidence/screens/2026-09-27-final/console-proveedor-abierto-inference-run-efc9be56964b-1440-dark.png) |
| Supplier connections, marked as outside the approved ontology | The live engine run's inference calls: all reasoning on Vultr, every call attributed |
| ![The completeness page on the harness-assisted instance](docs/evidence/screens/2026-09-27-final/harness-completeness-1440-dark.png) | ![The SF library case's answer page](docs/evidence/screens/2026-09-27-final/console-sf-library-branches-answer-1440-dark.png) |
| The DoD recounted from gold on the harness-assisted instance. "100%" is the approved rule (≥ 80% of core fields); 0.924 of suppliers have all six. Source classes: 3 of 4 approved (no company registry reachable), as its banner says | The second, engine-authored case: its answer page says "no answer yet" until gold lands |

### Where things stand (Sun 27 Sep, 17:55 UTC)

Three tracks, each labelled for what it is.

1. **The engine on the real case (engine-authored).** The PRD, factors and ontology are approved in the console,
   each decision bound to the digest of the exact file reviewed. The engine has run discovery and capture for real
   many times: source reviews, gVisor sandbox jobs with all six proof checks, real document fetches into bronze,
   and every failure fixed in code and rerun. All inference runs on Vultr. It has **no engine gold yet**: the primary
   federal procurement portal (ComprasMX) is a JavaScript app whose data API the sandbox egress allowlist refused,
   and the source critic has accepted none of the remaining candidates. We did not loosen the critic to get a
   number; the allowlist now admits ComprasMX's own API and CDN hosts (engine `378a8c0`, deployed 10:52 PT), and run
   `run-efc9be56964b` resumed on it. **The engine run continues after submission; its status is live on the judges
   console.**
2. **A harness-assisted run (Claude Code, not engine-authored).** To show what the definition of done looks like
   on real data, a Claude Code session built a dataset by hand-written scripts from public downloads, keyed to the
   **approved** ontology and measured by the same unmodified DoD probe. Result: 394 suppliers and 958 contracts;
   dod1 394 ≥ 50; dod2 0.924 with all six core fields; dod3 0 of 7,761 values without evidence; dod4 met by the
   probe, 3 of 4 against the approved source classes (no public company registry was reachable). Contracts are
   INAI's own OCDS publication; ComprasMX refused bulk access (403 and reCAPTCHA) and that block was not bypassed.
   Founding dates are derived from the RFC, and addresses are as declared in contracts. Supplier-to-supplier
   connections (same procedure 372, shared address 7, shared contact person 18) are a **harness extension**, marked
   "not in the approved ontology" on screen. The harness data lives outside both repos, `case/` and the lake; its
   caveats are listed on every page of the harness instance.
3. **A second, unrelated case (engine-authored).** *"Which San Francisco Public Library branches offer free Wi-Fi,
   and when is each one open?"* The same engine, no domain code: the PRD and factors are approved, and a rerun
   (`run-01d4b6d08cfc`) started on `378a8c0`. Its answer page shows the live run and fills with gold cards when
   gold lands:
   https://ontofill-console-judges.eu1.netbird.services/cases/sf-library-branches/answer

   **Building in the open.** The simpler SF case found four engine defects that the harder case had hidden. All four
   were fixed today, each with tests:
   - P1 rejected city-level jurisdictions ("San Francisco, California, USA" against a publisher's "USA").
   - P2 had no presence operator, so invalid rules exhausted the phase. Invalid rules are now set aside as
     recommendations, with deterministic salvage.
   - A core PRD field ("weekly opening hours") was never bound to a DoD property. The missing property is now added
     deterministically, with a repair receipt for human review.
   - The runner reported an exhausted PRD or ontology as a crash. It now pauses as needs-human, with a
     phase-specific ask.

## Use case

**Who uses it.** Investigative journalists, civil-society watchdogs and auditors who need to check a company that
won public contracts, quickly and with evidence they can cite.

**What they do in the app.**
1. Open a **dossier** for a company (`/entities/<id>`). Every property shows its value, confidence and status.
2. Click a value's **capture**: the source link, the screenshot of the page and the selector the agent read.
3. Read a **signal** (red flag): the rule, the evidence, a plain-language explanation, how to verify it, and the
   dispute path for the company.
4. **Trace any value back to the brief** (`/journal/<value_id>`): capture step, technical definition, objective,
   ontology, PRD, brief.

**What the agent does to get there** (five phases, two of them approved by a person):

```mermaid
flowchart LR
  B["brief.md<br/>one question"] --> P1["1 Scope<br/>personas, jobs, PRD + DoD"]
  P1 -->|approver signs off| P2["2 Ontology<br/>factors → taxonomies → schema + SHACL"]
  P2 -->|approver signs off| P3["3 Fan out<br/>discover sources, rank objectives"]
  P3 --> P4["4 Local scoping<br/>technical definition per source"]
  P4 --> P5["5 Execute<br/>D0 → D1 → S1 → S2 in sandbox pods"]
  P5 --> L[("lake<br/>bronze → silver → gold")]
  L --> A["app: dossier · signals · relationships<br/>journal · live run · completeness"]
  A -.->|gold gap reopens fan-out| P3
```

## How it works

From one open question to linked data, stage by stage (question → PRD → ontology → search → spiders → extraction →
gold with receipts), with the evidence for each stage and an honest status of what is live:
[`docs/planning/04-question-to-linked-data.md`](docs/planning/04-question-to-linked-data.md).

## Runs on Vultr + NetBird

What runs where on Vultr (the two VMs, Serverless Inference behind the gateway, Object Storage) and how NetBird is
the network and the lock (zero open ports, gated URLs, one-way policies, per-session live views), without IDs, keys
or device names: [`docs/reference/vultr-netbird-usage.md`](docs/reference/vultr-netbird-usage.md).

## Architecture: "Two instances. One boundary."

A control plane that plans on Vultr models and dispatches disposable sandboxes. The full, canonical description is
[`docs/planning/03-technical-architecture.md`](docs/planning/03-technical-architecture.md).

```
                 Judges / users ──HTTPS──▶ NetBird reverse proxy (PIN: investigator · SSO: approver)
                                                  │ WireGuard (zero open ports)
 ┌──────────── VX1 #1 · CONTROL PLANE ────────────▼─────────────────────────────────┐
 │ Proveedor Abierto app (reads gold export; dossier, run view, journal, approvals) │
 │ Ontofill engine: P1 scope → P2 ontology → P3 fan-out → P4 local scoping → P5 exec│
 │   ├─ decision interface ─▶ Inference gateway ─▶ Vultr Serverless Inference      │
 │   │                          (only real key · per-session tokens · Jev + safety) │
 │   ├─ Controller (MCP): sessions, cell pool, native loop / Skyvern backends       │
 │   ├─ Refiner: silver → SHACL → gold · metrics · DoD                             │
 │   └─ Postgres + Oxigraph (silver/gold graphs)                                    │
 └──────────────────────────┬───────────────────────────────────────────────────────┘
          CDP / cell API (control → sandbox only, NetBird + VPC)
 ┌──────────── VX1 #2 · SANDBOX HOST (zero secrets) ▼───────────────────────────────┐
 │ cell-1 [Skyvern brain? ─CDP─ gVisor Chromium hands ─ egress allowlist proxy]     │
 │ cell-N  … caps: mem/cpu/pids/timeout · destroyed after every session             │
 │ (optional: a throwaway VX1 per high-risk cell)                                   │
 └──────────────────────────┬───────────────────────────────────────────────────────┘
                            ▼
              Vultr Object Storage = bronze (raw captures, content-addressed)
```

- **Control plane (VX1 #1):** the engine plans each phase on Vultr models, this app reads the gold export and the
  live run feed, and the browser layer runs as three parts:
  - **Inference gateway:** an OpenAI-compatible proxy in front of Vultr Serverless Inference. It holds the **only
    real key**, issues a per-session token (time limit, dollar budget, revoked at close), attributes every model call
    to a session and step, and screens page content inside prompts with Jev and the Vultr content-safety model
    before forwarding. A flagged page is quarantined (wrapped as untrusted data), never silently passed on.
  - **Controller** (MCP): `session.open / act / observe / close`, a warm pool of cells, recycled after every session.
    Two backends: the **native** loop (primary, concurrent) and **Skyvern** for hard navigation (one unmodified
    Skyvern per cell, called over its API).
  - Postgres + Oxigraph for silver and gold, on the control VM (loopback only).
- **Sandbox host (VX1 #2), zero secrets:** each **cell** is gVisor Chromium "hands" behind an egress allowlist
  proxy, with memory, CPU, process and time caps, plus an optional Skyvern "brain" that holds only a session token.
  Each cell has its own network; it cannot reach the cloud metadata IP, the mesh or other cells. Live on the sandbox
  VM: a real cell reports runtime `runsc` and passes all six proof checkpoints (a local rehearsal without gVisor runs
  `runc`, and the proof panel says so).
- **Lake:** bronze (raw, content-addressed captures) on Vultr Object Storage; silver (observations with evidence,
  conflicts kept) and gold (reconciled, SHACL-valid values). Git never holds captured data. An ontology or PRD change
  re-refines gold from bronze without browsing again.

**Execution modes per step,** chosen by the technical definition for each source and escalated only when a check fails:

| Mode | What runs |
|---|---|
| D0 | download + parse (CSV, XLSX, PDF, API), no model |
| D1 | a crystallized script; the model only maps, parses or repairs fields |
| S1 | the native agent loop: observe → Jev gate → plan (Vultr tool call) → Jev action guard → act → Jev check → Vultr vision verify |
| S2 | Skyvern in its own cell, through the gateway |

**Two execution patterns, both visible in the Ontofill Console** (the engine's operator console, a separate product
at `https://ontofill-console.<domain>`; this app shows only the published result):

| Pattern | Loop | Where you see it |
|---|---|---|
| B, browser use (primary) | browser action → a Vultr vision model verifies the screenshot against the step goal → retry if not achieved. A person approves anything final through the **approve-before-submit gate**. | console run view: verify verdicts per action; console approvals: action requests with screenshot and risk tier |
| A, code execution | extractor code attempt → run in the sandbox against stored captures → stderr fed back → patch → retry; a passing extractor is promoted to a macro | console run view: repair attempts with result, stderr excerpt and diff |

Every sandbox job reports **six proof checks** on the console's run view → Sandbox proof: host check, task result, where it ran,
isolation probe (BLOCKED), teardown and secret hygiene (no keys in the pod; metadata IP and mesh BLOCKED). The
proof also shows each job's resource limits (memory, CPU, processes, timeout, steps) and any job a limit killed.

## Setup: run it yourself

Four pieces, in two repos. Commands below were checked against the code; env vars are names only (values live in
gitignored `.env` files on the machine that needs them).

**1. The product (this repo), synthetic data, no credentials**

```bash
uv sync --all-extras
uv run pa-app serve --fixtures                         # http://127.0.0.1:8400, synthetic export
uv run pa-app fixtures --domain libraries .cache/libs   # a second, unrelated domain: same screens, no code changes
uv run pa-app dod --gold-dir <export>                   # recompute the DoD from gold, cross-check metrics.json
uv run pytest -q                                       # unit, HTTP, schema and headless-browser tests
```

Against a real engine export: copy `lake.example.yaml` to `lake.yaml` (S3 or `kind: file`), or set `PA_GOLD_DIR`
to a local export; `PA_RUN_ID` (or `serve --run-id`) pins a run; `PA_CASE_DIR` points at the case package. The product
is consumer-only: approvals, the live run view, spend, evidence and replay live in the Ontofill Console.

**2. The engine** ([Ontofill](https://github.com/ricalanis/ontofill))

```bash
cd ../ontofill && uv sync
uv run ontofill run ../proveedor-abierto/case --to-phase 1 --budget-usd 2   # add --run-id run-<id> to name it
```

- Inference: in the deployment the engine calls Vultr **only through the inference gateway**:
  `VULTR_INFERENCE_BASE_URL=http://<control NetBird IP>:8700/v1` and, in `VULTR_INFERENCE_API_KEY`, the engine's
  gateway service token (not a Vultr key; see the browser-agent README, "Service principals"). On a development
  laptop without the gateway you can instead put a direct Vultr key there; then nothing screens the prompts.
- Lake: `lake.yaml` next to the case (`bronze.kind` s3 with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or file).
- Checkpoints: a run stops with **exit code 3** at each human checkpoint (PRD, factors, ontology) and writes
  `APPROVAL_PENDING.md`. A person decides in the Ontofill Console (or, in development only, by writing `APPROVED` by
  hand); the next `ontofill run` resumes or, after a deny with a reason, regenerates the artifact.
- A second, unrelated brief (public libraries) runs in scratch with the same engine: see the Ontofill README,
  "Try a second brief through the ontology checkpoint".

**3. Inference gateway, controller and cells** (`ontofill/services/browser-agent`)

```bash
cd ../ontofill/services/browser-agent && uv sync
uv run ba-gateway                                   # 127.0.0.1:8700; the only process with VULTR_INFERENCE_API_KEY and JEV_API_KEY
uv run ba-controller --transport streamable-http   # MCP: session.open / act / observe / close
```

Gateway: `BA_GATEWAY_ADMIN_TOKEN`, `BA_GATEWAY_LOG`, `BA_GATEWAY_HOST` / `BA_GATEWAY_PORT`,
`BA_GATEWAY_SERVICE_TOKENS` (the engine's principal, by token hash and budget). Cells: `BA_CELL_PROVIDER=ontofill-http`
with `BA_CELLS_URL` / `BA_CELLS_TOKEN` drives the engine's gVisor substrate, served by `ontofill cells serve --port 8766`
(needs `ONTOFILL_CELLS_TOKEN`, and `ONTOFILL_SANDBOX_DOCKER_HOST=ssh://…` for the sandbox VM's Docker with `runsc`).
Live view per session: `BA_LIVEVIEW_EXPOSE=netbird` with `BA_LIVEVIEW_HOST=<control NetBird IP>` and
`BA_LIVEVIEW_PORTS`.

**4. The Ontofill Console** (`ontofill/console`)

```bash
cd ../ontofill/console && uv sync
uv run ontofill-console serve --fixtures .cache/console-fixtures --identity local   # two synthetic cases, dev mode
ONTOFILL_CONSOLE_CASES="main=/path/to/case" uv run ontofill-console serve        # real cases, SSO identity
uv run ontofill-console replay /path/to/local/lake --scratch /tmp/replay           # demo insurance, scratch copy
```

Behind NetBird SSO the approver's identity comes from the header named in `ONTOFILL_CONSOLE_IDENTITY_HEADER`
(default `X-NetBird-User`); `/whoami` shows which headers arrive (names only). Every decision is bound to the
artifact's sha256 and appended to the case's `decisions.jsonl`.

**Deploy** ([`deploy/README.md`](deploy/README.md)): two Vultr VMs joined by NetBird. The control VM runs the product
container (`deploy/compose.yaml`, bound to its NetBird IP), the console (`ontofill/console/deploy/compose.yaml`), the
gateway, controller and cell API; the sandbox VM runs Docker with gVisor `runsc`. `deploy/netbird_services.py
plan|apply|status|retire` manages the public services; `deploy/verify.sh remote <vm-ip> <product-url>
<console-url> [<judges-console-url>]` proves zero open ports, that every URL refuses unauthenticated requests, and that
the judges console refuses every write.

**Public URLs:** listed under [For judges](#for-judges): the read-only console, the product over the harness-assisted
dataset and the product over the engine's export (all behind the judges password), plus the Ontofill Console for
approvers (NetBird SSO, approvers group).

**Generic over the ontology.** The app takes its domain from the case's approved ontology: the primary class,
property labels, definition-of-done properties, relations, rules and source classes
([`app/README.md`](app/README.md)). `pa-app fixtures --domain libraries` builds a public-libraries case that renders
every screen with no code changes.

| Folder | What goes there |
|--------|-----------------|
| `case/` | The case package: brief (the only human input), PRD, ontology, objectives, technical definition documents, macros. Written by the engine, forkable. |
| `app/` | The consumer product: dossiers with receipts, explained signals, relationships, case journal, watchlist, open exports, completeness |
| `deploy/` | Product container, NetBird services, remote verification |
| `lake.example.yaml` | Pointer to the external lake (copy to `lake.yaml`; secrets only in env vars) |
| `docs/` | Definition docs, the demo script and the NetBird evidence images (`docs/evidence/`) |

Code: Apache-2.0 (`LICENSE`). Case package: CC BY 4.0 (`case/LICENSE`). No data in git. Public sources only, no logins.

## The app

Investigation, not a dashboard. Every screen reads the engine's gold export and nothing else, and takes its
vocabulary from the case ontology.

- **Dossier** (`/entities/<id>`): every property with its value, confidence, status (gold, conflict,
  missing) and captures. Click a value's captures to see the source link, the screenshot and the selector the
  agent read.
- **Signal explainer** (`/signals`): each red flag with its rule, the evidence it was computed from, a
  plain-language explanation, steps to verify it, and a dispute path. Signals are prompts to check, not accusations.
- **Relationships** (`/relationships`): entities linked by the relations the ontology defines, each link backed by
  the value that creates it. The approved ontology defines supplier → contract; the supplier-to-supplier types on the
  harness instance (same procedure, shared address, shared contact person) are marked on screen as not in the
  approved ontology.
- **Case journal** (`/journal/<value_id>`): a replay from any value back to the brief, through the capture
  step, the technical definition, the objective, the ontology and the PRD.
- **Watchlist and open export** (`/watchlist`, `/export/*`): follow entities and see what changed since the
  previous run. Export gold as CSV or RDF Turtle, and as OCDS 1.1 JSON when the ontology aligns a class to OCDS.
- **Completeness** (`/completeness`): the definition of done recomputed from gold and cross-checked against the
  engine's own `metrics.json`, including each declarative DoD query. It shows per-property bars and taxonomy
  coverage per level, and can follow a run live.

Approver work and run control are not in this app: the live run view, approvals (PRD, factors, ontology and
approve-before-submit actions), spend, evidence and replay are the **Ontofill Console**'s (`ontofill/console`,
CONTRACT §14), behind its own SSO-gated URL.

`uv run pa-app dod` recomputes the definition of done from gold and cross-checks `metrics.json`.

Fixtures are synthetic and obviously fake: "Proveedor Ejemplo NN", RFC-shaped IDs starting with `ZZZ`, and
hosts on the reserved `.example` domain. They validate against the engine's contract JSON Schemas.

## Access: two products, three gated URLs

Three services are public, each behind NetBird's reverse proxy with its own access policy. Neither VM opens an
inbound port.

| URL | What it is | Can | NetBird access policy |
|-----|------------|-----|-----------------------|
| `https://proveedor.<domain>` | this app, the consumer product | Read one case's published gold export and export it. Server side is read-only; the watchlist lives in the browser. | shared password (the judges password, above) |
| `https://ontofill-console.<domain>` | the Ontofill Console (engine repo) | Cases, runs and live view, approvals, spend, evidence, replay. Each decision takes its approver from the SSO identity header, is bound to the digest of the exact artifact reviewed (409 if it changed), and is appended to `decisions.jsonl`. | SSO restricted to the approvers group |
| `https://ontofill-console-judges.<domain>` | the same console, a separate read-only instance | View everything above. Every non-GET request is refused (403) before any route runs, whatever headers arrive, and its case, registry and runner mounts are read-only. | shared password (the judges password) |

The product has no write routes at all (approval, run and spend routes return 404) and runs in a container with the
case mounted read-only.

### NetBird: the Zero-Port Access bonus

How it is deployed and gated: [`deploy/README.md`](deploy/README.md). Management is NetBird Cloud.

| Bonus criterion (NetBird deck) | Our setup | Evidence |
|---|---|---|
| 1. No open ports | The containers bind to the VM's NetBird IP, not a public interface. The public URLs go through the NetBird reverse proxy. The VMs allow zero public inbound ports, SSH included (admin over NetBird). | `deploy/verify.sh remote` ✓ (all checked ports closed, port 22 included) · `verify.sh local` ✓ |
| 2. Gated access tied to a role | Three URLs, two roles: viewers (the product and the read-only judges console, one shared password) and approvers (the Ontofill Console, SSO restricted to the approvers group; each approval records the verified group). The product has no approval routes at all (404); the judges console refuses every write (403) even with a forged group header. | `verify.sh remote` ✓ (every URL refuses unauthenticated requests; judges writes → 403) · [services and their auth](docs/evidence/netbird-services.png) ✓ |
| 3. Peer-to-peer | The control-plane VM and the sandbox VM talk over WireGuard; the sandbox host sits in its own group, which can reach only the control plane's ports (the deck's "fence in your agents"). | [VM peers and groups](docs/evidence/netbird-peers-groups.png) ✓ · [access policies](docs/evidence/netbird-policies.png) ✓ (sandbox → control plane: tcp/8700 only, one way; the Default all-to-all policy is disabled) |
| 4. Lifecycle-bound URLs (clarification) | Each browser session's live view gets its own `netbird expose` for exactly the session's lifetime: the controller starts it at `session.open` and kills it at `session.close`, so the URL itself stops existing. A per-session view token gates it too. | outside check ✓ (200 with the token, 404 without, 404 from NetBird after close; saved on the console's `/evidence`) |

The evidence images are rendered from the NetBird API by [`deploy/netbird_evidence.py`](deploy/netbird_evidence.py):
only the two VM peers are ever named (other peers appear only as group member counts), no emails, keys or PINs, and
the script refuses to save a page that would contain any other peer's name.

## Built during the event

Built during the Vultr Agent Arena (Sat 11:30 → Sun 12:00 PT). The first commit (`e008b0d`) holds what
pre-existed: the definition documents in `docs/planning/` and `docs/reference/`, and an empty scaffold (folder
layout, placeholder READMEs, `case/brief.md`, `lake.example.yaml`). The full license texts were added in the same
commit. Everything else was built during the event, one granular commit at a time. The table groups
`git log --reverse --date=format:'%a %H:%M'` by work block; the log itself is the source of truth:
[public commit history](https://github.com/ricalanis/proveedor-abierto/commits/main).

| When (PT) | What was built | Commits (first → last) |
|-----------|----------------|------------------------|
| Sat 13:32 | Pre-existing only: definition docs, empty scaffold, `case/brief.md`, licenses | `e008b0d` |
| Sat 13:39–14:31 | App foundation: gold-export reader, synthetic fixtures, DoD evaluator, dossier, signals with dispute path, journal, relationships, exports; evaluation harness (reference taxonomies, Simula scorer, PRD rubric) | `80e6b3d` → `9d83502` |
| Sat 14:18–15:44 | Deploy and NetBird gating (role URLs through the reverse proxy, `verify.sh`), track alignment (Pattern A/B, approve-before-submit gate, six proof checks), generic ontology-driven app with a second-domain proof | `7e3bef0` → `e8df371` |
| Sat 16:22–17:56 | First live PRD draft from the engine on Vultr, checkpoint deny with a reason, loop threads, track-checklist evidence page, per-cell live-view check | `ef5371e` → `ca1c0db` |
| Sat 18:01–18:44 | Split into two products: the Ontofill Console (engine, approvers) and Proveedor Abierto (consumer, Spanish first, receipts on every value); approver and replay URLs retired; NetBird evidence images from the API | `36f4213` → `2a8ff1c` |
| Sat 19:11–22:57 | Receipt identity and source directory, real-data readiness, process docs (question → linked data, Vultr + NetBird usage), screenshot kit that never signs in, public judges password and read-only console | `ba74cd0` → `83c2bc2` |
| Sun 05:36–08:42 | Demo script and video plan on the night's real runs with an honest gold status; real-case console screenshots; `eval/gold_probe.py`, a read-only recount of the DoD from gold | `c5bc840` → `b21a682` |
| Sun 10:18–10:32 | Harness-assisted dataset as a separate, labelled product instance; connection types outside the approved ontology say so | `ac69d66` → `d64e197` |

The engine itself (phases, sandbox cells, gateway, console, runner) was built in the same window in
[Ontofill](https://github.com/ricalanis/ontofill/commits/main); its README has the matching timeline.

Engine output written into `case/` during the live run is committed separately and marked by its
`generated_by` provenance. Mock runs never enter the tracked `case/`.

## Guardrails

- Profiles are of **legal entities**. Data about people is limited to what public records publish in their role
  (for example a legal representative), and is never enriched from social media.
- Flags are signals needing verification, with a documented way for the entity to dispute them.
- Non-goals: accusing anyone, or scoring a "corruption probability".
