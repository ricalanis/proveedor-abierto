#!/usr/bin/env bash
# Prove the app's access gate.
#
#   deploy/verify.sh local
#       On the VM (or a laptop rehearsal) with `docker compose up` running: both role processes answer on
#       loopback only, nothing listens on a public interface, the investigator process refuses approval routes
#       and cannot write the case, the approver process can reach them.
#
#   deploy/verify.sh remote <vm-public-ip> <investigator-url> <approver-url>
#       From outside: the VM exposes no inbound port at all (SSH included), and both NetBird URLs refuse
#       unauthenticated requests (no app page is served without the role's credential).
#       Optional: PA_INVESTIGATOR_COOKIE="name=value" (a session cookie after logging in to the investigator URL)
#       also checks that the investigator URL cannot reach approver routes.
set -uo pipefail
cd "$(dirname "$0")"
[[ -f .env ]] && set -a && . ./.env && set +a

INV_PORT="${PA_INVESTIGATOR_PORT:-8400}"
APP_PORT="${PA_APPROVER_PORT:-8401}"
BIND_IP="${PA_BIND_IP:-127.0.0.1}"
APP_MARKER='class="wordmark"'   # present on every app page; must never appear without authentication
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
  echo "Local gate checks (bind ${BIND_IP}, investigator :${INV_PORT}, approver :${APP_PORT})"
  for port in "$INV_PORT" "$APP_PORT"; do
    addrs=$(listeners "$port" | sort -u)
    if [[ -z "$addrs" ]]; then fail "nothing listens on :$port (is compose up?)"; continue; fi
    if echo "$addrs" | grep -Eq '^(\*|0\.0\.0\.0|\[::\]|::):'; then
      fail ":$port listens on all interfaces: $(echo "$addrs" | tr '\n' ' ')"
    elif echo "$addrs" | grep -vq "^${BIND_IP//./\\.}:\|^\[::1\]:"; then
      fail ":$port listens beyond ${BIND_IP}: $(echo "$addrs" | tr '\n' ' ')"
    else
      pass ":$port bound to $(echo "$addrs" | tr '\n' ' ')"
    fi
  done

  role=$(curl -s --max-time 5 "http://${BIND_IP}:${INV_PORT}/healthz" | grep -o '"role":"[a-z]*"')
  [[ "$role" == '"role":"investigator"' ]] && pass "investigator process answers (${role})" || fail "investigator /healthz: ${role:-no answer}"
  role=$(curl -s --max-time 5 "http://${BIND_IP}:${APP_PORT}/healthz" | grep -o '"role":"[a-z]*"')
  [[ "$role" == '"role":"approver"' ]] && pass "approver process answers (${role})" || fail "approver /healthz: ${role:-no answer}"

  c=$(code "http://${BIND_IP}:${INV_PORT}/approvals")
  [[ "$c" == 403 ]] && pass "investigator GET /approvals -> 403" || fail "investigator GET /approvals -> $c (want 403)"
  c=$(code -X POST -d 'phase_dir=01-scope&approver=verify' "http://${BIND_IP}:${INV_PORT}/approvals")
  [[ "$c" == 403 ]] && pass "investigator POST /approvals -> 403" || fail "investigator POST /approvals -> $c (want 403)"
  c=$(code "http://${BIND_IP}:${APP_PORT}/approvals")
  [[ "$c" == 200 ]] && pass "approver GET /approvals -> 200" || fail "approver GET /approvals -> $c (want 200)"
  c=$(code -H 'Origin: https://attacker.example' -X POST -d 'phase_dir=01-scope&approver=x' "http://${BIND_IP}:${APP_PORT}/approvals")
  [[ "$c" == 403 ]] && pass "approver refuses cross-origin POST -> 403" || fail "approver cross-origin POST -> $c (want 403)"

  ip=$(host_ip)
  if [[ -n "$ip" && "$ip" != "$BIND_IP" ]]; then
    for port in "$INV_PORT" "$APP_PORT"; do
      if port_open "$ip" "$port" 2; then fail "reachable on non-loopback ${ip}:${port}"
      else pass "not reachable on non-loopback ${ip}:${port}"; fi
    done
  else
    warn "no non-loopback IPv4 found to probe"
  fi

  if command -v docker >/dev/null && docker compose ps -q investigator >/dev/null 2>&1; then
    if docker compose exec -T investigator sh -c 'touch /case/.verify-write' 2>/dev/null; then
      fail "investigator container can write the case"
      docker compose exec -T investigator rm -f /case/.verify-write 2>/dev/null
    else
      pass "investigator container cannot write the case (read-only mount)"
    fi
    if docker compose exec -T investigator sh -c 'touch /srv/app/.verify-write' 2>/dev/null; then
      fail "investigator container root filesystem is writable"
    else
      pass "investigator container root filesystem is read-only"
    fi
  fi
}

remote_mode() {
  local vm=$1 inv=$2 app=$3
  echo "Remote gate checks (VM ${vm})"
  for port in 80 443 3000 5000 5432 7700 7878 8000 8080 8400 8401 8402 8443 8700 8702 8766 9000; do
    if port_open "$vm" "$port" 3; then fail "VM port $port is open"; else pass "VM port $port closed"; fi
  done
  # Zero public inbound ports, SSH included: administration goes over NetBird.
  if port_open "$vm" 22 3; then fail "VM port 22 (ssh) is open publicly; admin must go over NetBird"
  else pass "VM port 22 closed"; fi

  for url in "$inv" "$inv/approvals" "$app" "$app/approvals" "$app/api/run/x"; do
    body=$(curl -s -L --max-time 10 "$url")
    c=$(code -L "$url")
    if grep -q "$APP_MARKER" <<<"$body"; then fail "unauthenticated $url served the app (HTTP $c)"
    else pass "unauthenticated $url refused (HTTP $c, no app content)"; fi
  done

  if [[ -n "${PA_INVESTIGATOR_COOKIE:-}" ]]; then
    c=$(code -H "Cookie: ${PA_INVESTIGATOR_COOKIE}" "$inv/")
    [[ "$c" == 200 ]] && pass "investigator URL with its credential -> 200" || fail "investigator URL with credential -> $c"
    c=$(code -H "Cookie: ${PA_INVESTIGATOR_COOKIE}" "$inv/approvals")
    [[ "$c" == 403 ]] && pass "investigator URL cannot reach approver routes -> 403" || fail "investigator /approvals -> $c (want 403)"
  else
    warn "PA_INVESTIGATOR_COOKIE not set: skipped the authenticated role-boundary check (covered by local mode)"
  fi
}

case "${1:-}" in
  local) local_mode ;;
  remote) [[ $# -eq 4 ]] || { echo "usage: $0 remote <vm-ip> <investigator-url> <approver-url>" >&2; exit 2; }
          remote_mode "$2" "$3" "$4" ;;
  *) echo "usage: $0 local | remote <vm-ip> <investigator-url> <approver-url>" >&2; exit 2 ;;
esac

if (( fails )); then echo "RESULT: FAIL ($fails)"; exit 1; fi
echo "RESULT: PASS"
