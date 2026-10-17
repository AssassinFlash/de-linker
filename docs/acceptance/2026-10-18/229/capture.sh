#!/usr/bin/env bash
# Same-browser, same-machine full-page EN/DE comparison for #229.
# Usage: bash docs/acceptance/2026-10-18/229/capture.sh <outdir> <c229-url>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../../.." && pwd)"
out="$1"
local_base="$2"
for width in 1280 1440 1920 390; do
    node "$repo/docs/acceptance/2026-10-18/249/pixel/shoot.mjs" \
        "$out" "$width" https://de-linker.com=live "$local_base=local" -- / /de/
done
python3 "$here/pixels.py" "$out"
