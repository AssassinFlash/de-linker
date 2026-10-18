#!/bin/sh
# Public WP-CLI test seam for the ticket's isolated instance.
set -eu
task_repo=$(CDPATH= cd "$(dirname "$0")/../../../.." && pwd)
cd "$task_repo"
exec env PHP="${PHP:-/opt/homebrew/opt/php@8.3/bin/php}" "$task_repo/tools/local/.venv/bin/linker-local" wp c254 "$@"
