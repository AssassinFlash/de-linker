"""Run the complete Engine suite in two measured, bounded pytest groups."""

import os
import signal
import subprocess
import sys
import threading
import time

GROUPS = (("standard", "not ci_expensive"), ("calculation", "ci_expensive"))


def run() -> int:
    processes = []
    readers = []

    def interrupted(signum, _frame):
        raise InterruptedError(f"signal {signum}")

    def stop():
        stopping = []
        for _, process in processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    stopping.append(process)
                except ProcessLookupError:
                    pass
        # The parent preflight grants five seconds before killing this runner.
        # Share one shorter deadline across both groups so it can reap them.
        deadline = time.monotonic() + 2
        for process in stopping:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
            # A terminated group leader may have left a child holding its pipe.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()

    previous = {
        sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        for name, expression in GROUPS:
            print(f"== engine {name}: started", flush=True)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "--durations=10",
                    "-m",
                    expression,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            processes.append((name, process))

            def stream(label, child):
                assert child.stdout is not None
                for line in child.stdout:
                    print(f"[{label}] {line}", end="", flush=True)

            reader = threading.Thread(target=stream, args=(name, process))
            reader.start()
            readers.append(reader)
        reported = set()
        while len(reported) < len(processes):
            for name, process in processes:
                status = process.poll()
                if status is None or name in reported:
                    continue
                reported.add(name)
                print(f"== engine {name}: exit {status}", flush=True)
                if status:
                    return status if status > 0 else 1
            time.sleep(0.1)
        return 0
    except InterruptedError as error:
        print(f"engine tests interrupted: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop()
        for reader in readers:
            reader.join()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(run())
