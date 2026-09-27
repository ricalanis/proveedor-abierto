"""NetBird evidence tables (services, VM peers, groups, policies) as HTML for screenshots (docs/evidence/).

    NETBIRD_API_TOKEN=... uv run python deploy/netbird_evidence.py OUT_DIR   # then screenshot OUT_DIR/*.html

Only allowlisted VM peers (name prefix "ontofill-") are ever named; every other peer is excluded, and the output is checked for any non-allowlisted name before saving."""
import html
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = "https://api.netbird.io/api"
OUT = Path(sys.argv[1])
ALLOW_PREFIX = "ontofill-"  # the two VM peers (control plane, sandbox host)

def get(path):
    r = urllib.request.Request(API + path, headers={"Authorization": "Token " + os.environ["NETBIRD_API_TOKEN"],
                                                    "Accept": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=30))

peers = get("/peers")
vm = {p["id"]: p for p in peers if str(p.get("name", "")).startswith(ALLOW_PREFIX)}
forbidden = {p["name"] for p in peers if p["id"] not in vm and p.get("name")}
forbidden |= {p.get("dns_label", "") for p in peers if p["id"] not in vm and p.get("dns_label")}
forbidden.discard("")
groups = get("/groups")
policies = get("/policies")
services = get("/reverse-proxies/services")
gname = {g["id"]: g["name"] for g in groups}

def table(title, head, rows):
    h = "".join(f"<th>{html.escape(x)}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<h2>{html.escape(title)}</h2><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"

svc_rows = []
for s in sorted(services, key=lambda s: s.get("name", "")):
    auth = s.get("auth") or {}
    kind = ("SSO (groups: " + ", ".join(gname.get(g, "?") for g in (auth.get("bearer_auth") or {}).get("distribution_groups", [])) + ")"
            if (auth.get("bearer_auth") or {}).get("enabled") else "password" if (auth.get("password_auth") or {}).get("enabled")
            else "PIN" if (auth.get("pin_auth") or {}).get("enabled") else "none")
    for t in s.get("targets") or []:
        peer = vm.get(t.get("target_id"))
        svc_rows.append([s.get("domain"), kind, peer["name"] if peer else "(other peer: hidden)", f'{t.get("host")}:{t.get("port")}', s.get("enabled")])
peer_rows = [[p["name"], p.get("ip"), p.get("os", "")[:28], "connected" if p.get("connected") else "offline",
              ", ".join(sorted(gname.get(g["id"], g.get("name", "?")) for g in p.get("groups") or []))] for p in vm.values()]
group_rows = [[g["name"], g.get("peers_count", len(g.get("peers") or [])),
               ", ".join(sorted(vm[p["id"]]["name"] for p in (g.get("peers") or []) if p.get("id") in vm)) or "—"]
              for g in sorted(groups, key=lambda g: g["name"])]
pol_rows = []
for p in policies:
    for r in p.get("rules") or []:
        src = ", ".join(sorted(x.get("name", gname.get(x.get("id"), "?")) for x in r.get("sources") or []))
        dst = ", ".join(sorted(x.get("name", gname.get(x.get("id"), "?")) for x in r.get("destinations") or []))
        ports = ",".join(r.get("ports") or []) or "all"
        pol_rows.append([p.get("name"), src, "→" if not r.get("bidirectional") else "↔", dst, r.get("protocol"), ports, r.get("action"), p.get("enabled")])
css = ("body{font:14px/1.45 ui-monospace,Menlo,monospace;background:#f4f4f1;color:#1d1d1b;margin:24px}"
       "h1{font:600 20px/1.2 system-ui,sans-serif}h2{font:600 15px/1.2 system-ui,sans-serif;margin:22px 0 8px}"
       "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #cfcfc8;padding:6px 10px;text-align:left}"
       "th{font-weight:600;border-bottom:2px solid #1d1d1b}.note{color:#5b5b55;font:12px system-ui,sans-serif}")
now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
pages = {
 "netbird-services": table("NetBird reverse-proxy services (the only public entry points)", ["domain", "auth", "target peer", "target (NetBird IP:port)", "enabled"], svc_rows),
 "netbird-peers-groups": table("VM peers", ["peer", "NetBird IP", "os", "status", "groups"], peer_rows)
    + table("Groups (member counts; only VM peers are named)", ["group", "members", "VM peers in it"], group_rows),
 "netbird-policies": table("Access policies", ["policy", "sources", "dir", "destinations", "protocol", "ports", "action", "enabled"], pol_rows),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, body in pages.items():
    doc = (f"<!doctype html><meta charset=utf-8><title>{name}</title><style>{css}</style>"
           f"<h1>Ontofill · NetBird evidence</h1><p class=note>From the NetBird API, {now}. Only the two VM peers are named; "
           f"other peers are excluded.</p>{body}")
    leaked = [n for n in forbidden if n and n.lower() in doc.lower()]
    if leaked:
        sys.exit(f"ABORT {name}: {len(leaked)} non-allowlisted peer name(s) would appear")
    (OUT / f"{name}.html").write_text(doc)
print("vm peers named:", len(vm), "| other peers excluded:", len(peers) - len(vm), "| services:", len(services),
      "| groups:", len(groups), "| policy rules:", len(pol_rows), "| leak check: passed")
