# Live demo script (3 minutes)

Judging: Technicality 40, Creativity 25, Live demo 20, Future potential 15. The story is **definition to
execution**: one open question becomes a PRD, an ontology, discovered sources and agent runs, and every value
the audience sees can be clicked back to its capture and to the brief. Show things working live; narrate little.

## Setup (before going on stage)

- Two browser windows, both through NetBird: **investigator URL** (left) and **approver URL** (right).
- A terminal on the control-plane VM, in `proveedor-abierto/`, with the engine CLI ready.
- A paused case run at the PRD checkpoint (`case/01-scope/APPROVAL_PENDING.md` exists, no `APPROVED`).
- Fallback: a cached full run in `bronze.kind: file` layout. If live inference or a source fails, set
  `PA_GOLD_DIR` to the cached run and restart the investigator process (about 5 s). Say so out loud.
- Pre-pick the demo supplier (one with a signal and a conflict) and the value to replay. Write the IDs here
  once the real run exists: supplier `sup:…`, value `val:…`.

## Beats

| Time | Beat | Where | What to do and say |
|------|------|-------|--------------------|
| 0:00–0:20 | **Brief → PRD** | terminal, then approver URL `/approvals` | Show `case/brief.md`: one sentence and no dataset. The engine has written a PRD with personas, jobs and a testable definition of done, and is waiting. Open the PRD link, then click **Approve the PRD**. "Only the approver role can do this. The investigator URL returns 403." |
| 0:20–0:40 | **Ontology** | approver URL `/approvals` | The factors and taxonomies appear as the next checkpoint. Approve them with one click. Mention Simula-style taxonomy expansion and Level Ratio Coverage as the completeness metric. |
| 0:40–1:05 | **Agents find sources, agree a TDD** | investigator `/journal` | The case package table lists the objectives and technical definition documents the agents produced; none were given. Open one TDD: allowed domains, starting mode and refresh rule. "Four or more public source types, all discovered." |
| 1:05–1:50 | **Execution, bars climb** | investigator `/completeness` (Follow the latest run on) | Run `ontofill run case/`. The sandboxes run while the per-field bars climb toward the 80% line. Point at the cross-check line: "the app recomputes the definition of done from gold and it matches the engine's metrics." Point at the modes: deterministic file download for the tax list, an agentic loop for the procurement portal. |
| 1:50–2:20 | **Dossier + signal** | investigator `/suppliers/<id>` | Every field shows value, confidence and status. Click a value's captures to show the source link, the screenshot and the selector. Open the signal: rule, evidence, plain-language explanation, "how to verify", and the dispute path. "A signal, not an accusation." |
| 2:20–2:40 | **Replay to the brief** | click "Trace this value to the brief" | Scroll the journal: value → capture step (mode) → TDD → objective → ontology → PRD → brief. "Any value in the app can do this." |
| 2:40–3:00 | **Blast radius zero** | terminal / engine evidence | A poisoned page is blocked by the sandbox egress policy. Show the NetBird peer list: zero inbound ports, VMs talking peer to peer, two roles on two URLs. Close on the open export (OCDS JSON) and "fork the case package". |

## If something breaks

- **The run stalls:** switch `/completeness` to the cached run (`?run=<cached run id>`) and keep narrating the
  same beats. Every screen works on any run.
- **The approval does not resume:** the `APPROVED` file is in `case/<phase>/`. Show it with `cat`. The engine
  resumes on the next `ontofill run`.
- **A screenshot fails to load:** the evidence panel still shows the source URL and the bronze key. Click the
  raw capture link.

## Numbers to say (fill from the live run, never invent)

- Suppliers at ≥ 80% of core fields: __ / target 50
- Distinct public source types: __ / target 4
- Gold values without evidence: __ (must be 0)
