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
    "$OPS_DIR/site-probe.sh"
    "$SYSTEMD/linker-site-probe.service"
    "$SYSTEMD/linker-site-probe.timer"
    "$SYSTEMD/linker-site-alert.service"
    "$SYSTEMD/linker-site-alert.timer"
    "etc/linker-site-alert.env"
)
CONFIG="$ROOT/etc/linker-site-alert.env"
usage() { echo "usage: $0 backup | apply | verify | rollback < backup.tar" >&2; exit 2; }
[[ $# == 1 ]] || usage

timer_state() {
    local unit enabled active
    for unit in linker-site-probe.timer linker-site-alert.timer; do
        enabled=0
        active=0
        if systemctl is-enabled --quiet "$unit"; then enabled=1; fi
        if systemctl is-active --quiet "$unit"; then active=1; fi
        printf '%s %s %s\n' "$unit" "$enabled" "$active"
    done
}

case "$1" in
    backup)
        # One archive of the managed paths that exist, modes preserved, streamed
        # to the operator machine; the host keeps no copy.
        existing=()
        for relative in "${MANAGED[@]}"; do
            [[ -e "$ROOT/$relative" ]] && existing+=("$relative")
        done
        [[ ${#existing[@]} -gt 0 ]] || { echo "nothing installed yet" >&2; exit 0; }
        saved=$(mktemp -d)
        trap 'rm -rf "$saved"' EXIT
        timer_state > "$saved/timer-state"
        tar -C "$ROOT" -cpf - "${existing[@]}" -C "$saved" timer-state
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
        if [[ "$HERE/site-probe.sh" -ef "$ROOT/$OPS_DIR/site-probe.sh" ]]; then
            echo "Run apply from a separate directory containing the reviewed release files." >&2
            exit 1
        fi
        install -m 755 "$HERE/site-probe.sh" "$ROOT/$OPS_DIR/site-probe.sh"
        install -m 644 "$HERE/linker-site-probe.service" "$ROOT/$SYSTEMD/linker-site-probe.service"
        install -m 644 "$HERE/linker-site-probe.timer" "$ROOT/$SYSTEMD/linker-site-probe.timer"
        install -m 755 "$HERE/site-alert.py" "$ROOT/$OPS_DIR/site-alert.py"
        install -m 644 "$HERE/linker-site-alert.service" \
            "$ROOT/$SYSTEMD/linker-site-alert.service"
        install -m 644 "$HERE/linker-site-alert.timer" \
            "$ROOT/$SYSTEMD/linker-site-alert.timer"
        systemctl daemon-reload
        systemctl enable --quiet linker-site-probe.timer
        systemctl start linker-site-probe.timer
        systemctl enable --quiet linker-site-alert.timer
        systemctl start linker-site-alert.timer
        echo "installed $ROOT/$OPS_DIR/site-alert.py and the timer"
        ;;
    verify)
        # Prints the resolved SMTP identity (never the password) and the
        # decision for the current record, without sending or writing state.
        /usr/bin/python3 "$ROOT/$OPS_DIR/site-alert.py" --check-config
        /usr/bin/python3 "$ROOT/$OPS_DIR/site-alert.py" --dry-run
        systemctl list-timers linker-site-probe.timer linker-site-alert.timer --no-pager
        ;;
    rollback)
        saved=$(mktemp -d)
        trap 'rm -rf "$saved"' EXIT
        tar -C "$saved" -xpf -
        for relative in "${MANAGED[@]}"; do
            # The deployed SMTP configuration stays in place when an operator
            # excludes private credentials from the code recovery archive.
            if [[ "$relative" != 'etc/linker-site-alert.env' && ! -f "$saved/$relative" ]]; then
                echo "Incomplete monitor backup: missing $relative." >&2
                exit 1
            fi
        done
        if [[ ! -f "$saved/timer-state" ]] || ! awk '
            NR == 1 && /^linker-site-probe[.]timer [01] [01]$/ { next }
            NR == 2 && /^linker-site-alert[.]timer [01] [01]$/ { next }
            { invalid = 1 }
            END { exit (invalid || NR != 2) }
        ' "$saved/timer-state"; then
            echo "Incomplete monitor backup: both original timer settings are required." >&2
            exit 1
        fi
        systemctl disable --quiet --now linker-site-alert.timer
        systemctl disable --quiet --now linker-site-probe.timer
        systemctl stop linker-site-alert.service linker-site-probe.service
        for relative in "${MANAGED[@]}"; do
            if [[ -f "$saved/$relative" ]]; then
                cp -p "$saved/$relative" "$ROOT/$relative"
            fi
        done
        systemctl daemon-reload
        while read -r unit enabled active; do
            if [[ "$enabled" == 1 ]]; then systemctl enable --quiet "$unit"; fi
            if [[ "$active" != 1 ]]; then continue; fi
            if [[ "$unit" == linker-site-alert.timer ]]; then
                # Give a restored two-column notifier a current reading before
                # it can see only obsolete lines and send a silence alert.
                last="$ROOT/$OPS_DIR/../state/site-probe.last"
                previous=$(cat "$last" 2>/dev/null || true)
                if ! systemctl start linker-site-probe.service; then
                    # A real HTTP outage exits 1 after recording its result.
                    [[ -s "$last" && "$(< "$last")" != "$previous" ]] || exit 1
                fi
            fi
            systemctl start "$unit"
        done < "$saved/timer-state"
        ;;
    *) usage ;;
esac
