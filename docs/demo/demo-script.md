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
- Check that the two containment scenarios (hostile page, `rm -rf /` or infinite loop) can be triggered on demand
  from the engine *(pending engine)*, and rehearse them once.

## Beats

| Time | Beat | Where | What to do and say |
|------|------|-------|--------------------|
| 0:00–0:15 | **Brief → PRD** | terminal, then approver URL `/approvals` | Show `case/brief.md`: one sentence and no dataset. The engine has written a PRD with personas, jobs and a testable definition of done, and is waiting. Open the PRD link, then click **Approve the PRD**. "Only the approver role can do this. The investigator URL returns 403." |
| 0:15–0:35 | **Ontology + action gate** | approver URL `/approvals/02-ontology/factors`, `/approvals/02-ontology`, then an action request under `/approvals` | Reject the factor without evidence, accept the rest, approve. The taxonomy review shows soundness, coverage and critic labels: "approve numbers, not vibes." If an action request is waiting (approve-before-submit gate *(pending engine)*), open it: screenshot, intended action and risk tier; deny it. "Anything final needs a person." |
| 0:35–0:55 | **Agents find sources, agree a TDD** | investigator `/journal` | The sources table lists what the agents found and how each was found; none were given. Open one TDD: allowed domains, starting mode and refresh rule. |
| 0:55–1:35 | **Execution, bars climb** | investigator `/run` | Run `ontofill run case/`. Steps stream in with their mode. Point at a browser action followed by its **verify verdict** from a Vultr vision model (Pattern B), and at a **repair** attempt with its stderr and patch (Pattern A). The per-property bars climb. |
| 1:35–2:05 | **Containment moment** *(scenarios runnable on demand: pending engine)* | investigator `/run`, then **Sandbox proof** | Trigger the hostile page: the verify/guard step flags the prompt injection, and its attempts to reach the metadata IP or another domain come back **BLOCKED** (hard-stop badge in the stream). Then the extractor that runs `rm -rf /` or loops forever: a **limit kill** badge appears (timeout or memory cap). Scroll to Sandbox proof: "Two instances. One boundary." Isolation probe BLOCKED, secret hygiene (no keys in the pod, metadata IP and mesh BLOCKED), the job's resource limits and the kill, teardown verified. "Only the pod died. The host is untouched." |
| 2:05–2:30 | **Dossier + signal** | investigator `/entities/<id>` | Every property shows value, confidence and status. Click a value's captures: source link, screenshot, selector. Open the signal: rule, evidence, plain-language explanation, how to verify, dispute path. "A signal, not an accusation." |
| 2:30–2:45 | **Replay to the brief** | click "Trace this value to the brief" | Scroll the journal: value → capture step (mode) → TDD → objective → ontology → PRD → brief. "Any value in the app can do this." |
| 2:45–3:00 | **Zero-port access + close** | terminal / NetBird console | NetBird's three bonus criteria in one breath: zero inbound ports (`verify.sh remote`), gated access per role (two URLs, two credentials), VMs peer to peer. Close on the open export and "fork the case package". Closing line, from the deck: "Blast radius zero is the reason you can let your agent do anything." |

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

- Suppliers meeting the definition of done: __ / target 50
- Distinct public source classes: __ / target 4
- Gold values without evidence: __ (must be 0)
