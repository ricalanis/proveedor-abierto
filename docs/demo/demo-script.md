# Live demo script (3 minutes)

> **Final running order (Sun 27 Sep, 10:40 PT):** present with the deck in [`presentation/`](presentation/README.md) and
> drive the beats in [`video-plan.md`](video-plan.md), which uses the runs as they stand at the freeze. The 1-minute
> submission cut is [`one-minute-video.md`](one-minute-video.md). Two things changed since this script was written:
> the second brief is now the **engine-authored** case `sf-library-branches` on the console (its answer page replaces
> the scratch library run below), and the gold beat shows the **harness-assisted** product instance
> (`https://proveedor-harness.<domain>`), labelled as not engine-authored. The engine has no gold yet. The rest of
> this file is kept as the setup checklist and fallback notes.

Judging: Technicality 40, Creativity 25, Live demo 20, Future potential 15. **The demo opens on the engine, not the
app** (user decision, brief 08): the audience first meets Ontofill, an engine that turns *any* open question into an
evidence-backed dataset, safely on Vultr, then watches it prove itself on one hard real case, Proveedor Abierto.

**Story in one line:** "Ontofill: give it an open question, it plans on Vultr models, dispatches disposable sandboxes,
and returns a dataset where every value has a receipt. Here it is on Mexican public procurement."

The architecture behind every beat is `docs/planning/03-technical-architecture.md`: a control plane (engine, app,
inference gateway, controller) and a sandbox host of disposable cells with zero secrets. Show things working live;
narrate little; never describe what you cannot show; numbers come from the live run.

**Say it once, early:** "The engine runs itself; people only approve." Every decision inside a run is a Vultr
inference call through the gateway; humans write the brief, approve checkpoints and can pause or stop a run.

## Setup (before going on stage)

- **Architecture frame:** the ASCII diagram from `03-technical-architecture.md` (control plane → gVisor cells →
  Object Storage, NetBird around it) open full screen in a terminal tab or slide.
- **Second brief, run live the night before:** a scratch, non-procurement case (for example the public-libraries
  brief) run on live Vultr inference, in scratch, **never in `case/`**. The command is in the Ontofill README ("Try a
  second brief through the ontology checkpoint"): it copies `tests/genericity/cases/libraries/brief.md` into a scratch
  case and runs `ontofill run <scratch>/case --to-phase 2 --run-id run-library-<ts> --budget-usd 1.00` with a scratch
  `LAKE_ROOT`. It pauses at each checkpoint: **the user** approves the library PRD and factors (never the operator),
  then it stops at the library ontology. Done so far on the control VM: `run-library-1790469369` in
  `/root/demo-library`, paused at its PRD (glm-5.3). Keep two terminal tabs ready: the two `brief.md` files side by
  side, and the two PRDs (or ontologies, once the library one exists) side by side.
- Two browser windows, both through NetBird: the **product** (`https://proveedor.<domain>`, password; left) and the
  **Ontofill Console** (`https://ontofill-console.<domain>`, SSO for the approvers group; right). Approvals, runs,
  the live view and the sandbox proof are the console's; the dossier, signals and journal are the product's.
- A terminal on the control-plane VM, in `proveedor-abierto/`, with the engine CLI ready.
- A paused case run at the PRD checkpoint (`case/01-scope/APPROVAL_PENDING.md` exists, no `APPROVED`).
- Fallback, cached the night before from the best real run (not a fixture): copy that run's lake (gold export, live
  feed, jobs and the referenced captures) to a local folder. If live inference, the network or the engine fails on
  stage, replay it with the console (`ontofill/console`): `ontofill-console serve --replay CASE[:RUN]`, or
  `ontofill-console replay <local lake> --scratch <dir>` (it copies the lake first and never writes the source), and
  open the run view. It is the same run view, fed by the recording. Say out loud that it is a replay of a recorded run.
- Pre-pick the demo supplier (one with a signal and a conflict) and the value to replay. Write the IDs here
  once the real run exists: supplier `sup:…`, value `val:…`.
- Check that the two containment scenarios (hostile page, `rm -rf /` or infinite loop) can be triggered on demand
  from the engine, and rehearse them once. Have one running cell's **live view** link at hand (`session.open` →
  `live_view_url`, published with `netbird expose`).
- Timed rehearsal of the product beats: `uv run python docs/demo/rehearse.py` (the terminal and console beats are
  narration pauses there; rehearse the console beats by hand on the console).

## Beats

| Time | Beat | Where | What to do and say |
|------|------|-------|--------------------|
| 0:00–0:15 | **The engine** | architecture frame | "An agent that only chats is a demo. Ontofill executes: brief → PRD → ontology → sources → sandboxed agents → gold data with evidence." Point at the three homes: control plane (plans on Vultr models; the inference gateway holds the only key), gVisor cells on the sandbox host (zero secrets, destroyed after every session), Object Storage (every raw capture). NetBird around all of it. |
| 0:15–0:35 | **Generic by construction** | terminal: the two `brief.md` files, then the two PRDs (the two ontologies once the library one is approved through) | "Same engine commit, same model, zero code changes. A different question gives a different PRD, ontology and sources. A guard test keeps domain words out of the engine." What is real today, both live on glm-5.3: the library PRD's personas are a resident and a librarian, its DoD is "every free-internet flag and opening-hours value cites a public source, ≥ 90% of libraries have both", and its only trusted publisher is the city government; ours has an analyst and an oversight stakeholder, "≥ 50 suppliers linked to real public contracts, ≥ 80% with a complete core profile", and Mexican federal publishers plus US lists as secondary. |
| 0:35–0:50 | **The test case: Proveedor Abierto** | `case/brief.md`, then the console: `/cases/<id>/approvals` | "Our hard test: who receives public money in Mexico, and are they legitimate companies?" One sentence, no dataset. The engine wrote a PRD with personas, jobs and a testable definition of done, and is waiting. Click **Approve the PRD**. "Only an approver signed in through SSO can; the decision records who, and the exact version of the PRD they saw." |
| 0:50–1:05 | **Ontology + gate** | console `/cases/<id>/approvals/02-ontology/factors`, `/cases/<id>/approvals/02-ontology`, then an action request under `/cases/<id>/approvals` | Reject the factor without evidence, accept the rest, approve: "approve numbers, not vibes." If an action request is waiting (approve-before-submit gate), open it: screenshot, intended action, risk tier; deny it. "Anything final needs a person." |
| 1:05–1:20 | **Discovery** | product `/journal` sources table | "Nobody gave it sources. Each lead was confirmed by a sandbox capture and checked against the approved authority policy." Open one TDD: allowed domains, starting mode, refresh rule. |
| 1:20–1:55 | **Execution: Pattern B + Pattern A** | console run view (`/cases/<id>/runs/<run>`), then the live view (real: a gVisor cell's browser via a per-session `netbird expose` URL that disappears when the session closes) | Steps stream in with their mode (D0 download, D1 script, S1 native agent, S2 Skyvern cell). Point at an S1 browser action and its **verify verdict**: Jev's cheap check first, the Vultr vision model only when Jev is unsure ("decided by code / Jev / Vultr"). Point at a **repair** attempt with its stderr and patch (Pattern A). The per-property bars climb. Open a running cell's **live view** for a few seconds: "that browser is in a gVisor sandbox on the other VM; this is a read-only view that dies with the session." Then "watch the engine argue with itself, then close its own gaps": open the **Phase 1 loop** thread (the critic's objections, the revision that answered them, the approver's reason as a human revision, "stopped: checks passed") and point at the **Reopened phase 3** marker, where the gap loop sent discovery back for a gold gap. |
| 1:55–2:25 | **Containment** | console run view, then **Sandbox proof** | Trigger the hostile page: the inference gateway's Jev + content-safety screen flags the prompt injection and quarantines the page text before the model sees it as instructions, and the page's attempts to reach the metadata IP or another domain come back **BLOCKED** at the cell's egress allowlist (the **quarantined** step in the stream: withheld from planning, kept as evidence; if it has scrolled out of the latest 150 steps, click "Show the whole trail"). Then the extractor that runs `rm -rf /` or loops forever: a **limit kill** badge appears (timeout or memory cap). Scroll to Sandbox proof: "Two instances. One boundary." Isolation probe BLOCKED, secret hygiene (no keys in the cell; the real key lives only in the gateway; metadata IP and mesh BLOCKED), the job's resource limits and the kill, teardown verified. "Only the cell died. The host is untouched." |
| 2:25–2:45 | **The output** | product `/entities/<id>`, a signal, then "Trace this value to the brief" | Every property shows value, confidence and status; click a value's captures (source link, screenshot, selector). Open the signal: rule, evidence, how to verify, dispute path: "a signal, not an accusation." Trace one value: capture step → TDD → objective → ontology → PRD → brief. "Proveedor Abierto is just a viewer on Ontofill's gold export." |
| 2:45–3:00 | **Close** | NetBird evidence (`docs/evidence/netbird-*.png`), then both repo URLs | Talking points from `docs/reference/vultr-netbird-usage.md` ("Vultr: where it runs", "NetBird: the network and the lock"). Zero inbound ports (`verify.sh remote`), two gated URLs (product: password; console: SSO for approvers), VMs peer to peer. Show `github.com/ricalanis/ontofill` first, then `github.com/ricalanis/proveedor-abierto`. "Swap the brief, get a different investigation. Same engine, same boundary." |

If the containment scenarios are not runnable on the day, show the recorded ones through the console's replay and
say that they are recorded. Never describe a containment you cannot show.

## If something breaks

- **The run stalls:** start the console replay (see Setup) and keep narrating the same beats on its run view. The
  product's dossier and journal beats keep working on the gold already published.
- **The approval does not resume:** the approval is recorded (`APPROVED` in `case/<phase>/` and a line in
  `decisions.jsonl`); the runner resumes the run by itself within a poll. Show the console's runner state line.
  Never resume by hand during a run: the engine runs itself; people only approve.
- **A screenshot fails to load:** the evidence panel still shows the source URL and the bronze key. Click the
  raw capture link.

## Numbers to say (fill from the live run, never invent)

Measured so far (2026-09-27, production path on the two VX1s):
- Browser cell on the sandbox VM (gVisor `runsc`, 2 vCPU at the time): create 7.3 s cold, destroy 2.9 s; session open
  through the controller ~8 s.
- The six proof checkpoints on a real cell: host (runsc) ✓, task ✓, where ✓, isolation 3/3 BLOCKED (non-allowlisted
  network, write outside the pod, write outside the writable mount), secrets ✓ (0 keys in env or files, metadata IP
  BLOCKED, mesh BLOCKED), teardown ✓ (destroyed).
- Live view: frames from the cell's real Chromium; a wrong token and a closed session both return 404.
- Phase 1 on live Vultr inference: 2 loop iterations (propose glm-5.3, critique minimax-m3, revise, check) at about
  $0.02–0.035 per attempt; the critic's objections and the failed checks are what stopped a bad draft from passing.

- Second brief: its generated classes __ vs ours __ (same engine commit __)

- Suppliers meeting the definition of done: __ / target 50
- Distinct public source classes: __ / target 4
- Gold values without evidence: __ (must be 0)
