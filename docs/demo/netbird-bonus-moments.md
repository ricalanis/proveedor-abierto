# NetBird bonus: three video moments

Three short takes for the NetBird Zero-Port Access bonus, 10–20 s each. They can go into the 1-minute video
([`video-plan.md`](video-plan.md), last shot) or stand alone as a bonus clip. Record at 1440×900 in a clean
browser profile. Nothing below needs a credential on screen except the public judges password.

**Keep out of frame, every take:** the Vultr account name, email, billing, credit and API keys (the top bar and the
left account menu of the Vultr portal); NetBird account emails, setup keys and any peer whose name is not one of
the two VMs; the approvers' SSO login once it is filled in. Crop in the recording tool, not after upload.

## (a) Zero open ports: the firewall group and an outside scan

What it proves: the VMs accept no inbound connection from the internet, SSH included; administration goes over
NetBird.

1. **Vultr portal → Products → Network → Firewall → group `deny-inbound`.** Show its *Inbound Rules* tab: no rules
   (Vultr firewall groups deny anything not explicitly allowed). Then *Linked Instances*: the control-plane and
   sandbox VMs. Crop to the table only.
2. **Terminal, on a laptop outside the mesh** (NetBird disconnected, or another network):

   ```bash
   deploy/verify.sh remote <vm-public-ip> https://proveedor.eu1.netbird.services \
       https://ontofill-console.eu1.netbird.services https://ontofill-console-judges.eu1.netbird.services
   ```

   Let the `VM port … closed` lines scroll, pause on `VM port 22 closed` and `RESULT: PASS`. (With nmap installed,
   `nmap -Pn -p 1-10000 <vm-public-ip>` gives the same answer in one line: all ports filtered.)
3. **Voice-over:** "No inbound rules, and from outside every port is closed, SSH included. We administer these VMs
   over NetBird only."

Honest caveat for Q&A: the scan is the proof, not the firewall screen. During provisioning an outside probe found
SSH reachable while the group already showed zero inbound rules; the fix was on the host, whose firewall now allows
SSH only on the NetBird interface (`wt0`). So both layers deny, and the scan checks the result. Before filming,
confirm in the portal that both VMs are listed under the group's *Linked Instances*.

## (b) Public URLs and their auth prompts

What it proves: every public URL is gated by NetBird at the edge, with a policy per role.

Open each in a fresh private window, one after another:

| URL | What appears | Say |
|-----|--------------|-----|
| `https://ontofill-console.eu1.netbird.services` | redirect to NetBird SSO (`login.netbird.io`) | "Approvals: SSO, approvers group only." |
| `https://ontofill-console-judges.eu1.netbird.services` | NetBird password page | "Judges: a read-only console." |
| `https://proveedor.eu1.netbird.services` | NetBird password page | "The product: password." |

Optional 5 s tail: sign in to the judges console with the password from the README, open a case's *Approvals*
page, and show "decisions are disabled". Do not type into the SSO page on camera.

## (c) A live-view URL that dies with its session

What it proves: each browser session gets its own public URL (`netbird expose`), and the URL stops existing when the
session closes.

1. On the Mac, with the pinned SSH setup, start a scratch session on the control VM. It is never part of a case run:
   it only reads example.com, calls no model, and closes itself after `--hold` seconds.

   ```bash
   ssh root@<control NetBird IP> /opt/ontofill/engine/services/browser-agent/.venv/bin/python - --hold 60 \
       < docs/demo/liveview_moment.py
   ```

2. Copy the `LIVE VIEW URL:` line into the browser. The stream shows the sandboxed browser moving between
   example.com and iana.org every ~8 s. Film 10 s of it.
3. Wait for `session closed: token_revoked=True cell teardown=destroyed` in the terminal, then **reload the same
   tab**: NetBird answers 404 because the service no longer exists.
4. **Voice-over:** "Every agent session gets its own URL. When the session ends, the sandbox is destroyed and the URL
   is gone."

Rehearsed 2026-09-27 05:11 UTC: the page returned 200 during the session and 404 after close; no expose process was
left on the VM.

## Checklist before recording

- [ ] `verify.sh remote` with all three URLs: `RESULT: PASS`.
- [ ] `deploy/netbird_services.py status`: the three services `enabled=True status=active`.
- [ ] No run is mid-step on the sandbox VM (the scratch session in (c) takes one cell).
- [ ] Private window, zoom 125%, no bookmarks bar, no extensions visible.
