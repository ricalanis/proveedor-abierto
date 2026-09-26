# Live demo script (3 minutes)

Judging: Technicality 40, Creativity 25, Live demo 20, Future potential 15. The story is **definition to
execution**: one open question becomes a PRD, an ontology, discovered sources and agent runs, and every value
the audience sees can be clicked back to its capture and to the brief. Show things working live; narrate little.

## Setup (before going on stage)

- Two browser windows, both through NetBird: **investigator URL** (left) and **approver URL** (right).
- A terminal on the control-plane VM, in `proveedor-abierto/`, with the engine CLI ready.
- A paused case run at the PRD checkpoint (`case/01-scope/APPROVAL_PENDING.md` exists, no `APPROVED`).
- Fallback, cached the night before from the best real run (not a fixture):
  `uv run pa-app snapshot .cache/demo-snapshot --run-id <best run>`. This copies the gold export, the live feed,
  sandbox jobs and every referenced capture into a local folder. Check that it exits 0 (no missing captures).
  If live inference, the network or the engine fails on stage, start
  `uv run pa-app serve --gold-dir .cache/demo-snapshot --replay <best run> --duration 45` and open `/run`. It is
  the same run view, fed by the recording. Say out loud that it is a replay of a recorded run.
- Pre-pick the demo supplier (one with a signal and a conflict) and the value to replay. Write the IDs here
  once the real run exists: supplier `sup:…`, value `val:…`.

## Beats

| Time | Beat | Where | What to do and say |
|------|------|-------|--------------------|
| 0:00–0:20 | **Brief → PRD** | terminal, then approver URL `/approvals` | Show `case/brief.md`: one sentence and no dataset. The engine has written a PRD with personas, jobs and a testable definition of done, and is waiting. Open the PRD link, then click **Approve the PRD**. "Only the approver role can do this. The investigator URL returns 403." |
| 0:20–0:40 | **Ontology** | approver URL `/approvals/02-ontology/factors`, then `/approvals/02-ontology` | Factors show with their evidence. Reject the one without evidence, accept the rest, approve. The taxonomy review shows soundness, coverage and critic labels: "approve numbers, not vibes." Approve. |
| 0:40–1:05 | **Agents find sources, agree a TDD** | investigator `/journal` | The case package table lists the objectives and technical definition documents the agents produced; none were given. Open one TDD: allowed domains, starting mode and refresh rule. "Four or more public source types, all discovered." |
| 1:05–1:50 | **Execution, bars climb** | investigator `/run` | Run `ontofill run case/`. Steps stream in with their mode: one D0 download covers the whole tax list; the procurement portal starts as an agentic loop (S1) and is crystallized into a D1 macro; a registry page that fails its check escalates to S2 vision. The per-field bars climb toward the 80% line. Scroll to **Sandbox proof**: every job ran in a gVisor pod, the isolation probes were BLOCKED, and the pods were torn down. That answers "if I paste `rm -rf /`, what dies?" |
| 1:50–2:20 | **Dossier + signal** | investigator `/suppliers/<id>` | Every field shows value, confidence and status. Click a value's captures to show the source link, the screenshot and the selector. Open the signal: rule, evidence, plain-language explanation, "how to verify", and the dispute path. "A signal, not an accusation." |
| 2:20–2:40 | **Replay to the brief** | click "Trace this value to the brief" | Scroll the journal: value → capture step (mode) → TDD → objective → ontology → PRD → brief. "Any value in the app can do this." |
| 2:40–3:00 | **Blast radius zero** | terminal / engine evidence | A poisoned page is blocked by the sandbox egress policy. Show the NetBird peer list: zero inbound ports, VMs talking peer to peer, two roles on two URLs. Close on the open export (OCDS JSON) and "fork the case package". |

## If something breaks

- **The run stalls:** start the snapshot replay (see Setup) on a spare port and keep narrating the same beats on
  `/run`. When the replay finishes, it publishes its gold, so the dossier and journal beats work on it too.
- **The approval does not resume:** the `APPROVED` file is in `case/<phase>/`. Show it with `cat`. The engine
  resumes on the next `ontofill run`.
- **A screenshot fails to load:** the evidence panel still shows the source URL and the bronze key. Click the
  raw capture link.

## Numbers to say (fill from the live run, never invent)

- Suppliers at ≥ 80% of core fields: __ / target 50
- Distinct public source types: __ / target 4
- Gold values without evidence: __ (must be 0)
