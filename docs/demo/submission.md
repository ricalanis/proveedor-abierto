# Submission text (Vultr Agent Arena · Blast Radius Zero)

Paste-ready copy for the submission form. The numbers match the root README's "Where things stand" section.

**Name:** Ontofill, with Proveedor Abierto as its reference case

**Tagline:** Give it an open question. It returns a dataset where every value has a receipt, and every action ran
behind a wall.

**Repos:** https://github.com/ricalanis/ontofill (engine, Apache-2.0) ·
https://github.com/ricalanis/proveedor-abierto (case package and consumer app)

**Live:** https://ontofill-console-judges.eu1.netbird.services (read-only console) ·
https://proveedor-harness.eu1.netbird.services (product over the harness-assisted dataset). The password is in the
proveedor-abierto README, under "For judges".

## What it does

Ontofill takes a one-sentence brief and runs five phases on its own. It drafts a PRD with a testable definition of
done, derives an ontology, discovers public sources, scopes each one, and sends sandboxed browser and code agents to
fill every field. A person only approves or denies the PRD, the factors, the ontology and unknown sources. Each
decision is bound to the sha256 of the exact file reviewed. Every value keeps its evidence: source URL, capture,
locator and quote. Proveedor Abierto is the hard test case: "Who receives public money in Mexico through government
contracts, and are they legitimate companies?" Its app turns the result into dossiers, explained red flags,
connections and a journal from any value back to the brief.

## How it is built (Blast Radius Zero)

- **Two Vultr VMs, one boundary.** The control VM plans every phase on Vultr Serverless Inference and dispatches
  jobs. The sandbox VM runs each job in a gVisor (`runsc`) cell behind an egress allowlist proxy, with memory, CPU,
  process and time caps, and destroys the cell afterwards.
- **Six proof checks per job:** host check, task result, where it ran, isolation probe (BLOCKED), teardown, and
  secret hygiene (0 keys in the cell; the metadata IP and the mesh are BLOCKED).
- **One key.** Only the inference gateway on the control VM holds the Vultr key. It issues per-session tokens,
  attributes every call to a run and step, and screens captured page text before any model sees it.
- **Containment on a recorded run.** A prompt-injection page is quarantined, and a runaway extractor loop is killed
  by its cell's limits. The host is untouched.
- **Both patterns.**
  - Pattern B: browser actions are checked by a Vultr vision model, and an approve-before-submit gate covers
    anything beyond a read-only GET.
  - Pattern A: the engine writes an extractor, runs it in a networkless cell, feeds the failure back, and patches;
    a passing extractor is promoted to a versioned macro.
- **Zero open ports** on both VMs, SSH included. The URLs go through the NetBird reverse proxy, gated by role:
  viewers get a read-only console that refuses writes with 403, and approvers sign in through SSO. The VMs talk
  peer-to-peer over WireGuard, one way. Each browser session's live-view URL dies with the session.

## Honest status

- **Engine on the real case:** the PRD, factors and ontology are approved, and many real runs are on the console.
  There is **no engine gold yet**. The primary procurement portal's data API was refused by our egress allowlist,
  and the source critic accepted no other candidate. We didn't loosen the critic. The allowlist now admits the
  portal's own API and CDN hosts, and the run resumed on that fix. **The engine run continues after submission;
  its status is live on the judges console.**
- **Harness-assisted run (Claude Code, not engine-authored, labelled on every page):** 394 suppliers and 958
  contracts from public data, keyed to the approved ontology and measured by the same unmodified DoD probe.
  0.924 of suppliers have all six core fields, and 0 of 7,761 values lack evidence.
- **Second brief, same engine:** "Which San Francisco Public Library branches offer free Wi-Fi, and when is each one
  open?" Its PRD and factors are approved, and it is rerunning on today's fixes. This simpler case found four
  engine defects the hard case had hidden: city-level jurisdictions, a missing presence rule in the ontology
  validator, a core field never bound to a property, and a runner that reported a needs-human pause as a crash.
  All four were fixed in code with tests the same day.

## Challenges

Government portals fought back: Akamai blocks on our cloud IP, JavaScript apps with encrypted request headers, a
reCAPTCHA, dead hosts, a lookalike tax-authority domain in another country, and spreadsheets that turned out to be
monthly aggregates. Every failure was filed with evidence, fixed in code with a test, deployed in a window with no
engine running, and rerun. Nothing was patched by hand inside a run.

## What's next

Land engine gold on the real case once the egress fix ships. Add a public company-registry source. Open the case
package so a newsroom can fork a brief and get its own investigation.
