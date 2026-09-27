# 3-minute video plan

Built on what is real on Sat 26 → Sun 27 Sep 2026: the real case ran under the runner many times, and every
decision, failure and fix below is on a real run. **Engine gold did not land before the freeze.** Beat 7 says so, then shows the harness-assisted run,
labelled on every frame, and the second case (1-minute cut: [`one-minute-video.md`](one-minute-video.md)). Record at 1440×900 on the **judges console** (read-only, safe to
film; the masthead says "read-only viewer"), no music under the voice. Overlay the run id in a corner so every
number is checkable. Cut anything that is not visibly working.

Console base: `https://ontofill-console-judges.eu1.netbird.services` (below, `C` = `/cases/proveedor-abierto`).
Every URL below answered HTTP 200 on the judges console on 2026-09-27 at 15:40 UTC.

**Capture:** *live* = record the screen in a browser signed in with the judges password; *shot* = a screenshot
already in the repo (`docs/evidence/screens/2026-09-27/`, 00:50 UTC) or in the fresh real-case set
(`docs/evidence/screens/2026-09-27-real/`, 15:45 UTC, judges console). Approval pages are not in the screenshot
kit, so beats 2–4 need live capture for their approval screens.

| Time | Beat | Screen (URL on the judges console) | Capture | Voice-over (≈430 words in total) |
|------|------|------------------------------------|---------|---------------------------------|
| 0:00–0:12 | **The question** | `C` (case hub), then `C/files/brief.md` | shot (hub) + live (brief) | "One sentence goes in: who receives public money in Mexico through government contracts, and are they legitimate companies? No dataset, no list of sources. The engine runs itself; people only approve." |
| 0:12–0:35 | **PRD: drafted by the engine, revised by people** | `C/approvals/01-scope` (the PRD, its revision table with each deny's reason, archived drafts), then `C/approvals` (the decision log: delegated decisions, the 15:16 reopen) | live | "Ontofill researches the problem and drafts a PRD with a testable definition of done. People deny with a reason and the engine redrafts: four archived drafts tonight, plus one reopen after approval to add the federal procurement publisher. Every decision is bound to the digest of the exact artifact reviewed, and labelled as delegated when it was." |
| 0:35–0:55 | **Ontology** | `C/approvals/02-ontology` (classes, relations, rules, the compiled definition of done, set-aside proposals), then `C/definition` | live (approval) + shot (definition) | "From the PRD it derives an ontology. Two drafts were denied and fixed. The compiled definition of done shows what each criterion is measured on, so a criterion that can never be met is visible before approval." |
| 0:55–1:25 | **Discovery, source reviews, a real document fetch** | `C/discovery?run=run-7b2949d8bbb0` (leads, 154 objections, stop cause), then reviews `C/approvals/03-fanout/sources/source-dd7d33026b8d` (Peru, denied) and `…/source-480cb2d2014e` (CNBV, approved), then `C/pages?run=run-40fb8f2e7282` (SAT open-data .xls fetched in the sandbox and parsed: "xls · 204 rows parsed …") | shot (discovery, pages) + live (reviews) | "The engine searches, then argues with itself: 154 objections in one run. An unknown publisher stops for a human: www.sat.gob.pe looked like Mexico's tax authority but is Lima's, so it was denied; CNBV, the banking regulator, was approved. Approved documents are fetched in the sandbox and parsed there." |
| 1:25–1:55 | **Containment, repair, isolation** | `/cases/library-demo/runs/containment-demo-202609270251` (Repairs 1, Limit kills 1, Hostile pages quarantined 1, the Sandbox proof panel), then `C/runs/run-9c120dd56edd` (sandbox jobs with six checkpoints; isolation probes BLOCKED) | shot (both runs) | "Agents browse in gVisor sandboxes behind an allowlist proxy. Every job proves six checkpoints: host, task, where it ran, an isolation probe that must come back BLOCKED, secret hygiene, teardown. A hostile page is quarantined, a runaway job is killed, failing extraction code gets its error back and is patched." |
| 1:55–2:20 | **Failures with evidence, fixed in code** | `C/failures?run=run-087eb59cbbc8` (SAT PDFs as navigation errors), `C/failures?run=run-9c120dd56edd` (a download that bypassed the proxy) | shot | "Nothing is patched by hand. Each failure names its cause: PDFs opened as pages, a redirect off the allowlist, a download that tried DNS inside the sandbox. Each became a code fix, and the case was rerun from its approved checkpoints." |
| 2:20–2:40 | **Gold, honestly: engine gap + a labelled harness run** | `/watch` (the engine's DoD panel, no engine gold yet), then the harness product `https://proveedor-harness.eu1.netbird.services`: home tally, a dossier, **Ver comprobante**, `/relationships`; then `/cases/sf-library-branches/answer` | live (caption the harness shots "harness-assisted (Claude Code), not engine-authored") | "The engine's own gold hasn't landed: the procurement portal's data API was refused by our sandbox allowlist, and we didn't loosen it. To show what done looks like on real data, a Claude Code harness built a dataset from public downloads, keyed to the approved ontology and measured by the same probe: 394 suppliers, 958 contracts, zero values without evidence. It says harness-assisted on every page. And the same engine, with a different brief, is asking about San Francisco's libraries." |
| 2:40–3:00 | **Zero open ports, and the two repos** | the three NetBird moments from [`netbird-bonus-moments.md`](netbird-bonus-moments.md), compressed, then `github.com/ricalanis/ontofill` and `github.com/ricalanis/proveedor-abierto` | live | "No port open on either VM, SSH included. Approvers sign in with SSO, judges with a password, and every agent session gets a URL that dies with it. Swap the brief, get a different investigation." |

## The gold beat, in numbers (bronze audit, Sun 27 Sep 15:00 UTC)

- **642 captures** (1,284 objects: content + metadata): 224 HTML pages (70 of the small ones are access-denied or
  error pages; datos.gob.mx blocks our Vultr IP), 199 screenshots, 154 text, 48 PDFs, 11 JSON, 4 spreadsheets.
- The 4 SAT open-data spreadsheets are **monthly aggregate counts** (no RFCs).
- Company-level rows exist in two PDFs: SAT's **importer registry** (`Pad_Imp.pdf`, RFC + name, ~1,675 companies) and
  Economía's **2004 Fondo PYME beneficiaries** (`PBFPYMEXPROY.pdf`, 543 pages, RFC + name + state + amount).
- Against the definition of done: dod1 (≥ 50 suppliers linked to an awarded contract) **not supported**: no award data
  was captured; dod2 (≥ 80% complete core profile) **not supported**: name and RFC only, no address or founding
  date; dod3 (no value without evidence) **met**; dod4 (≥ 4 source classes) plausible.
- Why: the engine never turned those PDF tables into observations, and it never reached a procurement source
  (the old CompraNet host no longer resolves; comprasmx.buengobierno.gob.mx does).

## Runs to cite

| Run | When (UTC) | What it shows | How it ended |
|-----|------------|---------------|--------------|
| `run-49dd07ffa470` | 07:35–07:46 | the first real crawl after the ontology approval; "Domain blocked · www.economia.gob.mx" | needs you: no authoritative source (phase 3) |
| `run-087eb59cbbc8` | 08:53–09:07 | the first source review; SAT PDFs failing as navigation errors | stopped: sources unreachable |
| `run-bcdf9af9e6a6` | 09:52–10:25 | the Peru SAT review (denied); SAT's open-data page quarantined by the injection screen | done, no gold |
| `run-7342d49e3706` | resumed 10:25:21, killed 10:29:57 | the stale-resume incident, stopped with the kill switch | killed |
| `run-9c120dd56edd` | 11:06–11:44 | source-link reviews on SAT's open-data files; the download that bypassed the proxy | failed in phase 5, fixed in code |
| `run-7b2949d8bbb0` | 12:00–12:13 | the discovery funnel: 12 iterations, 154 objections | needs you: led to the user's widened source criteria |
| `run-40fb8f2e7282` | 12:57–13:15 | SAT open-data .xls fetched in the sandbox and parsed | needs you (phase 3) |
| `run-581ede590e5e` | 15:18– | the PRD reopened after approval to add the procurement publisher; the redraft fails validation | waiting at the PRD |
| `containment-demo-202609270251` (library-demo) | 02:49–03:10 | quarantine, a limit kill, a repair, isolation probes BLOCKED | scratch case, proof only |

## Before recording

- [ ] Sign in to the judges console once in the recording browser; check the masthead reads "read-only viewer".
- [ ] Re-check the URLs; if a newer run got further, swap it in.
- [ ] Private window, zoom 125%, no bookmarks bar, no account menus on screen.
