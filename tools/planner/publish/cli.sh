#!/usr/bin/env bash
# Publish the private planning HTTP/worker pair from one merged commit.
#
# docs/specs/548-service-hosting.md and ops/planner-worker.md describe this as a
# release window; the steps below are that window in order, with the facts the
# operator requires supplied rather than remembered:
#
#   * the source packer refuses a short SHA, so the revision is resolved here
#   * the candidate needs its own venv built in place before prepare accepts it
#   * runtime/worker policy and the two env files come from the release that is
#     running, because they are host policy and not part of the source
#   * every path inside those files names the old release, so they are rewritten
#
# Usage: cli.sh <full-git-revision> [--publication-url URL] [--dry-run]
#
# The candidate directory is the SHA-256 of the revision, which makes a repeated
# publish of the same commit reuse the same path instead of accumulating copies.

set -euo pipefail

REVISION=""
PUBLICATION_URL="https://de-linker.com/wp-json/linker/v1/publication/manifest"
DRY_RUN=0
HOST="linker-services"
ROOT="/opt/linker-planner"

while [ "$#" -gt 0 ]; do
	case "$1" in
	--publication-url)
		PUBLICATION_URL="$2"
		shift 2
		;;
	--dry-run)
		DRY_RUN=1
		shift
		;;
	-*)
		echo "unknown option: $1" >&2
		exit 2
		;;
	*)
		REVISION="$1"
		shift
		;;
	esac
done

if [ -z "$REVISION" ]; then
	echo "usage: $0 <full-git-revision> [--publication-url URL] [--dry-run]" >&2
	exit 2
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OPS="$REPO/services/engine/ops"

# The packer checks the exact object, so a short SHA is a refusal, not a guess.
if ! FULL="$(git -C "$REPO" rev-parse --verify "${REVISION}^{commit}" 2>/dev/null)"; then
	echo "not a commit in $REPO: $REVISION" >&2
	exit 1
fi

CANDIDATE="$(printf '%s' "$FULL" | shasum -a 256 | awk '{print $1}')"
TARGET="$ROOT/releases/$CANDIDATE"

echo "repository      $REPO"
echo "revision        $FULL"
echo "candidate       $TARGET"

CURRENT="$(ssh -o BatchMode=yes "$HOST" "cat $ROOT/selection.json 2>/dev/null" |
	python3 -c 'import json,sys; print(json.load(sys.stdin)["current"].rsplit("/.deploy",1)[0])' 2>/dev/null || true)"

if [ -z "$CURRENT" ] || ! ssh -o BatchMode=yes "$HOST" "test -d '$CURRENT'"; then
	echo "cannot read the running planner release from $ROOT/selection.json" >&2
	exit 1
fi
echo "running         $CURRENT"

if [ "$DRY_RUN" -eq 1 ]; then
	echo "dry run: nothing written"
	exit 0
fi

# 1. Pack the reviewed source closure and stream it into the new directory.
if ssh -o BatchMode=yes "$HOST" "test -d '$TARGET'"; then
	echo "candidate already exists; reusing it"
else
	echo "packing and streaming source"
	ssh -o BatchMode=yes "$HOST" "mkdir -p '$TARGET'"
	python3 "$OPS/planner_source.py" --repository "$REPO" --revision "$FULL" |
		ssh -o BatchMode=yes "$HOST" "tar -xf - -C '$TARGET'"
fi

# 2. Host policy comes from the running release; only the paths change.
echo "staging policy files from the running release"
ssh -o BatchMode=yes "$HOST" "C='$TARGET'; OLD='$CURRENT'
mkdir -p \"\$C/.deploy\"
for f in runtime.json worker.json http.env worker.env; do cp \"\$OLD/.deploy/\$f\" \"\$C/.deploy/\$f\"; done
python3 - \"\$C\" \"\$OLD\" <<'PY'
import json, pathlib, sys
new, old = sys.argv[1], sys.argv[2]
spec = json.load(open(old + '/.deploy/spec.json'))
spec['release'] = new
pathlib.Path(new + '/.deploy/spec.json').write_text(json.dumps(spec, indent=2) + '\n')
for name in ('http.env', 'worker.env'):
    path = pathlib.Path(new) / '.deploy' / name
    path.write_text(path.read_text().replace(old, new))
print('spec and env rewired to the new release')
PY
chown -R linker-planner:linker-planner \"\$C\"
chmod 600 \"\$C\".deploy/*.env 2>/dev/null || chmod 600 \"\$C/.deploy/\"*.env"

# 3. The candidate needs its own environment before prepare will accept it.
if ! ssh -o BatchMode=yes "$HOST" "test -x '$TARGET/.venv/bin/python'"; then
	echo "building the candidate environment"
	ssh -o BatchMode=yes "$HOST" "cd '$TARGET' && /root/.local/bin/uv sync --locked --no-dev --python 3.12 >/dev/null && chown -R linker-planner:linker-planner '$TARGET'"
fi

# 4. prepare, activate, then read the live identity back.
echo "prepare"
ssh -o BatchMode=yes "$HOST" "cd '$TARGET' && python3 ops/planner_release.py prepare .deploy/spec.json --source-environment '$TARGET/.deploy/http.env' --publication-url '$PUBLICATION_URL'" |
	tail -c 600

echo "activate"
ssh -o BatchMode=yes "$HOST" "cd '$TARGET' && python3 ops/planner_release.py activate .deploy/spec.json" | tail -c 600

echo "live"
ssh -o BatchMode=yes "$HOST" "systemctl show linker-planner-http -p ExecStart --value | head -1; systemctl is-active linker-planner-http linker-planner-worker"

echo "published $FULL"
