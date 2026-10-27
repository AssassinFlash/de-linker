#!/usr/bin/env bash
# Dedicated gateway configuration only; never restart the engine or shared nginx.
# Stream backup to a private file on the operator machine before apply/rollback.
set -euo pipefail
ROOT="${LINKER_TLS_ROOT:-/}"
HERE="$(cd "$(dirname "$0")" && pwd)"
NGINX="${NGINX:-/usr/sbin/nginx}"
SYSTEMCTL="${SYSTEMCTL:-/usr/bin/systemctl}"
RELATIVE="etc/linker-engine-tls/nginx.conf"
TARGET="${ROOT%/}/$RELATIVE"
TEMPORARY=""

usage() {
    echo "usage: $0 backup | apply <current-sha256> | rollback <current-sha256> < backup.tar" >&2
    exit 2
}
cleanup() { [[ -z "$TEMPORARY" ]] || rm -f -- "$TEMPORARY"; }
trap cleanup EXIT
digest() {
    python3 - "$1" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}
guard() {
    [[ "$EXPECTED" =~ ^[a-f0-9]{64}$ ]] || usage
    if [[ "$(digest "$TARGET")" != "$EXPECTED" ]]; then
        echo "Dedicated gateway configuration changed; refusing replacement." >&2
        exit 1
    fi
}

[[ $# -ge 1 && -f "$TARGET" && ! -L "$TARGET" ]] || usage
if [[ "$1" == backup ]]; then
    [[ $# == 1 ]] || usage
    COPYFILE_DISABLE=1 tar -C "$ROOT" -cpf - "$RELATIVE"
    exit 0
fi
[[ $# == 2 && ( "$1" == apply || "$1" == rollback ) ]] || usage
EXPECTED="$2"
guard
# A same-directory temporary file makes replacement atomic and retains the
# existing owner's mode. No server-side backup/archive is created.
TEMPORARY="$(mktemp "$(dirname "$TARGET")/.linker-tls-log.XXXXXX")"
cp -p -- "$TARGET" "$TEMPORARY"
if [[ "$1" == apply ]]; then
    cat "$HERE/nginx.conf" > "$TEMPORARY"
else
    # Extract contents of this one known member, never arbitrary archive paths.
    tar -xOf - "$RELATIVE" > "$TEMPORARY"
fi
"$NGINX" -t -q -c "$TEMPORARY"
CANDIDATE="$(digest "$TEMPORARY")"
guard
mv -f -- "$TEMPORARY" "$TARGET"
TEMPORARY=""
[[ "$(digest "$TARGET")" == "$CANDIDATE" ]]
"$NGINX" -t -q -c "$TARGET"
"$SYSTEMCTL" reload linker-engine-tls.service
"$SYSTEMCTL" is-active --quiet linker-engine-tls.service
echo "Dedicated gateway configuration installed: $CANDIDATE" >&2
