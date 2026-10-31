#!/usr/bin/env bash
# Source once per recipe so errors retain the command and its native exit code.
set -Eeuo pipefail
ci_phase_name=$1
ci_phase_started=$SECONDS
ci_phase_failed_command=
printf '== %s: started\n' "$ci_phase_name"
trap 'ci_phase_failed_command=$BASH_COMMAND' ERR
ci_phase_finish() {
    local status=$?
    if [ "$status" -eq 0 ]; then
        printf '== %s: passed (%ss)\n' "$ci_phase_name" "$((SECONDS - ci_phase_started))"
    else
        printf '== %s: failed (%ss, exit %s): %s\n' "$ci_phase_name" "$((SECONDS - ci_phase_started))" "$status" "$ci_phase_failed_command" >&2
    fi
    return "$status"
}
trap ci_phase_finish EXIT
