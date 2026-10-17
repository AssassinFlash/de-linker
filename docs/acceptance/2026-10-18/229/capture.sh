#!/usr/bin/env bash
# Same-browser, same-machine full-page EN/DE comparison for #229.
# Usage: bash docs/acceptance/2026-10-18/229/capture.sh <outdir> <c229-url>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../../.." && pwd)"
out="$1"
local_base="$2"
exec node "$repo/tests/visual/pixel-parity.mjs" "$out" https://de-linker.com "$local_base" \
    --widths 1280,1440,1920,390 --paths /,/de/ --allow-header /de/:1440,1920:89
