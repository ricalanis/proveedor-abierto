"""Create or update the app's two NetBird Cloud reverse-proxy services, idempotently.

    uv run python deploy/netbird_services.py plan     # show what would be sent (secrets redacted); no changes
    uv run python deploy/netbird_services.py apply    # create or update our two services
    uv run python deploy/netbird_services.py status   # our services: domain, enabled, certificate status
    uv run python deploy/netbird_services.py delete   # remove our two services (and nothing else)

Configuration comes from the environment (deploy/.env or the repo's .env, both gitignored):

    NETBIRD_API_TOKEN           personal access token (header `Authorization: Token ...`); never printed
    PA_CONTROL_PLANE_PEER       exact NetBird peer name (or id) of the control-plane VM. Required.
    PA_SERVICE_PREFIX           default "proveedor" -> proveedor.<free domain>, proveedor-approver.<free domain>
    PA_PROXY_DOMAIN             default: the account's free reverse-proxy domain
    PA_TARGET_HOST              default: the peer's NetBird IP (bind the containers there: PA_BIND_IP)
    PA_INVESTIGATOR_PORT/PA_APPROVER_PORT   default 8400 / 8401
    PA_INVESTIGATOR_PASSWORD or PA_INVESTIGATOR_PIN     investigator URL credential
    PA_APPROVER_GROUP           IdP distribution group for SSO on the approver URL (preferred), or PA_APPROVER_PIN
    PA_ALLOWED_COUNTRIES        optional, e.g. "US,MX": country allowlist on both services
    PA_REPLAY_PORT              optional: also a third service <prefix>-replay (the demo-insurance replay role,
                                compose profile `replay`), gated by the investigator credential

API reference: https://docs.netbird.io/api/resources/services (reverse proxy is in beta). Per
docs/reference/netbird.md the peer target type is `peer` and the proxy dials the peer's NetBird IP (not
127.0.0.1), so the default target host is that IP and the containers bind to it (PA_BIND_IP).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("NETBIRD_API_URL", "https://api.netbird.io/api")
SECRET_KEYS = {"password", "pin", "value"}


class ApiError(RuntimeError):
    pass


def load_env() -> None:
    """Read KEY=VALUE lines from deploy/.env and the repo .env without overriding the process environment."""
    for path in (Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(method: str, path: str, body: dict | None = None) -> object:
    token = os.environ.get("NETBIRD_API_TOKEN")
    if not token:
        raise ApiError("NETBIRD_API_TOKEN is not set")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "Authorization": f"Token {token}", "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:  # the error body never contains our token
        detail = exc.read().decode(errors="replace")[:500]
        raise ApiError(f"{method} {path} -> HTTP {exc.code}: {detail}") from None


def redact(obj):
    if isinstance(obj, dict):
        return {k: ("<redacted>" if k in SECRET_KEYS and v else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


def find_peer(api, name_or_id: str) -> dict:
    peers = api("GET", "/peers") or []
    match = [p for p in peers if name_or_id in (p.get("id"), p.get("name"), p.get("hostname"))]
    if len(match) != 1:
        raise ApiError(f"PA_CONTROL_PLANE_PEER must match exactly one peer (matched {len(match)})")
    peer = match[0]
    os_name = str(peer.get("os") or "").lower()
    if not any(k in os_name for k in ("linux", "ubuntu", "debian")):
        # guard: the app runs on the Linux control-plane VM; never point the services at a laptop peer
        raise ApiError("the selected peer is not a Linux host; refusing to target it")
    return peer


def group_id(api, name: str) -> str:
    groups = api("GET", "/groups") or []
    match = [g["id"] for g in groups if name in (g.get("name"), g.get("id"))]
    if len(match) != 1:
        raise ApiError(f"PA_APPROVER_GROUP must match exactly one group (matched {len(match)})")
    return match[0]


def free_domain(api) -> str:
    domains = api("GET", "/reverse-proxies/domains") or []
    free = [d["domain"] for d in domains if d.get("type") == "free" and d.get("validated", True)]
    if not free:
        raise ApiError("no free reverse-proxy domain on this account; set PA_PROXY_DOMAIN")
    return free[0]


def desired(api, env: dict[str, str]) -> list[dict]:
    """The service bodies we want to exist: investigator + approver, and replay when PA_REPLAY_PORT is set."""
    peer = find_peer(api, env["PA_CONTROL_PLANE_PEER"])
    host = env.get("PA_TARGET_HOST") or peer.get("ip")
    domain = env.get("PA_PROXY_DOMAIN") or free_domain(api)
    prefix = env.get("PA_SERVICE_PREFIX", "proveedor")

    if env.get("PA_INVESTIGATOR_PASSWORD"):
        inv_auth = {"password_auth": {"enabled": True, "password": env["PA_INVESTIGATOR_PASSWORD"]}}
    elif env.get("PA_INVESTIGATOR_PIN"):
        inv_auth = {"pin_auth": {"enabled": True, "pin": env["PA_INVESTIGATOR_PIN"]}}
    else:
        raise ApiError("set PA_INVESTIGATOR_PASSWORD or PA_INVESTIGATOR_PIN")
    if env.get("PA_APPROVER_GROUP"):
        app_auth = {"bearer_auth": {"enabled": True, "distribution_groups": [group_id(api, env["PA_APPROVER_GROUP"])]}}
    elif env.get("PA_APPROVER_PIN"):
        if env.get("PA_APPROVER_PIN") == env.get("PA_INVESTIGATOR_PIN"):
            raise ApiError("the two roles must not share a credential")
        app_auth = {"pin_auth": {"enabled": True, "pin": env["PA_APPROVER_PIN"]}}
    else:
        raise ApiError("set PA_APPROVER_GROUP (SSO) or PA_APPROVER_PIN")

    restrictions = {}
    if env.get("PA_ALLOWED_COUNTRIES"):
        restrictions = {"access_restrictions": {"allowed_countries": [
            c.strip().upper() for c in env["PA_ALLOWED_COUNTRIES"].split(",") if c.strip()]}}

    def service(name: str, port: int, auth: dict) -> dict:
        fqdn = f"{name}.{domain}"
        return {"name": fqdn, "domain": fqdn, "mode": "http", "enabled": True, "pass_host_header": False,
                "rewrite_redirects": False, "private": False, "auth": auth, **restrictions,
                "targets": [{"target_id": peer["id"], "target_type": "peer", "protocol": "http", "host": host,
                             "port": port, "path": "/", "enabled": True}]}

    services = [service(prefix, int(env.get("PA_INVESTIGATOR_PORT", 8400)), inv_auth),
                service(f"{prefix}-approver", int(env.get("PA_APPROVER_PORT", 8401)), app_auth)]
    if env.get("PA_REPLAY_PORT"):  # read-only replay of a recorded run: same credential as the investigator
        services.append(service(f"{prefix}-replay", int(env["PA_REPLAY_PORT"]), inv_auth))
    return services


def ours(api, names: set[str]) -> dict[str, dict]:
    return {s["name"]: s for s in (api("GET", "/reverse-proxies/services") or []) if s.get("name") in names}


def main(argv: list[str], api=request, env: dict[str, str] | None = None, out=print) -> int:
    cmd = argv[0] if argv else "plan"
    if env is None:
        load_env()
        env = dict(os.environ)
    try:
        want = desired(api, env)
        names = {s["name"] for s in want}
        have = ours(api, names)
        if cmd == "plan":
            for s in want:
                action = "update" if s["name"] in have else "create"
                out(f"{action} {s['name']}")
                out(json.dumps(redact(s), indent=2))
        elif cmd == "apply":
            for s in want:
                if s["name"] in have:
                    api("PUT", f"/reverse-proxies/services/{have[s['name']]['id']}", s)
                    out(f"updated https://{s['domain']}")
                else:
                    api("POST", "/reverse-proxies/services", s)
                    out(f"created https://{s['domain']}")
        elif cmd == "status":
            for name in sorted(names):
                s = have.get(name)
                meta = (s or {}).get("meta") or {}
                out(f"{name}: " + (f"enabled={s.get('enabled')} status={meta.get('status')}" if s else "absent"))
        elif cmd == "delete":
            for name, s in have.items():
                api("DELETE", f"/reverse-proxies/services/{s['id']}")
                out(f"deleted {name}")
        else:
            out(__doc__)
            return 2
    except ApiError as exc:
        out(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
