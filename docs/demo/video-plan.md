# 3-minute video plan

Built on what is real on the night of Sat 26 → Sun 27 Sep 2026: the real case ran under the runner many times, and
every decision, failure and fix below is on a real run. Gold has not landed yet; beat 7 has a slot for it and an
honest fallback. Record at 1440×900 on the **judges console** (read-only, safe to film), no music under the voice.
Overlay the run id in a corner so every number is checkable. Cut anything that is not visibly working.

Console base: `https://ontofill-console-judges.eu1.netbird.services` (below, `C` = `/cases/proveedor-abierto`).
Every URL below answered HTTP 200 on the judges console on 2026-09-27 at 12:30 UTC.

| Time | Beat | Screen (URL on the judges console) | Voice-over (≈430 words in total) |
|------|------|------------------------------------|---------------------------------|
| 0:00–0:12 | **The question** | `C` (case hub), then `C/files/brief.md` | "One sentence goes in: who receives public money in Mexico through government contracts, and are they legitimate companies? No dataset, no list of sources. The engine runs itself; people only approve." |
| 0:12–0:35 | **PRD, drafted by the engine, revised by people** | `C/approvals/01-scope` (the PRD and its revisions), then `C/approvals` (the decision log) | "Ontofill researches the problem and drafts a PRD with a testable definition of done. It went through four revisions: each deny carries a reason, and the engine redrafts from it. Every decision is bound to the digest of the exact artifact reviewed, and logged. Tonight they were made by an agent the user delegated to, and each record says so." |
| 0:35–0:55 | **Ontology** | `C/approvals/02-ontology` (classes, relations, rules, the compiled definition of done, set-aside proposals), then `C/definition` | "From the PRD it derives an ontology. Two drafts were denied and fixed. The compiled definition of done shows what each criterion is measured on, so a criterion that can never be met is visible before anyone approves it." |
| 0:55–1:25 | **Discovery funnel and source reviews** | `C/discovery?run=run-7b2949d8bbb0` (leads, objections, stop cause), then three reviews: `C/approvals/03-fanout/sources/source-dd7d33026b8d` (Peru, denied), `…/source-480cb2d2014e` (CNBV, approved), `…/source-link-6bcafaea9baf0b235c28` (a SAT open-data file, approved) | "The engine searches, then argues with itself: 154 objections in one run. An unknown publisher stops for a human. www.sat.gob.pe looked like Mexico's tax authority; it is Lima's, so it was denied. CNBV, the banking regulator, was approved. Each review shows the landing host, the redirect chain and the capture." |
| 1:25–1:55 | **Containment** | `/cases/library-demo/failures?run=containment-demo-202609270251` (quarantine, limit kill), then `C/runs/run-9c120dd56edd` (sandbox jobs with their six proof checkpoints), then `/watch` | "Agents browse in gVisor sandboxes behind an allowlist proxy. Every job proves six checkpoints: the host, the task, where it ran, an isolation probe that must come back BLOCKED, secret hygiene, and teardown. A hostile page is quarantined; a runaway job is killed. When a stale run resumed on its own at 10:25, the operator stopped it with the console's kill switch at 10:29, and the runner was fixed so it cannot happen again." |
| 1:55–2:20 | **Failures with evidence, fixed in code** | `C/failures?run=run-087eb59cbbc8` (SAT PDFs as navigation errors), `C/failures?run=run-49dd07ffa470` ("Domain blocked · www.economia.gob.mx"), `C/failures?run=run-9c120dd56edd` (a download that bypassed the proxy) | "Nothing is patched by hand. Each failure names its cause: PDFs opened as pages, a redirect off the allowlist, a download that tried DNS inside the sandbox. Each became a code fix, and the case was rerun from its approved checkpoints." |
| 2:20–2:40 | **Gold and the dossier** *(slot)* | If gold has landed: `C/output`, then the product's dossier for one supplier (click a capture, open a signal, trace a value to the brief). **If not:** `/watch` (the definition-of-done panel, honestly at 0 of 50), then the product at `https://proveedor.eu1.netbird.services`, captioned "synthetic fixture: how gold will read" | "Every value keeps its capture: the source link, a screenshot, the selector. Red flags explain themselves and are signals to verify, never accusations." (fallback: "Gold has not landed yet; this is how it will read.") |
| 2:40–3:00 | **Zero open ports, and the two repos** | the three NetBird moments from [`netbird-bonus-moments.md`](netbird-bonus-moments.md), compressed, then `github.com/ricalanis/ontofill` and `github.com/ricalanis/proveedor-abierto` | "No port open on either VM, SSH included. Approvers sign in with SSO, judges with a password, and every agent session gets a URL that dies with it. Swap the brief, get a different investigation." |

## Runs to cite

| Run | When (UTC) | What it shows | How it ended |
|-----|------------|---------------|--------------|
| `run-49dd07ffa470` | 07:35–07:46 | the first real crawl after the ontology approval; "Domain blocked · www.economia.gob.mx" | needs you: no authoritative source (phase 3) |
| `run-087eb59cbbc8` | 08:53–09:07 | the first source review (www.gob.mx via economia.gob.mx); SAT PDFs failing as navigation errors | stopped: sources unreachable (recorded as failed, before the runner fix) |
| `run-bcdf9af9e6a6` | 09:52–10:25 | the Peru SAT review (denied); SAT's open-data page quarantined by the injection screen; the first site graph (robots.txt answered 403) | done, no gold |
| `run-7342d49e3706` | resumed 10:25:21, killed 10:29:57 | the stale-resume incident, stopped with the kill switch | killed |
| `run-9c120dd56edd` | 11:06–11:44 | source-link reviews on SAT's open-data files (PorSitRFC21 approved); the download that bypassed the proxy | failed in phase 5, fixed in code |
| `run-7b2949d8bbb0` | 12:00–12:13 | the discovery funnel: 12 iterations, 154 objections | needs you: led to the user's widened source criteria |
| `containment-demo-202609270251` (library-demo) | 02:49–03:10 | quarantine and a limit kill | scratch case, proof only |

Counts from `decisions.jsonl` at 12:30 UTC: PRD 2 denied, 1 approved; ontology 2 denied, 1 approved; factors 2
approved; sources 6 approved, 11 denied; runner 9 starts, 7 pauses, 7 resumes.

## Before recording

- [ ] Re-check the URLs (all 200 on the judges console) and swap in the latest run if a newer one got further.
- [ ] If gold landed: replace beat 7's fallback with `C/output` and a real dossier, and update the README's gold line.
- [ ] Private window, zoom 125%, no bookmarks bar, no account menus on screen.
