# 1-minute submission video

The video for the submission form. The organizers ask for "a short one minute demo video … highlighting the specific
features, code, and functionality that your team built during the hackathon". The track and the NetBird bonus also
each ask for something to be on screen:

| Required on screen | Shot |
|--------------------|------|
| Only work built during the event, identifiable as such | caption on 0:00 and the closing repo shot (commit history) |
| Real executed results, a multi-step agentic workflow | 0:06–0:18 |
| **One containment moment** (rm -rf, infinite loop or hostile page) | 0:18–0:32 |
| Public demo URL, product-style app | 0:32–0:44 |
| NetBird tier 1: firewall with no inbound application ports, then the public URL loads | 0:44–0:50 |
| NetBird tier 2: the auth prompt | 0:50–0:54 |
| NetBird tier 3: a URL going dead after its task | 0:54–1:00 |

Record at 1440×900. Film only the **judges console** (read-only), the **harness product instance** and the NetBird
moments in [`netbird-bonus-moments.md`](netbird-bonus-moments.md). Never film the approvers console, the Vultr
account menu, emails, keys or mesh addresses (crop in the recorder). There's no music under the voice. Every shot
gets a small corner caption saying what it is, for example "engine-authored · run-efc9be56964b" or
"harness-assisted (Claude Code), not engine-authored".

Console base: `https://ontofill-console-judges.eu1.netbird.services` (`C` = `/cases/proveedor-abierto`).
Harness product: `https://proveedor-harness.eu1.netbird.services` (`H`).

| Time | Shot | Screen | Voice-over (≈150 words) |
|------|------|--------|-------------------------|
| 0:00–0:06 | The question | `C/files/brief.md`, caption "all built Sat 11:30 → Sun 12:00 PT" | "One sentence goes in: who receives public money in Mexico, and are they legitimate companies? Everything you'll see, we built this weekend." |
| 0:06–0:18 | Plans on Vultr, people approve | `C/approvals/01-scope`, then `C/runs/run-efc9be56964b` scrolling steps | "Ontofill plans every step on Vultr Serverless Inference. It drafts a PRD, an ontology, then discovers sources. People only approve, bound to the exact file they reviewed." |
| 0:18–0:32 | **Containment** | `/cases/library-demo/runs/containment-demo-202609270251`: the "Stopped by a resource limit" and "Hostile page quarantined" rows, then the secrets checkpoint | "Every action runs in a gVisor sandbox on a second VM, with no keys inside. This extractor runs rm -rf slash and then loops forever. The limit kills it and the host is untouched. A prompt-injection page gets quarantined." |
| 0:32–0:44 | Receipts | `H`: a dossier, click **Ver comprobante** | "Every value has a receipt. This dataset was harness-assisted, and it says so. The engine's own gold is still running, live on the console." |
| 0:44–0:50 | Zero open ports | Vultr firewall group `deny-inbound` → Inbound Rules: empty; then `verify.sh remote` → `RESULT: PASS` | "No inbound ports on either VM, SSH included." |
| 0:50–0:54 | Gated by role | a private window opening the judges console → NetBird password page | "Judges get a password; approvers get SSO." |
| 0:54–1:00 | A URL that dies | a live-view URL: 200 during its session, 404 after close (moment (c)), then the two GitHub repos | "Each browser session's URL dies with it. An agent that executes safely is a product." |

## Recording the tier 3 shot (a URL that dies)

Start this only when the recorder is ready. It uses a scratch browser session that touches neither case: it
visits example.com and iana.org only, makes no model calls, and costs about $0. From `proveedor-abierto/` on a
machine joined to the NetBird mesh:

```bash
ssh root@<control NetBird IP> /opt/ontofill/engine/services/browser-agent/.venv/bin/python - --hold 60 \
    < docs/demo/liveview_moment.py
```

1. The terminal prints `LIVE VIEW URL: https://….eu1.netbird.services/…`. Open it: a live stream of the sandbox
   browser, switching between the two sites every 8 s.
2. After `--hold` seconds the session closes, and the terminal prints `token_revoked=True` and the cell teardown.
3. The script polls the same URL until it prints `GET live-view URL -> 404`. Reload the tab and film the 404.

Crop the terminal so the SSH target (a mesh address) is out of frame.

## Rules for the cut

- Keep the harness caption on screen for the whole 0:32–0:44 shot. Never call that dataset engine gold.
- Only film URLs on the NetBird reverse proxy: no mesh addresses, no peer names, no password on screen.
- If a live page is slow, use the matching still from `docs/evidence/screens/2026-09-27-final/`. Every number in the
  voice-over must be visible on screen or in the linked evidence.
- The closing quote is the track's own line. Say it as theirs or cut it: "as the track puts it, an agent that
  executes safely is a product."
