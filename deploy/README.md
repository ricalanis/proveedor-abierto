# Deploying the app behind NetBird

The app runs on the control-plane VM next to the engine as **two processes, one per role**, published through
NetBird's reverse proxy as **two URLs with different credentials**. Management is **NetBird Cloud**
(`app.netbird.io`): peers enroll there, and the two role URLs and their access policies are configured in the
Cloud dashboard. The VMs allow **zero public inbound ports, SSH included**; administration goes over NetBird.

```
 browser ──HTTPS──> NetBird reverse proxy ──WireGuard──> control-plane VM
                    (auth per URL)                        127.0.0.1:8400  investigator  (read-only)
                                                          127.0.0.1:8401  approver      (writes APPROVED)
```

| URL | Process | Credential at the proxy | What the process can do |
|-----|---------|-------------------------|-------------------------|
| investigator | `PA_ROLE=investigator`, case and lake mounted **read-only**, read-only root filesystem | shared password or PIN | read and export; approval routes return 403 |
| approver | `PA_ROLE=approver`, case mounted read-write | SSO restricted to an `approvers` IdP group (or a different PIN) | everything above plus phase sign-off |

The role boundary holds at three layers: the proxy credential, the process role (routes), and the container
mounts (the investigator container cannot write even if its code were compromised).

**Secrets on the VM:** never put app or NetBird secrets in cloud-init `user_data`; anything there is readable from
inside the VM at `169.254.169.254`. Provision them after boot over NetBird into root-only files (`chmod 600`), as
`systemd/proveedor-expose.service` expects. NetBird Cloud (not self-hosted) also keeps inbound 80/443/UDP 3478 closed.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | App image (Python 3.13, uv, non-root user, healthcheck) |
| `compose.yaml` | The two role containers; host ports bound to `PA_BIND_IP` (default `127.0.0.1`); `cap_drop: ALL`, `no-new-privileges`, read-only root |
| `.env.example` | Local rehearsal defaults (synthetic fixtures). Copy to `.env`; secrets never go in the file |
| `netbird-expose.sh` | Publishes both URLs with `netbird expose`, one credential per role |
| `systemd/proveedor-expose.service` | Keeps the two expose sessions alive on the VM |
| `verify.sh` | Proves the gate: `local` on the VM, `remote` from outside |

## Run it

```bash
cd deploy
cp .env.example .env                    # on the VM: point PA_LAKE_DIR / PA_CASE_HOST_DIR at the real lake and case
docker compose up -d --build
./verify.sh local                       # loopback-only listeners, role routes, read-only investigator container

# Publish (NetBird client connected with `netbird up`, Peer Expose enabled for the account):
PA_INVESTIGATOR_PASSWORD=... PA_APPROVER_GROUPS=approvers ./netbird-expose.sh
# or install systemd/proveedor-expose.service with /etc/proveedor-abierto/expose.env (chmod 600)

# From a laptop outside the mesh:
./verify.sh remote <vm-public-ip> https://<investigator-url> https://<approver-url>
```

`verify.sh local` was run on a laptop rehearsal (OrbStack) and passes: both ports bound to 127.0.0.1, 403 on
approval routes from the investigator process, cross-origin approval refused, not reachable on the machine's LAN
IP, and the investigator container cannot write the case or its root filesystem. Binding to `0.0.0.0` makes it fail.
`verify.sh remote` needs the VM and the NetBird URLs, so it has **not been run yet**.

## How the two URLs are protected (NetBird Cloud reverse proxy, **beta**)

The proxy terminates TLS and enforces auth at the edge, then forwards over WireGuard to this VM; the VM has no
public IP exposure for the app. Protection options offered: SSO/OIDC, password, 6-digit PIN, API-key header,
NetBird-peers-only, IP and country rules, CrowdSec reputation. **Our choice:**

| URL | Protection | Why |
|-----|------------|-----|
| investigator | password (or 6-digit PIN) + optional country rule | read-only, shareable with the judges on the day |
| approver | SSO/OIDC restricted to the `approvers` group | signs off phases; tied to a named person in the IdP |

1. **Primary: two reverse-proxy services in the Cloud dashboard** (`app.netbird.io` → Reverse Proxy), each
   targeting the control-plane peer on its port (8400 / 8401), with the protection above. Persistent URLs,
   optional custom domain via CNAME.
   **Unverified:** whether a proxy service can reach a port bound to the peer's loopback. If it cannot, set
   `PA_BIND_IP` to the VM's NetBird IP (`100.x.y.z`), which is still not a public interface; `verify.sh local`
   checks listeners against `PA_BIND_IP`.
2. **Fallback: `netbird expose`** (`netbird-expose.sh`): `--with-password`/`--with-pin` for the investigator,
   `--with-user-groups approvers` for the approver. URLs live only while the command runs ("gone on Ctrl+C"),
   up to 10 sessions per peer. **Prerequisite for both:** an account admin enables **Peer Expose** in the Cloud
   account settings. Limitation: the credential is passed as a flag and is visible in the VM's process list.

The proxy stamps `X-NetBird-User` and `X-NetBird-Groups` on forwarded requests and strips client-supplied copies.
The approver process uses `X-NetBird-User` only to prefill the name field. `APPROVED` stores the typed name
(CONTRACT §2), and no decision depends on the header.

Sources (NetBird docs, reverse proxy in beta at the time of writing):
[Reverse Proxy](https://docs.netbird.io/manage/reverse-proxy) ·
[Authentication and Access Restrictions](https://docs.netbird.io/manage/reverse-proxy/authentication) ·
[Expose from CLI](https://docs.netbird.io/manage/reverse-proxy/expose-from-cli)

## Evidence to capture for the judges (no credentials on screen)

Before any screenshot goes into the README, check every peer, group and service name visible on screen.
Names must be neutral (for example `pa-control-plane`, `pa-sandbox`). Never capture a peer whose hostname
contains an employer's or client's name; rename the peer in the dashboard first, or leave it out of the capture.
Also keep account emails, setup keys, and the PIN or password fields out of frame.

- [ ] `./verify.sh remote ...` output (VM ports closed, unauthenticated URLs refused)
- [ ] `./verify.sh local` output on the VM
- [ ] NetBird dashboard: the two services (or the expose sessions) with their authentication settings
- [ ] Access policy / groups: investigators vs approvers
- [ ] Peers list: control-plane VM and sandbox VM connected peer to peer (Codex's side, approach 3), with names checked
- [ ] `./verify.sh remote` shows port 22 closed as well (admin over NetBird only)
