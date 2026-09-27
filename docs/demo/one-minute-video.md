# 1-minute submission video

The submission video. The 3-minute live demo is [`video-plan.md`](video-plan.md). Record at 1440×900 on the
**judges console** and the **harness product instance** (both read-only, judges password). Never film the approvers
console. No music under the voice. Put a small caption in a corner on every shot that says what it is, for example
"engine-authored · run-efc9be56964b" or "harness-assisted (Claude Code), not engine-authored".

Console base: `https://ontofill-console-judges.eu1.netbird.services` (`C` = `/cases/proveedor-abierto`).
Harness product: `https://proveedor-harness.eu1.netbird.services` (`H`).

| Time | Shot | Screen | Voice-over (≈150 words) |
|------|------|--------|-------------------------|
| 0:00–0:07 | The question | `C/files/brief.md` | "One sentence goes in: who receives public money in Mexico, and are they legitimate companies? No dataset, no source list." |
| 0:07–0:17 | People only approve | `C/approvals/01-scope`, then `C/approvals` (the decision log) | "Ontofill plans on Vultr models and drafts a PRD, then an ontology. People only approve or deny, and each decision is bound to the exact file they reviewed." |
| 0:17–0:32 | Blast radius zero | `/cases/library-demo/runs/containment-demo-202609270251` (Sandbox proof panel, Limit kills, Hostile pages quarantined), then `C/runs/run-9c120dd56edd` (six checkpoints) | "Every browser and every extractor runs in a gVisor cell on a second VM. It holds no keys, and it can't reach the metadata IP or the mesh. A hostile page gets quarantined, a runaway loop gets killed, and the cell is destroyed after each job." |
| 0:32–0:47 | Receipts | `H` home, a dossier, click **Ver comprobante**, then `H/relationships` | "This is what the definition of done looks like on real data: 394 suppliers, every value with its receipt. This run was harness-assisted, and it says so on every page. The engine's own gold hasn't landed yet, and the console shows exactly why." |
| 0:47–0:54 | Generic | `/cases/sf-library-branches/answer` | "Swap the brief, and the same engine is asking about San Francisco's libraries." |
| 0:54–1:00 | Zero open ports | NetBird services image (`docs/evidence/netbird-services.png`), then both GitHub repos | "Zero open ports, all on Vultr. An agent that executes safely is a product." |

## Rules for the cut

- Keep the harness caption on screen for the whole 0:32–0:47 shot. Never call that dataset engine gold.
- Only film URLs on the NetBird reverse proxy: no mesh addresses, no peer names, no password on screen.
- If a live page is slow, use the matching still from `docs/evidence/screens/` instead. Every number in the voice
  must be visible on screen or in the linked evidence.
