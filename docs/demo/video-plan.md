# 1-minute video plan

One take per shot, screen capture at 1440×900, no music under narration. Record from the real run; overlay the
run ID in a corner so the numbers are checkable. Cut anything that is not visibly working.

| Time | Shot | Voice-over (about 150 words in total) |
|------|------|------------------------------------|
| 0:00–0:06 | **The engine:** the architecture frame from `03-technical-architecture.md` | "Ontofill turns an open question into a dataset where every value has a receipt. It plans on Vultr models and works in disposable sandboxes." |
| 0:06–0:14 | **Two briefs, two PRDs:** the library brief and ours side by side, then their live PRDs (personas, DoD, publishers); the two ontologies once the user has approved the library case through its checkpoints | "Same engine, zero code changes. A different question gives a different ontology and different sources." |
| 0:14–0:20 | **The test case:** `case/brief.md`, then an approver approves the PRD in the Ontofill Console | "Our hard test: who receives public money in Mexico, and are they legitimate? A person signs off on a URL only approvers can reach." |
| 0:20–0:30 | the console's run view: a browser action, its vision verdict, a repair attempt | "Agents browse in gVisor sandboxes. A Vultr vision model checks each step; failing code gets its error back and retries." |
| 0:30–0:42 | **Containment:** the hostile page quarantined and BLOCKED, a limit kill, then the Sandbox proof | "A hostile page and an `rm -rf /` hit the sandbox. They are quarantined, blocked or killed. Only the cell dies." |
| 0:42–0:54 | Dossier: click a capture, open a signal, trace the value to the brief | "Every value has its capture. Red flags explain themselves, and any value traces back to the brief." |
| 0:54–1:00 | NetBird peer list, then the two repo URLs, engine first | "Zero open ports. Swap the brief, get a different investigation." |

The containment shot depends on the engine's on-demand scenarios *(pending)*. If they are not ready, record them
from the console's replay and caption the shot "recorded run".

Shot list to capture ahead of time (as a fallback if the live capture fails): the architecture frame, the two briefs
and their two ontologies (from the live scratch run), the approvals page before and after approving, `/completeness` at two points in the run, the containment sequence on the console run view and the Sandbox proof, one dossier with a conflict, one signal page, one journal
replay, and the NetBird console (no credentials or credit codes on screen).
