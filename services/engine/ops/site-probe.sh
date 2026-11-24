#!/bin/bash
# One complete, bounded reading per cycle for the independent VPS notifier.
set -eu
STATE=${1:-/opt/linker-engine/state}
LOG="$STATE/site-probe.log"
LAST="$STATE/site-probe.last"
PROBE_LOG_MAX=2016

health() {
    local url=$1 service=$2 reply code body
    if ! reply=$(curl -sS --max-time 15 -w $'\n%{http_code}' "$url" 2>/dev/null); then
        echo 000
        return
    fi
    code=${reply##*$'\n'}
    body=${reply%$'\n'*}
    if [[ "$code" == 200 ]] && ! python3 -c '
import json,sys
try:
    data=json.load(sys.stdin)
    ok=isinstance(data,dict) and data.get("status")=="ok"
    if sys.argv[1]=="planner":
        ok=ok and data.get("service")=="linker-planner-http" and data.get("worker_alive") is True and data.get("workspace_readable") is True
except ValueError:
    ok=False
sys.exit(0 if ok else 1)
' "$service" <<< "$body"; then
        code=200/invalid
    fi
    echo "$code"
}

wordpress=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 https://de-linker.com/wp-json/ 2>/dev/null) || wordpress=000
engine=$(health http://127.0.0.1:8901/health engine)
planner=$(health http://127.0.0.1:8911/health planner)
genie=$(health http://127.0.0.1:8902/health genie)
line="$(date -u +%Y-%m-%dT%H:%M:%SZ) $wordpress $engine $planner $genie"
printf '%s\n' "$line" >> "$LOG"
printf '%s\n' "$line" > "$LAST"
tail -n "$PROBE_LOG_MAX" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
[[ "$wordpress $engine $planner $genie" == "200 200 200 200" ]]
