#!/bin/bash
# Site probe: one database-backed URL every run, one line of record.
# Keeps at most PROBE_LOG_MAX lines so a long outage cannot grow the log
# unbounded (goal E: no unbounded accumulation).
set -u
STATE=/opt/linker-engine/state
LOG="$STATE/site-probe.log"
LAST="$STATE/site-probe.last"
URL="https://de-linker.com/wp-json/"
PROBE_LOG_MAX=2016  # 5-minute cadence for one week; older lines fall off.

# curl always prints the final %http_code on stdout — including 000 when the
# connection never completes — so no fallback echo: appending one would
# double the code (measured "000000" on the live outage, 2026-11-11).
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$URL" 2>/dev/null)
[ -n "$code" ] || code=000
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$now $code" >> "$LOG"
echo "$now $code" > "$LAST"
tail -n "$PROBE_LOG_MAX" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
[ "$code" = "200" ]
