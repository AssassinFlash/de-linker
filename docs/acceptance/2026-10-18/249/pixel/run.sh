#!/usr/bin/env bash
# The #249 pixel gate: live vs local at rest, full page, 1440 and 390.
#   docs/acceptance/2026-10-18/249/pixel/run.sh <outdir> <local base>
# e.g. run.sh /tmp/pix http://127.0.0.1:9084 (`just status` for the address).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$1"
local_base="$2"
paths=(
	/
	/de/
	/product/saj-h2-10k-t3/
	/de/produkt/saj-h2-10k-t3/
	/product-category/inverters/
	/de/produkt-kategorie/wechselrichter/
	/solution/residential-storage/
	/de/loesung/heimspeicher/
)
for width in 1440 390; do
	node "$here/shoot.mjs" "$out/$width" "$width" https://de-linker.com=live "$local_base=local" -- "${paths[@]}"
	python3 "$here/pixdiff.py" "$out/$width"
done
