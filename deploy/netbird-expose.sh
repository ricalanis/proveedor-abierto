#!/usr/bin/env bash
# Fallback: publish the product URL through NetBird's reverse proxy with `netbird expose` (NetBird >= v0.66).
# The primary path is netbird_services.py (persistent Cloud services for the product and the Ontofill Console).
# Management is NetBird Cloud (app.netbird.io): the VM's peer must be enrolled there, and an account admin must
# enable Peer Expose. The product URL is protected by a shared password or PIN. The console is not published here:
# it needs SSO restricted to the approvers group, which the Cloud service (netbird_services.py) sets up.
# The session lives while this script runs (TTL renewed every 30 s); run it under systemd (see systemd/).
# Note: `netbird expose` takes the credential as a flag, so it is visible in the local process list; restrict
# shell access on the VM.
set -euo pipefail
cd "$(dirname "$0")"
[[ -f .env ]] && set -a && . ./.env && set +a

prefix="${PA_NAME_PREFIX:-proveedor}"
inv_port="${PA_INVESTIGATOR_PORT:-8400}"

if [[ -n "${PA_INVESTIGATOR_PASSWORD:-}" ]]; then inv_auth=(--with-password "$PA_INVESTIGATOR_PASSWORD")
elif [[ -n "${PA_INVESTIGATOR_PIN:-}" ]]; then inv_auth=(--with-pin "$PA_INVESTIGATOR_PIN")
else echo "set PA_INVESTIGATOR_PASSWORD or PA_INVESTIGATOR_PIN" >&2; exit 2; fi

command -v netbird >/dev/null || { echo "netbird client not installed" >&2; exit 2; }
netbird status >/dev/null || { echo "netbird is not connected (run: netbird up)" >&2; exit 2; }

exec netbird expose "$inv_port" --with-name-prefix "$prefix" "${inv_auth[@]}"
