#!/usr/bin/env bash
# Run only after reviewed code is released and a local streamed backup verified.
# backup emits only a tar stream: redirect it to the operator machine, not the VPS.
# This touches the dedicated Linker instance, never the shared nginx/firewall/SSH.
set -euo pipefail
ROOT="${LINKER_BOUNDARY_ROOT:-/}"
HERE="$(cd "$(dirname "$0")" && pwd)"
NGINX="${NGINX:-/usr/sbin/nginx}"
FILES=(etc/linker-engine-tls/nginx.conf etc/systemd/system/linker-engine.service)
usage() { echo "usage: $0 backup | apply | rollback < backup.tar" >&2; exit 2; }
[[ $# == 1 ]] || usage
case "$1" in
    backup)
        tar -C "$ROOT" -cpf - "${FILES[@]}"
        ;;
    apply)
        # Syntax-check candidate before replacing either live configuration.
        "$NGINX" -t -q -c "$HERE/nginx.conf"
        install -m 644 "$HERE/nginx.conf" "$ROOT/${FILES[0]}"
        install -m 644 "$HERE/linker-engine.service" "$ROOT/${FILES[1]}"
        ;;
    rollback)
        # Only these two known paths can be restored, preserving archive modes.
        tar -C "$ROOT" -xpf - "${FILES[@]}"
        ;;
    *) usage ;;
esac
if [[ "$1" != backup ]]; then
    "$NGINX" -t -q -c "$ROOT/${FILES[0]}"
    systemctl daemon-reload
    systemctl restart linker-engine.service
    systemctl reload linker-engine-tls.service
    systemctl is-active --quiet linker-engine.service linker-engine-tls.service
fi
