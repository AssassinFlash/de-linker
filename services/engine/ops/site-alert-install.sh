#!/usr/bin/env bash
# Install, verify or roll back the site-alert unit on the engine host.
# Follows network-boundary.sh: a backup mode that only writes a tar stream to
# the operator machine, an apply mode that installs reviewed files, and a
# rollback mode that restores exactly those paths. Nothing here touches the
# shared host, nginx, the firewall or any customer-facing service.
set -euo pipefail
ROOT="${LINKER_ALERT_ROOT:-/}"
OPS_DIR="${LINKER_ALERT_OPS:-opt/linker-engine/ops}"
SYSTEMD="${SYSTEMD_UNIT_DIR:-etc/systemd/system}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="${OPS_DIR#/}"
SYSTEMD="${SYSTEMD#/}"
# Relative, so `tar -C ROOT` never sees an absolute member name.
MANAGED=(
    "$OPS_DIR/site-alert.py"
    "$SYSTEMD/linker-site-alert.service"
    "$SYSTEMD/linker-site-alert.timer"
    "etc/linker-site-alert.env"
)
CONFIG="$ROOT/etc/linker-site-alert.env"
usage() { echo "usage: $0 backup | apply | verify | rollback < backup.tar" >&2; exit 2; }
[[ $# == 1 ]] || usage

case "$1" in
    backup)
        # One archive of the managed paths that exist, modes preserved, streamed
        # to the operator machine; the host keeps no copy.
        existing=()
        for relative in "${MANAGED[@]}"; do
            [[ -e "$ROOT/$relative" ]] && existing+=("$relative")
        done
        [[ ${#existing[@]} -gt 0 ]] || { echo "nothing installed yet" >&2; exit 0; }
        tar -C "$ROOT" -cpf - "${existing[@]}"
        ;;
    apply)
        [[ -f "$CONFIG" ]] || {
            echo "missing $CONFIG" >&2
            echo "Create it with LINKER_SMTP_HOST/PORT/USER/PASS copied from" >&2
            echo "~/.config/terravolt-builder/sunriver-smtp.env on the shared host" >&2
            echo "(plus LINKER_ALERT_TO if it differs from the 2026-10-17 ruling)," >&2
            echo "mode 600, then rerun apply." >&2
            exit 1
        }
        install -m 755 "$HERE/site-alert.py" "$ROOT/$OPS_DIR/site-alert.py"
        install -m 644 "$HERE/linker-site-alert.service" \
            "$ROOT/$SYSTEMD/linker-site-alert.service"
        install -m 644 "$HERE/linker-site-alert.timer" \
            "$ROOT/$SYSTEMD/linker-site-alert.timer"
        systemctl daemon-reload
        systemctl enable --quiet linker-site-alert.timer
        systemctl start linker-site-alert.timer
        echo "installed $ROOT/$OPS_DIR/site-alert.py and the timer"
        ;;
    verify)
        # Prints the resolved SMTP identity (never the password) and the
        # decision for the current record, without sending or writing state.
        /usr/bin/python3 "$ROOT/$OPS_DIR/site-alert.py" --check-config
        /usr/bin/python3 "$ROOT/$OPS_DIR/site-alert.py" --dry-run
        systemctl list-timers linker-site-alert.timer --no-pager
        ;;
    rollback)
        # Stop first: a restored unit must not keep running the new code.
        systemctl disable --quiet --now linker-site-alert.timer 2>/dev/null || true
        tar -C "$ROOT" -xpf -
        systemctl daemon-reload
        ;;
    *) usage ;;
esac
