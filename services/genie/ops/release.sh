#!/usr/bin/env bash
# Publish, roll back or report a Genie service release.
# Layout (docs/specs/13-genie.md): $ROOT/<version>/ and current -> version.
# Default root is /opt/linker-genie on the VPS. Bash 3.2 (macOS) compatible.
set -euo pipefail

ROOT="${GENIE_RELEASE_ROOT:-/opt/linker-genie}"
KEEP="${GENIE_RELEASE_KEEP:-3}"

usage() {
    echo "usage: $0 publish <source-dir> | rollback | status" >&2
    exit 2
}

list_versions() {
    python3 - "$ROOT" <<'PY'
import os
import re
import sys

root = sys.argv[1]
if not os.path.isdir(root):
    raise SystemExit(0)
for name in sorted(os.listdir(root)):
    path = os.path.join(root, name)
    # Only directories named by publish() are releases. Persistent ops, state
    # and index directories must never consume retention or become a rollback.
    if (re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", name)
            and os.path.isdir(path) and not os.path.islink(path)):
        print(name)
PY
}

current() {
    if [[ -L "$ROOT/current" ]]; then
        readlink "$ROOT/current"
    fi
}

switch() {
    local version="$1"
    local tmp
    tmp="$ROOT/.current-$$"
    rm -f "$tmp"
    ln -s "$version" "$tmp"
    # Replace the symlink itself. `ln -sfn current` on macOS follows a
    # directory target and writes inside the previous release.
    python3 - "$tmp" "$ROOT/current" <<'PY'
import os
import sys

tmp, dest = sys.argv[1], sys.argv[2]
if os.path.lexists(dest):
    os.unlink(dest)
os.rename(tmp, dest)
PY
}

publish() {
    local source="$1"
    local version dest live extra
    version="$(python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))')"
    dest="$ROOT/$version"
    mkdir -p "$ROOT"
    mkdir "$dest"
    cp -a "$source"/. "$dest/"
    switch "$version"
    live="$(current)"
    extra=0
    while IFS= read -r v; do
        extra=$((extra + 1))
    done < <(list_versions)
    extra=$((extra - KEEP))
    if (( extra > 0 )); then
        while IFS= read -r v; do
            if (( extra <= 0 )); then
                break
            fi
            if [[ "$v" != "$live" ]]; then
                rm -rf "$ROOT/$v"
                extra=$((extra - 1))
            fi
        done < <(list_versions)
    fi
    echo "current=$(current)"
}

rollback() {
    local live previous="" v
    live="$(current)"
    [[ -n "$live" ]] || { echo "no current release" >&2; exit 1; }
    while IFS= read -r v; do
        if [[ "$v" == "$live" ]]; then
            break
        fi
        previous="$v"
    done < <(list_versions)
    [[ -n "$previous" ]] || { echo "no older release" >&2; exit 1; }
    switch "$previous"
    echo "current=$(current)"
}

status() {
    local names=""
    echo "root=$ROOT"
    echo "current=$(current)"
    while IFS= read -r v; do
        if [[ -z "$names" ]]; then
            names="$v"
        else
            names="$names,$v"
        fi
    done < <(list_versions)
    echo "releases=$names"
}

[[ $# -ge 1 ]] || usage
case "$1" in
    publish)
        [[ $# -eq 2 ]] || usage
        publish "$2"
        ;;
    rollback)
        rollback
        ;;
    status)
        status
        ;;
    *)
        usage
        ;;
esac
