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

## Two ways to publish, and what is not yet verified

1. **`netbird expose` (scripted here).** Per the NetBird docs, `netbird expose <port>` publishes a local service
   through the reverse proxy with `--with-password`, `--with-pin` or `--with-user-groups` (SSO), HTTP only, for as
   long as the command runs (90 s TTL renewed every 30 s), up to 10 sessions per peer. It needs NetBird ≥ v0.66,
   a connected client, and the Peer Expose feature enabled by the account admin.
   Limitation: the credential is passed as a flag and is visible in the VM's process list. Prefer SSO groups for
   the approver.
2. **Cloud dashboard reverse-proxy services (persistent, custom domain; preferred for the demo).** Configured in
   the NetBird Cloud dashboard (`app.netbird.io` → Reverse Proxy) with per-service
   Authentication (SSO with distribution groups, password, PIN, header) and Access Control (CIDR/country).
   The proxy tunnels to the target peer's NetBird address. **Unverified:** whether a dashboard service can reach a
   port bound to the peer's loopback. If it cannot, set `PA_BIND_IP` to the VM's NetBird IP (`100.x.y.z`). That is
   still not a public interface, and `verify.sh local` checks listeners against `PA_BIND_IP`.

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
