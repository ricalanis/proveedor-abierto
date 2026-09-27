#!/usr/bin/env bash
# Prove the access gate of the two public services: the product (this app) and the Ontofill Console.
#
#   deploy/verify.sh local
#       On the VM (or a laptop rehearsal) with `docker compose up` running: the product process answers on
#       loopback (or PA_BIND_IP) only, nothing listens on a public interface, it has no approval routes (404) and
#       cannot write the case or its own root filesystem.
#
#   deploy/verify.sh remote <vm-public-ip> <product-url> <console-url>
#       From outside: the VM exposes no inbound port at all (SSH included), and both NetBird URLs refuse
#       unauthenticated requests (no product page and no console page is served without the credential).
#       Optional: PA_INVESTIGATOR_COOKIE="name=value" (a session cookie after logging in to the product URL)
#       also checks that the product URL serves the app and has no approval routes.
set -uo pipefail
cd "$(dirname "$0")"
[[ -f .env ]] && set -a && . ./.env && set +a

INV_PORT="${PA_INVESTIGATOR_PORT:-8400}"
BIND_IP="${PA_BIND_IP:-127.0.0.1}"
APP_MARKER='class="wordmark"'       # present on every product page; must never appear without authentication
CONSOLE_MARKER='Ontofill Console'   # present on every console page; must never appear without authentication
fails=0

pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; fails=$((fails + 1)); }
# port_open HOST PORT SECONDS: TCP connect check with a bounded connect time. macOS (BSD) nc treats -w as an idle
# timeout only, so a filtered port would hang ~75 s; -G bounds the connect there. Linux (OpenBSD) nc bounds it with -w.
port_open() {
  if [ "$(uname -s)" = Darwin ]; then nc -z -G "$3" -w "$3" "$1" "$2" 2>/dev/null
  else nc -z -w "$3" "$1" "$2" 2>/dev/null; fi
}
warn() { printf '  WARN  %s\n' "$1"; }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$@"; }

listeners() {  # "addr:port" lines for TCP listeners on a port
  local port=$1
  if command -v ss >/dev/null; then
    ss -H -ltn "sport = :$port" | awk '{print $4}'
  else
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}'
  fi
}

host_ip() {  # a non-loopback IPv4 of this machine
  if command -v ip >/dev/null; then
    ip -4 -o addr show scope global | awk '{split($4, a, "/"); print a[1]; exit}'
  else
    ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null
  fi
}

local_mode() {
  echo "Local gate checks (bind ${BIND_IP}, product :${INV_PORT})"
  addrs=$(listeners "$INV_PORT" | sort -u)
  if [[ -z "$addrs" ]]; then fail "nothing listens on :$INV_PORT (is compose up?)"
  elif echo "$addrs" | grep -Eq '^(\*|0\.0\.0\.0|\[::\]|::):'; then
    fail ":$INV_PORT listens on all interfaces: $(echo "$addrs" | tr '\n' ' ')"
  elif echo "$addrs" | grep -vq "^${BIND_IP//./\\.}:\|^\[::1\]:"; then
    fail ":$INV_PORT listens beyond ${BIND_IP}: $(echo "$addrs" | tr '\n' ' ')"
  else
    pass ":$INV_PORT bound to $(echo "$addrs" | tr '\n' ' ')"
  fi

  c=$(code "http://${BIND_IP}:${INV_PORT}/healthz")
  [[ "$c" == 200 ]] && pass "product process answers /healthz" || fail "product /healthz -> ${c:-no answer}"

  # Approvals live in the Ontofill Console; the product has no such routes at all.
  c=$(code "http://${BIND_IP}:${INV_PORT}/approvals")
  [[ "$c" == 404 ]] && pass "product GET /approvals -> 404 (no approval routes)" || fail "product GET /approvals -> $c (want 404)"
  c=$(code -X POST -d 'phase_dir=01-scope&approver=verify' "http://${BIND_IP}:${INV_PORT}/approvals")
  [[ "$c" == 404 || "$c" == 405 ]] && pass "product POST /approvals -> $c (no approval routes)" || fail "product POST /approvals -> $c (want 404)"

  ip=$(host_ip)
  if [[ -n "$ip" && "$ip" != "$BIND_IP" ]]; then
    if port_open "$ip" "$INV_PORT" 2; then fail "reachable on non-loopback ${ip}:${INV_PORT}"
    else pass "not reachable on non-loopback ${ip}:${INV_PORT}"; fi
  else
    warn "no non-loopback IPv4 found to probe"
  fi

  if command -v docker >/dev/null && docker compose ps -q investigator >/dev/null 2>&1; then
    if docker compose exec -T investigator sh -c 'touch /case/.verify-write' 2>/dev/null; then
      fail "product container can write the case"
      docker compose exec -T investigator rm -f /case/.verify-write 2>/dev/null
    else
      pass "product container cannot write the case (read-only mount)"
    fi
    if docker compose exec -T investigator sh -c 'touch /srv/app/.verify-write' 2>/dev/null; then
      fail "product container root filesystem is writable"
    else
      pass "product container root filesystem is read-only"
    fi
  fi
}

remote_mode() {
  local vm=$1 product=$2 console=$3
  echo "Remote gate checks (VM ${vm})"
  for port in 80 443 3000 5000 5432 7700 7878 8000 8080 8400 8401 8402 8410 8443 8700 8702 8766 9000; do
    if port_open "$vm" "$port" 3; then fail "VM port $port is open"; else pass "VM port $port closed"; fi
  done
  # Zero public inbound ports, SSH included: administration goes over NetBird.
  if port_open "$vm" 22 3; then fail "VM port 22 (ssh) is open publicly; admin must go over NetBird"
  else pass "VM port 22 closed"; fi

  for url in "$product" "$product/data"; do
    body=$(curl -s -L --max-time 10 "$url")
    c=$(code -L "$url")
    if grep -q "$APP_MARKER" <<<"$body"; then fail "unauthenticated $url served the product (HTTP $c)"
    else pass "unauthenticated $url refused (HTTP $c, no product content)"; fi
  done
  for url in "$console" "$console/cases/x" "$console/evidence" "$console/whoami"; do
    body=$(curl -s -L --max-time 10 "$url")
    c=$(code -L "$url")
    if grep -q "$CONSOLE_MARKER" <<<"$body"; then fail "unauthenticated $url served the console (HTTP $c)"
    else pass "unauthenticated $url refused (HTTP $c, no console content)"; fi
  done

  if [[ -n "${PA_INVESTIGATOR_COOKIE:-}" ]]; then
    c=$(code -H "Cookie: ${PA_INVESTIGATOR_COOKIE}" "$product/")
    [[ "$c" == 200 ]] && pass "product URL with its credential -> 200" || fail "product URL with credential -> $c"
    c=$(code -H "Cookie: ${PA_INVESTIGATOR_COOKIE}" "$product/approvals")
    [[ "$c" == 404 ]] && pass "product URL has no approval routes -> 404" || fail "product /approvals -> $c (want 404)"
  else
    warn "PA_INVESTIGATOR_COOKIE not set: skipped the authenticated product check (covered by local mode)"
  fi
}

case "${1:-}" in
  local) local_mode ;;
  remote) [[ $# -eq 4 ]] || { echo "usage: $0 remote <vm-ip> <product-url> <console-url>" >&2; exit 2; }
          remote_mode "$2" "$3" "$4" ;;
  *) echo "usage: $0 local | remote <vm-ip> <product-url> <console-url>" >&2; exit 2 ;;
esac

if (( fails )); then echo "RESULT: FAIL ($fails)"; exit 1; fi
echo "RESULT: PASS"
