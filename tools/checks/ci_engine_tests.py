"""Run the complete Engine suite in two measured, bounded pytest groups."""

import signal
import sys

from ci_preflight import ROOT, Lane, _interrupted, run_parallel

GROUPS = (("standard", "not ci_expensive"), ("calculation", "ci_expensive"))
# Match the existing expanded calculation worker's BLAS/OpenMP limits. The
# local NumPy build uses macOS Accelerate, so bound that backend too.
THREAD_LIMITS = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
}


def run() -> int:
    lanes = [
        Lane(
            "engine-" + name,
            (sys.executable, "-m", "pytest", "-v", "--durations=10", "-m", expression),
            900,
            THREAD_LIMITS,
            cwd=ROOT / "services/engine",
            # The outer preflight gives this runner five seconds to exit.
            stop_grace_seconds=2,
        )
        for name, expression in GROUPS
    ]
    previous = signal.signal(signal.SIGTERM, _interrupted)
    try:
        return 0 if run_parallel(lanes, fail_fast=True) else 1
    except KeyboardInterrupt:
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(run())
