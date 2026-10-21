"""Capture #433's missing UI evidence on the local c332 instance.

The ticket names four gaps — 390 width, the German UI, the VPS-KILL live
error, and VPS-DOWN after a reload. Three fault states cover them, each at
1440 and 390, in English and German, live and reloaded:

- `sse-cut`  - the campaign #332 cut proxy keeps the first complete block and
               drops `done`, then the real dock shows the failure.
- `vps-down` - Genie is stopped before the turn, so the proxy answers 502.
- `vps-kill` - Genie is killed three seconds into the turn
               (run_faults.KILL_AFTER_S), so the proxy answers 502 mid-turn.

Each state is captured at 1440 and 390, in English and German, live and after
a reload. The live shot only happens after the failure sentence is visible;
capture.mjs records what the page showed and what the turn route answered.

Everything stays on 127.0.0.1. The instance, the cut proxy and the Genie
process are this worktree's c332 (`just up c332`, `just pull load c332
latest`, `just serve c332`).

    uv run --locked --project docs/research/2026-10-20-campaign-332/harness \\
        python docs/acceptance/2026-10-21/433/capture.py [--states sse-cut] \\
        [--out DIR] [--no-ui-copy]

The images are written to this directory. The same files are copied to
`~/de-linker-data/campaign-332/ui/`, where the battery's earlier shots live,
unless `--no-ui-copy` is given. `matrix.json` is the index the README cites.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HARNESS = ROOT / "docs/research/2026-10-20-campaign-332/harness"


def _harness() -> tuple[Any, Any]:
    """Import the campaign harness without a top-level path-dependent import."""
    sys.path.insert(0, str(HARNESS))
    import stack as stack_module
    from faults import FaultServer as fault_server

    return stack_module, fault_server


stack, FaultServer = _harness()

MJS = HERE / "capture.mjs"
# run_faults.KILL_AFTER_S — after the turn has left the client, before the
# shortest chat-fault fallback (8.144s) and Proxy::TURN_BUDGET (60s).
KILL_AFTER_S = 3.0
UI_HOME = Path.home() / "de-linker-data/campaign-332/ui"
# Width, height, language, path. The German page is the Polylang /de/ page.
COMBOS = (
    (1440, 900, "en", "/"),
    (1440, 900, "de", "/de/"),
    (390, 844, "en", "/"),
    (390, 844, "de", "/de/"),
)
STATES = ("sse-cut", "vps-kill", "vps-down")


def node() -> str:
    found = shutil.which("node")
    if not found:
        raise RuntimeError("node is not on PATH")
    return found


def combo_name(width: int, lang: str) -> str:
    return f"{width}-{lang}"


def spawn(
    state: str,
    width: int,
    height: int,
    lang: str,
    path: str,
    out: Path,
    phase: Path,
    hook: bool,
    reload: bool,
    question_key: str = "stock",
) -> subprocess.Popen[str]:
    argv = [
        node(),
        str(MJS),
        "--wp",
        stack.WP,
        "--path",
        path,
        "--width",
        str(width),
        "--height",
        str(height),
        "--lang",
        lang,
        "--name",
        state,
        "--out",
        str(out),
        "--question-key",
        question_key,
        "--shots",
        "live,reload" if reload else "live",
    ]
    if hook:
        argv += ["--hook", str(phase / "hook")]
        argv += ["--live-done", str(phase / "live-done")]
        argv += ["--resume", str(phase / "resume")]
    elif reload:
        argv += ["--live-done", str(phase / "live-done")]
        argv += ["--resume", str(phase / "resume")]
    return subprocess.Popen(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for(path: Path, proc: subprocess.Popen[str], timeout: float) -> bool:
    """Wait for `path`, or stop early when the capture process exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return True
        if proc.poll() is not None:
            return path.is_file()
        time.sleep(0.1)
    return path.is_file()


def finish(proc: subprocess.Popen[str], timeout: float) -> tuple[int, str, str]:
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return 124, stdout, stderr + "\ncapture timed out"
    return (
        proc.returncode if proc.returncode is not None else 0,
        stdout,
        stderr,
    )


def phase_files(out: Path, state: str, width: int, lang: str) -> Path:
    phase = out / "runs" / f"{state}-{combo_name(width, lang)}"
    phase.mkdir(parents=True, exist_ok=True)
    for name in ("hook", "live-done", "resume"):
        phase.joinpath(name).unlink(missing_ok=True)
    return phase


def ensure_genie_down() -> None:
    """The harness's own stop path, with the assertion the capture needs."""
    stack.stop_genie()
    if stack.health():
        # A start that raced the previous combo's restart: stop it again.
        stack.stop_genie()
    if stack.health():
        raise RuntimeError(f"genie is still listening at {stack.GENIE}")


def record_of(out: Path, state: str, width: int, lang: str) -> dict[str, object]:
    path = out / "runs" / f"{state}-{width}-{lang}.json"
    if not path.is_file():
        return {"id": state, "width": width, "lang": lang, "error": "no run record"}
    return json.loads(path.read_text())


def sse_cut(out: Path, combos: tuple[tuple[int, int, str, str], ...]) -> None:
    proxy = FaultServer("cut", upstream=stack.GENIE, cut="cut")
    proxy.start()
    stack.set_genie_url(proxy.url)
    try:
        for width, height, lang, path in combos:
            phase = phase_files(out, "sse-cut", width, lang)
            proc = spawn("sse-cut", width, height, lang, path, out, phase, False, True)
            # No process is stopped for a cut; the reload can follow at once.
            phase.joinpath("resume").write_text("no wait\n")
            code, stdout, stderr = finish(proc, 180)
            print(f"sse-cut {width} {lang}: exit {code} {stdout.strip()}", flush=True)
            if stderr.strip():
                print(stderr.strip(), file=sys.stderr, flush=True)
            report = proxy.cut_report()
            print(f"  cut: {json.dumps(report)}", flush=True)
    finally:
        stack.set_genie_url(stack.GENIE)
        proxy.stop()


def vps_down(out: Path, combos: tuple[tuple[int, int, str, str], ...]) -> None:
    try:
        for width, height, lang, path in combos:
            ensure_genie_down()
            phase = phase_files(out, "vps-down", width, lang)
            proc = spawn("vps-down", width, height, lang, path, out, phase, False, True)
            if not wait_for(phase / "live-done", proc, 90):
                code, stdout, stderr = finish(proc, 30)
                print(
                    f"vps-down {width} {lang}: no live shot (exit {code})", flush=True
                )
                print(stderr.strip(), file=sys.stderr, flush=True)
                if not stack.health():
                    stack.start_genie()
                continue
            stack.start_genie()
            phase.joinpath("resume").write_text("healthy\n")
            code, stdout, stderr = finish(proc, 180)
            print(f"vps-down {width} {lang}: exit {code} {stdout.strip()}", flush=True)
            if stderr.strip():
                print(stderr.strip(), file=sys.stderr, flush=True)
    finally:
        if not stack.health():
            stack.start_genie()


def attach_attempts(
    out: Path,
    state: str,
    width: int,
    lang: str,
    attempts: list[dict[str, object]],
) -> None:
    """Write the VPS-KILL attempt history into the combo's final record."""
    path = out / "runs" / f"{state}-{width}-{lang}.json"
    if not path.is_file() or not attempts:
        return
    data = json.loads(path.read_text())
    data["attempts"] = attempts
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def vps_kill(out: Path, combos: tuple[tuple[int, int, str, str], ...]) -> None:
    # The turn must still be running when stack.stop_genie's SIGKILL lands
    # (8s after SIGTERM, run_faults.VPS-KILL measured 11.123s). The stock
    # question is code-made and finishes too fast; the document and
    # recommendation turns measured 12-21s here. More than one attempt is
    # kept because the model's own time varies.
    question_keys = ("doc", "model", "doc", "model")
    try:
        for width, height, lang, path in combos:
            attempts: list[dict[str, object]] = []
            for attempt, question_key in enumerate(question_keys, start=1):
                if not stack.health():
                    stack.start_genie()
                phase = phase_files(out, "vps-kill", width, lang)
                proc = spawn(
                    "vps-kill",
                    width,
                    height,
                    lang,
                    path,
                    out,
                    phase,
                    True,
                    True,
                    question_key=question_key,
                )
                if not wait_for(phase / "hook", proc, 60):
                    code, stdout, stderr = finish(proc, 30)
                    print(
                        f"vps-kill {width} {lang}: no turn request (exit {code})",
                        flush=True,
                    )
                    print(stderr.strip(), file=sys.stderr, flush=True)
                    attempts.append(
                        {
                            "attempt": attempt,
                            "question_key": question_key,
                            "outcome": "no turn request",
                        }
                    )
                    # A page that never sent a turn gets the next attempt.
                    continue
                time.sleep(KILL_AFTER_S)
                ensure_genie_down()
                if wait_for(phase / "live-done", proc, 90):
                    stack.start_genie()
                    phase.joinpath("resume").write_text("healthy\n")
                    code, stdout, stderr = finish(proc, 180)
                    print(
                        f"vps-kill {width} {lang}: exit {code} "
                        f"(attempt {attempt}, {question_key}) {stdout.strip()}",
                        flush=True,
                    )
                    if stderr.strip():
                        print(stderr.strip(), file=sys.stderr, flush=True)
                    attempts.append(
                        {
                            "attempt": attempt,
                            "question_key": question_key,
                            "outcome": "live failure captured",
                        }
                    )
                    break
                code, stdout, stderr = finish(proc, 15)
                print(
                    f"vps-kill {width} {lang}: attempt {attempt} ({question_key}) "
                    f"did not reach the kill state (exit {code})",
                    flush=True,
                )
                if stderr.strip():
                    print(stderr.strip(), file=sys.stderr, flush=True)
                attempts.append(
                    {
                        "attempt": attempt,
                        "question_key": question_key,
                        "outcome": "no live failure",
                    }
                )
                if not stack.health():
                    stack.start_genie()
            else:
                print(
                    f"vps-kill {width} {lang}: no attempt reached the kill state",
                    file=sys.stderr,
                    flush=True,
                )
            attach_attempts(out, "vps-kill", width, lang, attempts)
    finally:
        if not stack.health():
            stack.start_genie()


def report(
    out: Path,
    states: list[str],
    combos: tuple[tuple[int, int, str, str], ...],
    no_ui_copy: bool,
) -> int:
    """Write matrix.json and the ui copy, and fail if a record has an error."""
    # The phase directories only coordinate one combo (hook, live-done,
    # resume). The run records are the evidence; the coordinators are not.
    for phase in (out / "runs").glob("*/"):
        if phase.is_dir():
            shutil.rmtree(phase, ignore_errors=True)
    # A partial rerun replaces only its own rows; the other states stay in
    # matrix.json. A full rerun rewrites all twelve.
    matrix_path = out / "matrix.json"
    rows: dict[tuple[str, int, str], dict[str, object]] = {}
    if matrix_path.is_file():
        try:
            for row in json.loads(matrix_path.read_text()):
                rows[(str(row["id"]), int(row["width"]), str(row["lang"]))] = row
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            rows = {}
    for state in states:
        for width, _height, lang, _path in combos:
            rows[(state, width, lang)] = record_of(out, state, width, lang)
    matrix = [
        rows[(state, width, lang)]
        for state in STATES
        for width, _height, lang, _path in COMBOS
        if (state, width, lang) in rows
    ]
    matrix_path.write_text(json.dumps(matrix, indent=2) + "\n")
    print(f"matrix: {matrix_path}", flush=True)

    if not no_ui_copy:
        UI_HOME.mkdir(parents=True, exist_ok=True)
        copied = []
        for shot in sorted(out.glob("*-live-*.png")) + sorted(
            out.glob("*-reload-*.png")
        ):
            target = UI_HOME / shot.name
            shutil.copy2(shot, target)
            copied.append(str(target))
        print(f"ui: {len(copied)} images in {UI_HOME}", flush=True)

    failed = [row for row in matrix if row.get("error")]
    if failed:
        print(json.dumps({"failed": failed}, indent=2), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", default=",".join(STATES))
    parser.add_argument(
        "--combos",
        default=",".join(combo_name(width, lang) for width, _h, lang, _p in COMBOS),
    )
    parser.add_argument("--out", default=str(HERE))
    parser.add_argument("--no-ui-copy", action="store_true")
    parser.add_argument(
        "--matrix-only",
        action="store_true",
        help="Rebuild matrix.json and the ui copy from the run records; capture nothing.",
    )
    args = parser.parse_args(argv)
    states = [item.strip() for item in args.states.split(",") if item.strip()]
    unknown = [item for item in states if item not in STATES]
    if unknown:
        parser.error(f"unknown states: {', '.join(unknown)}")
    wanted = {item.strip() for item in args.combos.split(",") if item.strip()}
    combos = tuple(
        combo for combo in COMBOS if combo_name(combo[0], combo[2]) in wanted
    )
    if not combos:
        parser.error("no matching combos")
    if args.matrix_only:
        states = list(STATES)
        combos = COMBOS
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if args.matrix_only:
        return report(out, states, combos, args.no_ui_copy)
    if not stack.health():
        print(
            f"Genie is not healthy at {stack.GENIE}; run `just serve c332` first",
            file=sys.stderr,
        )
        return 2
    current = stack.wp("option", "get", "linker_genie_url").strip().splitlines()[-1]
    if current != stack.GENIE:
        print(
            f"linker_genie_url is {current}, not {stack.GENIE}; run `just serve c332`",
            file=sys.stderr,
        )
        return 2

    try:
        if "sse-cut" in states:
            sse_cut(out, combos)
        if "vps-kill" in states:
            vps_kill(out, combos)
        if "vps-down" in states:
            vps_down(out, combos)
    finally:
        stack.set_genie_url(stack.GENIE)
        if not stack.health():
            stack.start_genie()

    return report(out, states, combos, args.no_ui_copy)


if __name__ == "__main__":
    raise SystemExit(main())
