#!/usr/bin/env bash
# Publish the two role URLs through NetBird's reverse proxy (`netbird expose`, NetBird >= v0.66).
# Each URL gets its own credential, so access matches the role:
#   investigator (read-only app)  -> shared password or PIN
#   approver (phase sign-off)     -> SSO restricted to an IdP group (preferred) or a different PIN
# Sessions live while this script runs (TTL renewed every 30 s); run it under systemd (see systemd/).
# Note: `netbird expose` takes the credential as a flag, so it is visible in the local process list;
# prefer SSO groups for the approver, and restrict shell access on the VM.
set -euo pipefail
cd "$(dirname "$0")"
[[ -f .env ]] && set -a && . ./.env && set +a

prefix="${PA_NAME_PREFIX:-proveedor}"
inv_port="${PA_INVESTIGATOR_PORT:-8400}"
app_port="${PA_APPROVER_PORT:-8401}"

if [[ -n "${PA_INVESTIGATOR_PASSWORD:-}" ]]; then inv_auth=(--with-password "$PA_INVESTIGATOR_PASSWORD")
elif [[ -n "${PA_INVESTIGATOR_PIN:-}" ]]; then inv_auth=(--with-pin "$PA_INVESTIGATOR_PIN")
else echo "set PA_INVESTIGATOR_PASSWORD or PA_INVESTIGATOR_PIN" >&2; exit 2; fi

if [[ -n "${PA_APPROVER_GROUPS:-}" ]]; then app_auth=(--with-user-groups "$PA_APPROVER_GROUPS")
elif [[ -n "${PA_APPROVER_PIN:-}" ]]; then app_auth=(--with-pin "$PA_APPROVER_PIN")
else echo "set PA_APPROVER_GROUPS (SSO) or PA_APPROVER_PIN" >&2; exit 2; fi

if [[ "${PA_INVESTIGATOR_PIN:-x}" == "${PA_APPROVER_PIN:-y}" ]]; then
  echo "the two roles must not share a credential" >&2; exit 2
fi

command -v netbird >/dev/null || { echo "netbird client not installed" >&2; exit 2; }
netbird status >/dev/null || { echo "netbird is not connected (run: netbird up)" >&2; exit 2; }

trap 'kill 0' EXIT
netbird expose "$inv_port" --with-name-prefix "$prefix" "${inv_auth[@]}" &
netbird expose "$app_port" --with-name-prefix "${prefix}-approver" "${app_auth[@]}" &
wait -n   # if either session dies, stop both so systemd restarts a consistent pair
