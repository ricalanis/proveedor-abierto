# Deploying behind NetBird

Two public services run on the control-plane VM, each published through NetBird's reverse proxy with its own
credential. Management is **NetBird Cloud** (`app.netbird.io`): peers enroll there, and the services and their
access policies are configured there (scripted with `netbird_services.py`). The VMs allow **zero public inbound
ports, SSH included**; administration goes over NetBird.

```
 browser ──HTTPS──> NetBird reverse proxy ──WireGuard──> control-plane VM (NetBird IP)
                    (auth per URL)                        :8400  Proveedor Abierto (this app, read-only)
                                                          :8410  Ontofill Console (ontofill/console)
```

| URL | Process | Credential at the proxy | What it does |
|-----|---------|-------------------------|--------------|
| product, `https://proveedor.<domain>` | this repo's app (`compose.yaml`), case and lake mounted **read-only**, read-only root filesystem | shared password or PIN | the consumer product: one case's published gold export (dossiers with receipts, signals, relationships, journal, exports); no approval, run or spend routes (they return 404) |
| console, `https://ontofill-console.<domain>` | the Ontofill Console (`ontofill/console`, its own container and compose file) | SSO restricted to the `approvers` IdP group (or a different PIN) | the engine's operator and approver console: cases, runs and live view, approvals (identity from the SSO header, decisions bound to the artifact digest, append-only `decisions.jsonl`), spend, evidence, replay |

The product's boundary holds at three layers: the proxy credential, the app (it has no write routes), and the
container mounts (it cannot write even if its code were compromised). Approvals are the console's (CONTRACT §14).

**Secrets on the VM:** never put app or NetBird secrets in cloud-init `user_data`; anything there is readable from
inside the VM at `169.254.169.254`. Provision them after boot over NetBird into root-only files (`chmod 600`), as
`systemd/proveedor-expose.service` expects. NetBird Cloud (not self-hosted) also keeps inbound 80/443/UDP 3478 closed.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | App image (Python 3.13, uv, non-root user, healthcheck) |
| `compose.yaml` | The product container; host port bound to `PA_BIND_IP` (default `127.0.0.1`); `cap_drop: ALL`, `no-new-privileges`, read-only root |
| `.env.example` | Local rehearsal defaults (synthetic fixtures). Copy to `.env`; secrets never go in the file |
| `netbird_services.py` | Creates or updates the product and console NetBird Cloud reverse-proxy services via the API (primary); `retire` removes the retired approver and replay services |
| `netbird-expose.sh` | Publishes the product URL with `netbird expose` (fallback) |
| `systemd/proveedor-expose.service` | Keeps that expose session alive on the VM |
| `verify.sh` | Proves the gate: `local` on the VM, `remote` from outside (product and console) |

## Run it

```bash
cd deploy
cp .env.example .env                    # on the VM: point PA_LAKE_DIR / PA_CASE_HOST_DIR at the real lake and case
docker compose up -d --build
./verify.sh local                       # listeners bound to PA_BIND_IP, no approval routes, read-only container

# Publish (NetBird client connected with `netbird up`):
uv run python netbird_services.py plan && uv run python netbird_services.py apply   # product + console
# fallback for the product only: PA_INVESTIGATOR_PASSWORD=... ./netbird-expose.sh
# (or install systemd/proveedor-expose.service with /etc/proveedor-abierto/expose.env, chmod 600)

# From a laptop outside the mesh:
./verify.sh remote <vm-public-ip> https://proveedor.<domain> https://ontofill-console.<domain>
```

The console is deployed from the engine repo (`ontofill/console`: `Dockerfile`, `deploy/compose.yaml`, README),
bound to the same NetBird IP on `8410`.

## How the two URLs are protected (NetBird Cloud reverse proxy, **beta**)

The proxy terminates TLS and enforces auth at the edge, then forwards over WireGuard to this VM; the VM has no
public IP exposure for either service. Protection options offered: SSO/OIDC, password, 6-digit PIN, API-key header,
NetBird-peers-only, IP and country rules, CrowdSec reputation. **Our choice:**

| URL | Protection | Why |
|-----|------------|-----|
| product | password (or 6-digit PIN) + optional country rule | read-only, shareable with the judges on the day |
| console | SSO/OIDC restricted to the `approvers` group | approves and denies checkpoints; each decision is tied to the SSO identity |

1. **Primary: two reverse-proxy services in NetBird Cloud**, scripted against the Services API with
   `deploy/netbird_services.py` (`plan` → `apply`, idempotent; `status` and `delete` touch only these two services;
   `retire` deletes only the retired `<prefix>-approver` and `<prefix>-replay` services if they still exist).
   Each targets the control-plane peer on its port (8400 / 8410) with the protection above, under the account's
   free proxy domain (`proveedor.<domain>`, `ontofill-console.<domain>`). The script refuses a peer that is not a
   Linux host, and never prints the token or credentials (`plan` redacts them).
   **Confirmed** (docs/reference/netbird.md): the proxy reaches the VM's NetBird IP, not 127.0.0.1, and the
   target type for a peer is `peer`. On the VM, bind the containers there: `PA_BIND_IP=$(netbird status --ipv4)` in
   `deploy/.env`. That is not a public interface, and `verify.sh local` checks listeners against `PA_BIND_IP`.
2. **Fallback for the product: `netbird expose`** (`netbird-expose.sh`, `--with-password`/`--with-pin`). URLs live
   only while the command runs ("gone on Ctrl+C"). **Prerequisite:** an account admin enables **Peer Expose** in the
   Cloud account settings. Limitation: the credential is passed as a flag and is visible in the VM's process list.

The proxy stamps `X-NetBird-User` and `X-NetBird-Groups` on forwarded SSO requests and strips client-supplied copies.
The console takes the approver identity from that header only (never a form field) and refuses a decision without
it; its `/whoami` page shows which identity headers arrive (names only, never values).

Sources (NetBird docs, reverse proxy in beta at the time of writing):
[Reverse Proxy](https://docs.netbird.io/manage/reverse-proxy) ·
[Authentication and Access Restrictions](https://docs.netbird.io/manage/reverse-proxy/authentication) ·
[Expose from CLI](https://docs.netbird.io/manage/reverse-proxy/expose-from-cli)

## Evidence to capture for the judges (no credentials on screen)

Before any screenshot goes into the README, check every peer, group and service name visible on screen.
Names must be neutral (for example `pa-control-plane`, `pa-sandbox`). Never capture a peer whose hostname
contains an employer's or client's name; rename the peer in the dashboard first, or leave it out of the capture.
Also keep account emails, setup keys, and the PIN or password fields out of frame.

- [x] `./verify.sh remote <ip> <product-url> <console-url>`: PASS (all checked ports closed, port 22 included; both
      URLs refuse unauthenticated requests)
- [ ] `./verify.sh local` output on the VM (not yet captured for the README)
- [x] NetBird services with their authentication: [`docs/evidence/netbird-services.png`](../docs/evidence/netbird-services.png)
- [x] Groups and access policies (sandbox → control plane: tcp/8700 only, one way):
      [`netbird-peers-groups.png`](../docs/evidence/netbird-peers-groups.png) ·
      [`netbird-policies.png`](../docs/evidence/netbird-policies.png), rendered from the API by `netbird_evidence.py`
      with only the two VM peers named
