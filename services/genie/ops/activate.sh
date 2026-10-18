#!/usr/bin/env bash
# Bring the releases `release.sh publish` laid down into service on the VPS
# (docs/specs/17-cutover.md §5; #258). Run by `just cutover services --run`
# after both publishes, so a services deploy is one command:
#   - each service's virtualenv is built in its new release (`uv sync --locked`:
#     the publish ships no .venv, and the units run current/.venv);
#   - the quality worker's unit is installed or updated from the release;
#   - systemd reloads, and the engine, Genie and the quality worker restart;
#   - each unit must be active afterwards, or the run fails.
# The one thing it does not do is set the token: GENIE_JUDGE_TOKEN in
# /etc/linker-genie.env (and LINKER_GENIE_JUDGE_TOKEN in the site's
# wp-config.php) are placed by hand. Without it the worker is installed but
# not started, and the run exits 3 saying so.
# Every path is a parameter so tests run it against a temporary tree.
set -euo pipefail

UV="${UV:-/root/.local/bin/uv}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"
GENIE_ENV="${GENIE_ENV_FILE:-/etc/linker-genie.env}"
ENGINE_ROOT="${ENGINE_RELEASE_ROOT:-/opt/linker-engine}"
GENIE_ROOT="${GENIE_RELEASE_ROOT:-/opt/linker-genie}"
JUDGE_UNIT="linker-genie-judge.service"
# Seconds to wait before asking whether a restarted unit is still up: the
# worker checks its settings and credentials at start and exits 2 within a
# second when one is missing (linker_genie.quality.worker.main).
SETTLE="${ACTIVATE_SETTLE_SECONDS:-3}"

for root in "$ENGINE_ROOT" "$GENIE_ROOT"; do
    (cd "$root/current" && "$UV" sync --locked --quiet)
    echo "synced $root/current"
done

install -m 644 "$GENIE_ROOT/current/ops/$JUDGE_UNIT" "$UNIT_DIR/$JUDGE_UNIT"
systemctl daemon-reload
echo "installed $UNIT_DIR/$JUDGE_UNIT"

units=(linker-engine.service linker-genie.service)
judge=no
if grep -q '^GENIE_JUDGE_TOKEN=.' "$GENIE_ENV" 2>/dev/null; then
    systemctl enable --quiet "$JUDGE_UNIT"
    units+=("$JUDGE_UNIT")
    judge=yes
else
    systemctl disable --now --quiet "$JUDGE_UNIT" 2>/dev/null || true
fi

if ! grep -q '^GENIE_SERVICE_TOKEN=.' "$GENIE_ENV" 2>/dev/null; then
    echo "$GENIE_ENV has no GENIE_SERVICE_TOKEN: the service would answer 503 to every Genie POST (gate.py, #236). Set it there and LINKER_GENIE_SERVICE_TOKEN in the site's wp-config.php to the same value (the local stack writes both: tools/local/src/linker_local/services.py)." >&2
    exit 3
fi

systemctl restart "${units[@]}"
sleep "$SETTLE"
failed=0
for unit in "${units[@]}"; do
    if systemctl is-active --quiet "$unit"; then
        echo "active $unit"
    else
        echo "NOT ACTIVE $unit (journalctl -u $unit)" >&2
        failed=1
    fi
done
if (( failed )); then
    exit 1
fi
if [[ "$judge" == no ]]; then
    echo "$JUDGE_UNIT installed but not started: GENIE_JUDGE_TOKEN is not set in $GENIE_ENV" >&2
    exit 3
fi
