# Live demo script (3 minutes)

Judging: Technicality 40, Creativity 25, Live demo 20, Future potential 15. **The demo opens on the engine, not the
app** (user decision, brief 08): the audience first meets Ontofill, an engine that turns *any* open question into an
evidence-backed dataset, safely on Vultr, then watches it prove itself on one hard real case, Proveedor Abierto.

**Story in one line:** "Ontofill: give it an open question, it plans on Vultr models, dispatches disposable sandboxes,
and returns a dataset where every value has a receipt. Here it is on Mexican public procurement."

The architecture behind every beat is `docs/planning/03-technical-architecture.md`: a control plane (engine, app,
inference gateway, controller) and a sandbox host of disposable cells with zero secrets. Show things working live;
narrate little; never describe what you cannot show; numbers come from the live run.

## Setup (before going on stage)

- **Architecture frame:** the ASCII diagram from `03-technical-architecture.md` (control plane → gVisor cells →
  Object Storage, NetBird around it) open full screen in a terminal tab or slide.
- **Second brief, run live the night before:** a scratch, non-procurement case (for example the public-libraries
  brief) run on live Vultr inference to its ontology checkpoint, in scratch, **never in `case/`**. Use Codex's
  one-command second-brief run (*command pending from Codex; write it here*). Keep two terminal tabs ready: the two
  `brief.md` files side by side, and the two generated ontologies' class lists side by side.
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
- Check that the two containment scenarios (hostile page, `rm -rf /` or infinite loop) can be triggered on demand
  from the engine, and rehearse them once. Have one running cell's **live view** link at hand (`session.open` →
  `live_view_url`, published with `netbird expose`).
- Timed rehearsal of the app beats on the replay: `uv run python docs/demo/rehearse.py` (the terminal beats are
  narration pauses there).

## Beats

| Time | Beat | Where | What to do and say |
|------|------|-------|--------------------|
| 0:00–0:15 | **The engine** | architecture frame | "An agent that only chats is a demo. Ontofill executes: brief → PRD → ontology → sources → sandboxed agents → gold data with evidence." Point at the three homes: control plane (plans on Vultr models; the inference gateway holds the only key), gVisor cells on the sandbox host (zero secrets, destroyed after every session), Object Storage (every raw capture). NetBird around all of it. |
| 0:15–0:35 | **Generic by construction** | terminal: the two `brief.md` files, then the two ontologies | "Same engine, zero code changes. A different question gives a different PRD, ontology and sources. A guard test keeps domain words out of the engine." Show the scratch case's generated classes next to ours for three seconds. Say that the scratch case ran live last night. |
| 0:35–0:50 | **The test case: Proveedor Abierto** | `case/brief.md`, then approver `/approvals` | "Our hard test: who receives public money in Mexico, and are they legitimate companies?" One sentence, no dataset. The engine wrote a PRD with personas, jobs and a testable definition of done, and is waiting. Click **Approve the PRD**. "Only the approver can. The investigator URL returns 403." |
| 0:50–1:05 | **Ontology + gate** | approver `/approvals/02-ontology/factors`, `/approvals/02-ontology`, then an action request under `/approvals` | Reject the factor without evidence, accept the rest, approve: "approve numbers, not vibes." If an action request is waiting (approve-before-submit gate), open it: screenshot, intended action, risk tier; deny it. "Anything final needs a person." |
| 1:05–1:20 | **Discovery** | investigator `/journal` sources table | "Nobody gave it sources. Each lead was confirmed by a sandbox capture and checked against the approved authority policy." Open one TDD: allowed domains, starting mode, refresh rule. |
| 1:20–1:55 | **Execution: Pattern B + Pattern A** | investigator `/run`, then the live view | Steps stream in with their mode (D0 download, D1 script, S1 native agent, S2 Skyvern cell). Point at an S1 browser action and its **verify verdict**: Jev's cheap check first, the Vultr vision model only when Jev is unsure ("decided by code / Jev / Vultr"). Point at a **repair** attempt with its stderr and patch (Pattern A). The per-property bars climb. Open a running cell's **live view** for a few seconds: "that browser is in a gVisor sandbox on the other VM; this is a read-only view that dies with the session." Then "watch the engine argue with itself, then close its own gaps": open the **Phase 1 loop** thread (the critic's objections, the revision that answered them, the approver's reason as a human revision, "stopped: checks passed") and point at the **Reopened phase 3** marker, where the gap loop sent discovery back for a gold gap. |
| 1:55–2:25 | **Containment** | investigator `/run`, then **Sandbox proof** | Trigger the hostile page: the inference gateway's Jev + content-safety screen flags the prompt injection and quarantines the page text before the model sees it as instructions, and the page's attempts to reach the metadata IP or another domain come back **BLOCKED** at the cell's egress allowlist (the **quarantined** step in the stream: withheld from planning, kept as evidence; if it has scrolled out of the latest 150 steps, click "Show the whole trail"). Then the extractor that runs `rm -rf /` or loops forever: a **limit kill** badge appears (timeout or memory cap). Scroll to Sandbox proof: "Two instances. One boundary." Isolation probe BLOCKED, secret hygiene (no keys in the cell; the real key lives only in the gateway; metadata IP and mesh BLOCKED), the job's resource limits and the kill, teardown verified. "Only the cell died. The host is untouched." |
| 2:25–2:45 | **The output** | investigator `/entities/<id>`, a signal, then "Trace this value to the brief" | Every property shows value, confidence and status; click a value's captures (source link, screenshot, selector). Open the signal: rule, evidence, how to verify, dispute path: "a signal, not an accusation." Trace one value: capture step → TDD → objective → ontology → PRD → brief. "Proveedor Abierto is just a viewer on Ontofill's gold export." |
| 2:45–3:00 | **Close** | NetBird console, then both repo URLs | Zero inbound ports (`verify.sh remote`), role-gated URLs (two credentials), VMs peer to peer. Show `github.com/ricalanis/ontofill` first, then `github.com/ricalanis/proveedor-abierto`. "Swap the brief, get a different investigation. Same engine, same boundary." |

If the containment scenarios are not runnable on the day, show the recorded ones through the snapshot replay and
say that they are recorded. Never describe a containment you cannot show.

## If something breaks

- **The run stalls:** start the snapshot replay (see Setup) on a spare port and keep narrating the same beats on
  `/run`. When the replay finishes, it publishes its gold, so the dossier and journal beats work on it too.
- **The approval does not resume:** the `APPROVED` file is in `case/<phase>/`. Show it with `cat`. The engine
  resumes on the next `ontofill run`.
- **A screenshot fails to load:** the evidence panel still shows the source URL and the bronze key. Click the
  raw capture link.

## Numbers to say (fill from the live run, never invent)

- Second brief: its generated classes __ vs ours __ (same engine commit __)

- Suppliers meeting the definition of done: __ / target 50
- Distinct public source classes: __ / target 4
- Gold values without evidence: __ (must be 0)
