#!/usr/bin/env python3
"""Release the legacy Engine reader alone; prepare before selecting, never Genie.

The controller streams reviewed Git blobs in RAM. The stdlib-only host operator
owns one immutable final path, the existing selector, and the feed timer window.
"""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import http.client
import io
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SERVICE = "linker-engine.service"
WORKER = "linker-engine-feed-sync.service"
TIMER = "linker-engine-feed-sync.timer"
STATE = ".legacy-engine-release.json"
OWNED = ".legacy-engine-owners.json"
PREPARING = ".legacy-engine-preparing.json"
OWNER = ".reader-owner.json"
MANIFEST = ".git-source-manifest.json"
ROOTS = {
    "src",
    "schemas",
    "data",
    "ops",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
}
VERSION = re.compile(r"[0-9]{8}T[0-9]{12}Z(?:-[0-9a-f]{8,40})?")


def runtime_environment(values: dict[str, str]) -> dict[str, str]:
    """Apify belongs to assistant investigation, never automatic/runtime tools."""
    return {
        key: value
        for key, value in values.items()
        if not key.upper().startswith("APIFY_")
    }


class OperatorError(RuntimeError):
    def __init__(
        self, args: list[str], stderr: bytes, code: int | None, phase: str
    ) -> None:
        self.stderr = stderr  # private in-memory diagnostic; never printed verbatim
        text = stderr.decode(errors="replace")
        categories = [
            name
            for name, pattern in {
                "ssh_banner_timeout": "banner exchange",
                "connection_refused": "Connection refused",
                "permission_denied": "Permission denied",
                "module_missing": "ModuleNotFoundError",
                "syntax_error": "SyntaxError",
                "lock_mismatch": "lockfile needs to be updated",
            }.items()
            if pattern in text
        ]
        self.diagnostic: dict[str, Any] = {
            "phase": phase,
            "command": Path(args[0]).name,
            "exit_code": code,
            "categories": categories,
            "stderr_bytes": len(stderr),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "timeout": code is None,
        }
        if Path(args[0]).name == "systemctl" and args[-1] in {SERVICE, WORKER, TIMER}:
            self.diagnostic["unit"] = args[-1]
        frames = re.findall(
            r'File "[^"\n]*?([A-Za-z0-9_.-]+\.py|<string>)", line ([0-9]+)', text
        )
        if frames:
            self.diagnostic["location"] = frames[-1][0] + ":" + frames[-1][1]
        if Path(args[0]).name == "ssh":
            try:
                remote = json.loads(text)
                keys = {
                    "phase",
                    "error",
                    "command",
                    "exit_code",
                    "categories",
                    "stderr_bytes",
                    "stderr_sha256",
                    "reason",
                    "unit",
                    "location",
                    "timeout",
                }
                if isinstance(remote, dict) and set(remote).issubset(keys):
                    self.diagnostic["remote"] = remote
            except ValueError:
                pass
        super().__init__("bounded release operation failed")


def command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 30,
    phase: str = "release.command",
) -> bytes:
    if phase == "release.command" and Path(args[0]).name == "systemctl":
        phase = "systemd." + args[1]
    # Reap the whole owned group, including uv's interpreter, before cleanup.
    with subprocess.Popen(
        args,
        stdin=subprocess.PIPE if body is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=runtime_environment(dict(os.environ) if env is None else env),
        start_new_session=True,
    ) as child:
        try:
            output, stderr = child.communicate(body, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            _, stderr = child.communicate()
            raise OperatorError(args, stderr, None, phase) from None
        except BaseException:
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate()
            raise
        if child.returncode:
            raise OperatorError(args, stderr, child.returncode, phase)
        return output


def write(path: Path, value: Any) -> None:
    tmp = path.with_name(path.name + ".next")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def environment(path: Path) -> dict[str, str]:
    if path.stat().st_mode & 0o077:
        raise ValueError("service environment must be private")
    result = runtime_environment(dict(os.environ))
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, raw = line.removeprefix("export ").split("=", 1)
        if key.upper().startswith("APIFY_"):
            # systemd independently reads this file when starting the service.
            # Filtering only this probe would still leak the alias to runtime.
            raise ValueError(
                "investigation-only provider alias in runtime environment file"
            )
        if key in {"PYTHONPATH", "PYTHONHOME"}:
            raise ValueError(
                "service import override conflicts with immutable runtime binding"
            )
        value = shlex.split(raw)
        if not re.fullmatch("[A-Z][A-Z0-9_]*", key) or len(value) != 1:
            raise ValueError("invalid service environment entry")
        result[key] = value[0]
    if not result.get("GENIE_SERVICE_TOKEN"):
        raise ValueError("service token unavailable")
    return result


def release(root: Path, name: str) -> Path:
    if not VERSION.fullmatch(name):
        raise ValueError("invalid release name")
    path = root / name
    if path.is_symlink():
        raise ValueError("release may not be a symlink")
    return path


def selected(root: Path) -> str:
    link = root / "current"
    if not link.is_symlink():
        raise ValueError("existing runtime selector required")
    target = link.resolve(strict=True)
    if target.parent != root.resolve():
        raise ValueError("selector leaves runtime root")
    release(root, target.name)
    return target.name


def switch(root: Path, name: str) -> None:
    release(root, name)
    tmp = root / f".reader-current-{os.getpid()}"
    tmp.symlink_to(name)
    try:
        os.replace(tmp, root / "current")
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def locked(root: Path) -> Iterator[None]:
    with (root / ".legacy-engine.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def verify_source(path: Path, blobs: dict[str, str]) -> None:
    for name, oid in blobs.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe source path")
        source = path / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError("source file missing or linked")
        data = source.read_bytes()
        if (
            hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            != oid
        ):
            raise ValueError("runtime source differs from reviewed Git blobs")
    for name in ROOTS:
        tree = path / name
        if tree.is_symlink():
            raise ValueError("runtime input directory is linked")
        for source in tree.rglob("*") if tree.is_dir() else [tree]:
            if source.is_symlink():
                raise ValueError("runtime input is linked")
            if source.is_file() and str(source.relative_to(path)) not in blobs:
                if "__pycache__" in source.parts and source.suffix == ".pyc":
                    continue
                raise ValueError("untracked runtime input")


PROBE = """import json,os,hashlib,sys
from pathlib import Path
from linker_engine import version,geo
from linker_engine.products import Products
from linker_engine.compatibility import Compatibility
from linker_engine.publication import Publication
from linker_engine.engine import Engine
from linker_engine.pvgis import Pvgis
import linker_engine
root=Path(linker_engine.__file__).resolve().parents[2]
assert root==Path(sys.argv[1]).resolve(), 'candidate imports another runtime'
feed_path=Path(os.environ['LINKER_ENGINE_FEED']).resolve()
feed=feed_path.read_bytes();data=json.loads(feed)
compat_path=feed_path.parent/'compatibility.json' if (feed_path.parent/'manifest.json').exists() else Path(os.environ['LINKER_ENGINE_COMPATIBILITY'])
compat_file=compat_path.read_bytes()
if (feed_path.parent/'manifest.json').exists():
 m=json.loads((feed_path.parent/'manifest.json').read_text())
 assert m['feed_sha256']==hashlib.sha256(feed).hexdigest() and m['compatibility_sha256']==hashlib.sha256(compat_file).hexdigest()
compat=json.dumps(data['compatibility'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
products=Products.from_feed(data);contract=Compatibility(json.loads(compat))
engine=Engine(products=products,compatibility=contract,pvgis=Pvgis(Path(os.environ['LINKER_ENGINE_CACHE'])/'pvgis'))
prepared=Publication(data).prepared_products(engine)
place=geo.lookup('10115');assert place is not None
print(json.dumps({'import_root':str(root),'version':version.digest(version.source_bytes(root/'src/linker_engine'),feed,compat),
 'source_revision':data['source_revision'],'compatibility_revision':data['compatibility_revision'],
 'prepared_products':prepared,'feed_sha256':hashlib.sha256(feed).hexdigest(),
 'compatibility_sha256':hashlib.sha256(compat_file).hexdigest(),
 'geo':{'plz':place.plz,'latitude':place.latitude,'longitude':place.longitude,'state':place.state,'place':place.name}}))
"""


def probe(path: Path, env: dict[str, str]) -> dict[str, Any]:
    local = {**env, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    local.pop("PYTHONPATH", None)
    value: dict[str, Any] = json.loads(
        command(
            [str(path / ".venv/bin/python"), "-B", "-c", PROBE, str(path)],
            env=local,
            timeout=60,
            phase="prepare.native_reader_probe",
        )
    )
    return value


def get(port: int, path: str, env: dict[str, str]) -> dict[str, Any]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request(
            "GET", path, headers={"X-Linker-Service-Token": env["GENIE_SERVICE_TOKEN"]}
        )
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError("private Engine readback refused")
        value: dict[str, Any] = json.loads(response.read())
        return value
    finally:
        conn.close()


def timer_tick() -> int:
    """Read native D-Bus uint64; systemctl formats this property as a duration."""
    location = shlex.split(
        command(
            [
                "busctl",
                "call",
                "org.freedesktop.systemd1",
                "/org/freedesktop/systemd1",
                "org.freedesktop.systemd1.Manager",
                "GetUnit",
                "s",
                TIMER,
            ],
            phase="timer.raw_unit_path",
        ).decode()
    )
    if (
        len(location) != 2
        or location[0] != "o"
        or not location[1].startswith("/org/freedesktop/systemd1/unit/")
    ):
        raise ValueError("invalid native timer object path")
    raw = (
        command(
            [
                "busctl",
                "get-property",
                "org.freedesktop.systemd1",
                location[1],
                "org.freedesktop.systemd1.Timer",
                "LastTriggerUSecMonotonic",
            ],
            phase="timer.raw_monotonic_tick",
        )
        .decode()
        .split()
    )
    if len(raw) != 2 or raw[0] != "t" or not raw[1].isdigit() or int(raw[1]) >= 2**64:
        raise ValueError("timer did not return a native uint64")
    return int(raw[1])


def unit(name: str) -> dict[str, str]:
    raw = command(
        [
            "systemctl",
            "show",
            name,
            "--property=ActiveState,SubState,MainPID,ExecStart,UnitFileState,Unit,LastTriggerUSecMonotonic,ExecMainStatus,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,Result",
        ]
    )
    return dict(line.split("=", 1) for line in raw.decode().splitlines() if "=" in line)


def check_process(root: Path, name: str) -> dict[str, str]:
    state = unit(SERVICE)
    pid = int(state.get("MainPID", "0"))
    if (
        state.get("ActiveState") != "active"
        or state.get("SubState") != "running"
        or pid < 1
    ):
        raise RuntimeError("Engine process is not running")
    if Path(f"/proc/{pid}/cwd").resolve(strict=True) != release(root, name).resolve():
        raise RuntimeError("Engine process cwd differs from selected release")
    if str(root / "current/.venv/bin/python") not in state.get("ExecStart", ""):
        raise RuntimeError("Engine unit does not execute this selector")
    return {"pid": str(pid), "cwd": str(release(root, name))}


def readback(
    root: Path, name: str, expected: dict[str, Any], env: dict[str, str], port: int
) -> dict[str, Any]:
    if selected(root) != name:
        raise RuntimeError("runtime selector changed")
    actual = get(port, "/resource/version?ready=1", env)
    for key in ("version", "source_revision", "compatibility_revision"):
        if actual.get(key) != expected[key]:
            raise RuntimeError("actual Engine loaded receipt differs")
    rows = actual.get("prepared_products")
    if not isinstance(rows, list) or sorted(
        rows, key=lambda row: row["product_id"]
    ) != sorted(expected["prepared_products"], key=lambda row: row["product_id"]):
        raise RuntimeError("actual prepared product coverage differs")
    geo = get(port, "/geo/plz/10115", env)
    if any(geo.get(key) != value for key, value in expected["geo"].items()):
        raise RuntimeError("actual Engine geo data differs")
    return {
        "loaded": actual,
        "geo": expected["geo"],
        "process": check_process(root, name),
    }


def ready(
    root: Path, name: str, expected: dict[str, Any], env: dict[str, str], port: int
) -> dict[str, Any]:
    # The new Python process imports the scientific stack before binding 8901.
    deadline = time.monotonic() + 45
    while True:
        try:
            return readback(root, name, expected, env, port)
        # Uvicorn has not bound its loopback socket while imports run. Once a
        # process answers, any version/coverage/geo/auth conflict is definitive:
        # never repeat the Woo-backed ready computation for that mismatch.
        except ConnectionRefusedError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)


def restore_timer(before: dict[str, str]) -> None:
    # Do not rewrite enabled state or any installed unit/environment definition.
    command(
        [
            "systemctl",
            "start" if before.get("ActiveState") == "active" else "stop",
            TIMER,
        ]
    )
    if unit(TIMER).get("ActiveState") != before.get("ActiveState"):
        raise RuntimeError("original feed timer state was not restored")


def discard_preparation(
    root: Path, record: dict[str, Any], *, created_here: bool = False
) -> None:
    path = release(root, record["name"])
    state = json.loads((root / STATE).read_text()) if (root / STATE).exists() else {}
    if path.name in {state.get("current"), state.get("previous")}:
        raise RuntimeError("published current/previous runtime is protected")
    if selected(root) == path.name or referenced(path):
        raise RuntimeError("preparation is selected or referenced; cleanup refused")
    if path.exists():
        marker = path / OWNER
        if not created_here and (
            not marker.is_file() or json.loads(marker.read_text()) != record
        ):
            raise RuntimeError("preparation owner is unproven; preserve and inspect")
        if (path / ".venv").is_symlink():
            raise RuntimeError("linked candidate environment preserved")
        allowed = ROOTS | {".venv", MANIFEST, OWNER, ".reader-prepared.json"}
        if any(item.name not in allowed for item in path.iterdir()):
            raise RuntimeError(
                "unknown preparation data preserved; inspect before cleanup"
            )
        blobs = record.get("blobs", {})
        for top in ROOTS:
            tree = path / top
            if tree.is_symlink():
                raise RuntimeError("linked preparation input preserved")
            for item in tree.rglob("*") if tree.is_dir() else [tree]:
                if item.is_symlink():
                    raise RuntimeError("linked preparation input preserved")
                if not item.is_file():
                    continue
                relative = str(item.relative_to(path))
                if "__pycache__" in item.parts and item.suffix == ".pyc":
                    continue
                raw = item.read_bytes()
                actual = hashlib.sha1(
                    b"blob " + str(len(raw)).encode() + b"\0" + raw
                ).hexdigest()
                if blobs.get(relative) != actual:
                    raise RuntimeError("unknown or changed preparation input preserved")
        shutil.rmtree(path)
    metadata = root / (".reader-owner-" + record["owner"])
    if metadata.exists():
        if metadata.is_symlink() or referenced(metadata):
            raise RuntimeError("ownership metadata is linked or referenced")
        extra = [p for p in metadata.iterdir() if p.name != OWNER]
        marker = metadata / OWNER
        if extra or (marker.exists() and json.loads(marker.read_text()) != record):
            raise RuntimeError("ownership metadata differs; cleanup refused")
        shutil.rmtree(metadata)
    (root / PREPARING).unlink(missing_ok=True)
    if (root / OWNED).exists():
        owners = json.loads((root / OWNED).read_text())
        if owners.get("_candidate") == record["name"]:
            owners.pop("_candidate", None)
            owners.pop(record["name"], None)
            write(root / OWNED, owners)


def prepare(
    root: Path,
    name: str,
    expected: str,
    archive: bytes,
    env: dict[str, str],
    protected: dict[str, str] | None = None,
) -> dict[str, Any]:
    with locked(root):
        if name == expected or selected(root) != expected:
            raise RuntimeError("runtime changed or candidate is already selected")
        if (root / PREPARING).exists():
            interrupted = json.loads((root / PREPARING).read_text())
            discard_preparation(root, interrupted)
        owners = (
            json.loads((root / OWNED).read_text()) if (root / OWNED).exists() else {}
        )
        state = (
            json.loads((root / STATE).read_text()) if (root / STATE).exists() else {}
        )
        if name in {state.get("current"), state.get("previous")}:
            raise RuntimeError(
                "published current/previous runtime cannot be prepared again"
            )
        if name in {**owners.get("_protected", {}), **(protected or {})}:
            raise RuntimeError("protected interpreter cannot be prepared again")
        if release(root, name).exists() and referenced(release(root, name)):
            raise RuntimeError("referenced runtime cannot be prepared again")
        pending = owners.get("_candidate")
        if pending and pending not in {name, selected(root)}:
            raise RuntimeError(
                "one prepared candidate already exists; explicitly discard it before changing name"
            )
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            members = tar.getmembers()
            if len({item.name for item in members}) != len(members):
                raise ValueError("duplicate archive entries")
            for item in members:
                if (
                    not item.isfile()
                    or Path(item.name).is_absolute()
                    or ".." in Path(item.name).parts
                ):
                    raise ValueError("source archive contains unsafe entries")
            metadata = tar.extractfile(MANIFEST)
            if metadata is None:
                raise ValueError("missing Git source manifest")
            manifest = json.load(metadata)
            baseline = manifest["baseline"]
            verify_source(release(root, expected), baseline["blobs"])
            # Existing manually deployed readers have no manifest. Git content
            # proof establishes their baseline without editing the old source.
            old_manifest = release(root, expected) / MANIFEST
            if (
                old_manifest.exists()
                and json.loads(old_manifest.read_text())["revision"]
                != baseline["revision"]
            ):
                raise ValueError("prior runtime declaration differs from Git proof")
            if {item.name for item in members} != {MANIFEST, *manifest["blobs"]}:
                raise ValueError("archive inventory differs from reviewed source")
            path = release(root, name)
            if path.exists():
                if (path / ".venv").is_symlink():
                    raise RuntimeError(
                        "linked candidate environment cannot be prepared again"
                    )
                prior = json.loads((path / MANIFEST).read_text())
                if prior != manifest:
                    raise ValueError("candidate belongs to another preparation")
                verify_source(path, manifest["blobs"])
                record = json.loads((path / OWNER).read_text())
            else:
                record = {
                    "name": name,
                    "revision": manifest["revision"],
                    "owner": secrets.token_hex(16),
                    "blobs": manifest["blobs"],
                }
            write(root / PREPARING, record)
            created = False
            try:
                if not path.exists():
                    # An empty owned metadata directory is renamed before any
                    # source/build input is written. A final path always has
                    # its owner even if the process is killed before unpack.
                    metadata_dir = root / (".reader-owner-" + record["owner"])
                    metadata_dir.mkdir(mode=0o700)
                    write(metadata_dir / OWNER, record)
                    os.rename(metadata_dir, path)
                    created = True
                    for item in members:
                        file = path / item.name
                        file.parent.mkdir(parents=True, exist_ok=True)
                        handle = tar.extractfile(item)
                        if handle is None:
                            raise ValueError("source archive entry missing")
                        file.write_bytes(handle.read())
                        file.chmod(0o444)
                verify_source(path, manifest["blobs"])
                command(
                    [
                        "/root/.local/bin/uv",
                        "sync",
                        "--locked",
                        "--no-dev",
                        "--project",
                        str(path),
                    ],
                    timeout=240,
                    phase="prepare.locked_environment",
                )
                receipt = probe(path, env)
                write(path / ".reader-prepared.json", receipt)
                owners = (
                    json.loads((root / OWNED).read_text())
                    if (root / OWNED).exists()
                    else {}
                )
                owners[expected] = baseline
                owners[name] = {
                    "revision": manifest["revision"],
                    "blobs": manifest["blobs"],
                }
                owners["_candidate"] = name
                owners["_protected"] = {
                    **owners.get("_protected", {}),
                    **(protected or {}),
                }
                write(root / OWNED, owners)
                (root / PREPARING).unlink()
                return {
                    "prepared": name,
                    "revision": manifest["revision"],
                    "files": len(manifest["blobs"]),
                    **receipt,
                }
            except BaseException:
                discard_preparation(root, record, created_here=created)
                raise


def activate(
    root: Path, name: str, expected: str, env: dict[str, str], port: int
) -> dict[str, Any]:
    with locked(root):
        if selected(root) != expected:
            raise RuntimeError(
                "runtime changed before activation; inspect, never replay"
            )
        path = release(root, name)
        owners = json.loads((root / OWNED).read_text())
        verify_source(path, owners[name]["blobs"])
        verify_source(release(root, expected), owners[expected]["blobs"])
        timer = unit(TIMER)
        if str(root / "current/.venv/bin/python") not in unit(SERVICE).get(
            "ExecStart", ""
        ):
            raise RuntimeError("Engine service is not selector-bound")
        if (
            str(root / "ops/sync-feed.py") not in unit(WORKER).get("ExecStart", "")
            or timer.get("Unit") != WORKER
        ):
            raise RuntimeError("feed timer/worker is not bound to this Engine")
        worker = root / "ops/sync-feed.py"
        binding = next(
            (
                n.value
                for n in ast.parse(worker.read_text()).body
                if isinstance(n, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "PROBE_PYTHON"
                    for t in n.targets
                )
            ),
            None,
        )
        if not isinstance(binding, ast.Constant) or binding.value != str(
            root / "current/.venv/bin/python"
        ):
            raise RuntimeError("stable feed worker validator is not selector-bound")
        state: dict[str, Any] = {
            "current": name,
            "previous": expected,
            "phase": "quiescing",
            "timer": timer,
            "timer_baseline": timer_tick(),
            "worker_verified": False,
        }
        write(root / STATE, state)
        try:
            command(["systemctl", "stop", TIMER])
            deadline = time.monotonic() + 90
            while unit(WORKER).get("ActiveState") in {
                "active",
                "activating",
                "deactivating",
            }:
                if time.monotonic() >= deadline:
                    raise RuntimeError("feed worker did not become idle")
                time.sleep(0.5)
            with (root / "state/.publication-sync.lock").open("a") as feed_lock:
                fcntl.flock(feed_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                before = probe(release(root, expected), env)
                readback(root, expected, before, env, port)
                after = probe(path, env)
                prepared = json.loads((path / ".reader-prepared.json").read_text())
                if after != prepared:
                    raise RuntimeError(
                        "feed, coverage or geo changed after preparation"
                    )
                state.update(phase="switching", before=before, after=after)
                write(root / STATE, state)
                owners.pop("_candidate", None)
                write(root / OWNED, owners)
                command(["systemctl", "stop", SERVICE])
                switch(root, name)
                command(["systemctl", "start", SERVICE])
                result = ready(root, name, after, env, port)
                state["phase"] = "ready"
                write(root / STATE, state)
        except BaseException:
            if state.get("phase") in {"switching", "ready"}:
                # This is the same owned, locked transaction, not an ambiguous
                # client replay. Inspecting later uses status/verify/rollback.
                if selected(root) not in {name, expected}:
                    raise RuntimeError("foreign selector; recovery refused") from None
                command(["systemctl", "stop", SERVICE])
                switch(root, expected)
                command(["systemctl", "start", SERVICE])
                ready(root, expected, state["before"], env, port)
                state.update(phase="restored", current=expected, previous=name)
                write(root / STATE, state)
            raise
        finally:
            restore_timer(timer)
        return {
            "current": name,
            "previous": expected,
            "phase": "ready",
            "worker_verified": False,
            **result,
        }


def verify(
    root: Path, env: dict[str, str], port: int, wait: float = 0
) -> dict[str, Any]:
    with locked(root):
        state = json.loads((root / STATE).read_text())
        name = selected(root)
        if state["current"] != name or state["phase"] not in {"switching", "ready"}:
            raise RuntimeError("inspect/recovery required")
        owners = json.loads((root / OWNED).read_text())
        verify_source(release(root, name), owners[name]["blobs"])
        expected = probe(release(root, name), env)
        result = ready(root, name, expected, env, port)
        if unit(TIMER).get("ActiveState") != state["timer"].get("ActiveState"):
            restore_timer(state["timer"])
        if owners.get("_candidate") in {state["current"], state["previous"]}:
            owners.pop("_candidate", None)
            write(root / OWNED, owners)
        if state["phase"] == "switching":
            state["phase"] = "ready"
            write(root / STATE, state)
        if wait:
            if state["timer"].get("ActiveState") != "active":
                raise ValueError(
                    "original timer was inactive; cannot prove an interval"
                )
            deadline = time.monotonic() + wait
            while True:
                worker = unit(WORKER)
                trigger = timer_tick()
                if trigger > int(state["timer_baseline"] or "0") and worker.get(
                    "ActiveState"
                ) not in {
                    "active",
                    "activating",
                    "deactivating",
                }:
                    if (
                        int(worker.get("ExecMainStartTimestampMonotonic", "0") or "0")
                        < trigger
                        or int(worker.get("ExecMainExitTimestampMonotonic", "0") or "0")
                        < trigger
                    ):
                        if time.monotonic() >= deadline:
                            raise RuntimeError(
                                "no completed natural worker interval observed"
                            )
                        time.sleep(1)
                        continue
                    if (
                        worker.get("ExecMainStatus") != "0"
                        or worker.get("Result") != "success"
                    ):
                        raise RuntimeError("natural feed worker failed")
                    result = ready(
                        root, name, probe(release(root, name), env), env, port
                    )
                    state["worker_verified"] = True
                    write(root / STATE, state)
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("no successful natural worker interval observed")
                time.sleep(1)
        return {
            "current": name,
            "previous": state["previous"],
            "worker_verified": state["worker_verified"],
            **result,
        }


def rollback(
    root: Path, expected: str, env: dict[str, str], port: int
) -> dict[str, Any]:
    with locked(root):
        state = json.loads((root / STATE).read_text())
        old = state["previous"]
        intended = state["current"]
        physical = selected(root)
        interrupted_before_switch = physical == old and state["phase"] in {
            "quiescing",
            "switching",
        }
        if physical != expected or (
            expected != state["current"] and not interrupted_before_switch
        ):
            raise RuntimeError("rollback selector changed")
        owners = json.loads((root / OWNED).read_text())
        verify_source(release(root, old), owners[old]["blobs"])
        verify_source(release(root, expected), owners[expected]["blobs"])
        command(["systemctl", "stop", TIMER])
        try:
            if unit(WORKER).get("ActiveState") in {
                "active",
                "activating",
                "deactivating",
            }:
                raise RuntimeError("feed worker busy; rollback refused")
            with (root / "state/.publication-sync.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                baseline = probe(release(root, old), env)
                if "before" in state and baseline != state["before"]:
                    raise RuntimeError(
                        "rollback feed/coverage changed; restore a compatible data generation first"
                    )
                command(["systemctl", "stop", SERVICE])
                switch(root, old)
                command(["systemctl", "start", SERVICE])
                result = ready(root, old, baseline, env, port)
                state.update(
                    phase="restored",
                    current=old,
                    previous=expected if expected != old else intended,
                )
                write(root / STATE, state)
                if owners.get("_candidate") in {state["current"], state["previous"]}:
                    owners.pop("_candidate", None)
                    write(root / OWNED, owners)
        except BaseException:
            if selected(root) == old and expected != old:
                # Failed rollback is also a transaction: retain the current
                # reader if the verified prior binary cannot be restarted.
                command(["systemctl", "stop", SERVICE])
                switch(root, expected)
                command(["systemctl", "start", SERVICE])
                ready(root, expected, probe(release(root, expected), env), env, port)
                state["phase"] = "ready"
                write(root / STATE, state)
            raise
        finally:
            restore_timer(state["timer"])
        return {"current": old, "restored": True, **result}


def referenced(path: Path) -> bool:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            arguments = (proc / "cmdline").read_bytes().split(b"\0")
            prefix = os.fsencode(path)
            if any(arg == prefix or arg.startswith(prefix + b"/") for arg in arguments):
                return True
        except OSError:
            pass
        try:
            for line in (proc / "maps").read_bytes().splitlines():
                fields = line.split(maxsplit=5)
                if len(fields) != 6:
                    continue
                raw = fields[5].removesuffix(b" (deleted)")
                raw = re.sub(
                    rb"\\([0-7]{3})", lambda match: bytes([int(match[1], 8)]), raw
                )
                mapped = Path(os.fsdecode(raw))
                if mapped == path or path in mapped.parents:
                    return True
        except OSError:
            pass
        for link in [proc / "cwd", proc / "exe", *list((proc / "fd").glob("*"))]:
            try:
                value = link.resolve(strict=True)
                if value == path or path in value.parents:
                    return True
            except (OSError, RuntimeError):
                pass
    return False


def discard(root: Path, name: str, revision: str) -> dict[str, Any]:
    """Retire the one exact unselected candidate, never a published fallback."""
    with locked(root):
        owners = json.loads((root / OWNED).read_text())
        state = (
            json.loads((root / STATE).read_text()) if (root / STATE).exists() else {}
        )
        if name in {state.get("current"), state.get("previous")}:
            raise RuntimeError("published current/previous runtime is protected")
        if (
            owners.get("_candidate") != name
            or owners.get(name, {}).get("revision") != revision
        ):
            raise ValueError("discard does not name the exact owned candidate")
        if name in owners.get("_protected", {}):
            raise RuntimeError("candidate has an explicit interpreter dependency")
        path = release(root, name)
        if selected(root) == name:
            raise RuntimeError("cannot discard selected runtime")
        if (root / PREPARING).exists():
            journal = json.loads((root / PREPARING).read_text())
            if journal.get("name") != name:
                raise RuntimeError("another preparation owns the recovery journal")
        if path.exists():
            verify_source(path, owners[name]["blobs"])
            record = json.loads((path / OWNER).read_text())
            if record.get("revision") != revision or record.get("name") != name:
                raise RuntimeError("candidate ownership differs")
            allowed = ROOTS | {".venv", MANIFEST, OWNER, ".reader-prepared.json"}
            if any(item.name not in allowed for item in path.iterdir()):
                raise RuntimeError("unknown candidate data preserved")
            discard_preparation(root, record)
        else:
            owners.pop(name)
            owners.pop("_candidate")
            write(root / OWNED, owners)
        return {"discarded": name, "current": selected(root)}


def prune(root: Path, protected: dict[str, str]) -> dict[str, Any]:
    with locked(root):
        state = json.loads((root / STATE).read_text())
        owners = json.loads((root / OWNED).read_text())
        if (
            selected(root) != state["current"]
            or state["phase"] != "ready"
            or not state["worker_verified"]
        ):
            raise RuntimeError(
                "prune requires verified current and real natural worker"
            )
        protected = {**owners.get("_protected", {}), **protected}
        keep = {
            state["current"],
            state["previous"],
            owners.get("_candidate"),
            *protected,
        }
        removed = []
        unknown = []
        for path in root.iterdir():
            if not VERSION.fullmatch(path.name) or path.name in keep:
                continue
            if path.name not in owners or path.is_symlink():
                unknown.append(path.name)
                continue
            if referenced(path):
                raise RuntimeError("retired runtime still has process references")
            verify_source(path, owners[path.name]["blobs"])
            allowed = ROOTS | {".venv", MANIFEST, OWNER, ".reader-prepared.json"}
            if any(entry.name not in allowed for entry in path.iterdir()):
                raise RuntimeError("unknown release data preserved; retirement refused")
            shutil.rmtree(path)
            removed.append(path.name)
            del owners[path.name]
        write(root / OWNED, owners)
        return {
            "current": state["current"],
            "previous": state["previous"],
            "protected": protected,
            "retired": removed,
            "unknown_preserved": unknown,
        }


def git_blobs(repository: Path, revision: str) -> dict[str, str]:
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("exact reviewed commit required")
    result = {}
    for record in command(
        [
            "git",
            "-C",
            str(repository),
            "ls-tree",
            "-rz",
            revision,
            "--",
            "services/engine",
        ]
    ).split(b"\0"):
        if not record:
            continue
        header, raw = record.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        name = raw.decode().removeprefix("services/engine/")
        if Path(name).parts[0] not in ROOTS:
            continue
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("linked runtime source is forbidden")
        result[name] = oid
    if not {"data/plz_de.csv.gz", "pyproject.toml", "uv.lock"}.issubset(result):
        raise ValueError("incomplete legacy runtime including geo data")
    return result


def archive(repository: Path, revision: str, previous_revision: str) -> bytes:
    blobs = git_blobs(repository, revision)
    prior = git_blobs(repository, previous_revision)
    operator = command(
        [
            "git",
            "-C",
            str(repository),
            "show",
            revision + ":services/engine/ops/legacy_release.py",
        ]
    )
    if operator != Path(__file__).read_bytes():
        raise ValueError("operator is not the reviewed Git entrypoint")
    manifest = {
        "revision": revision,
        "blobs": blobs,
        "baseline": {"revision": previous_revision, "blobs": prior},
    }
    batch = command(
        ["git", "-C", str(repository), "cat-file", "--batch"],
        body="".join(oid + "\n" for oid in blobs.values()).encode(),
        phase="prepare.git_blob_batch",
    )
    offset = 0
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, oid in blobs.items():
            end = batch.index(b"\n", offset)
            header = batch[offset:end].decode().split()
            if header[:2] != [oid, "blob"]:
                raise ValueError("Git batch returned a different source object")
            size = int(header[2])
            data = batch[end + 1 : end + 1 + size]
            offset = end + size + 2
            if (
                hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest()
                != oid
            ):
                raise ValueError("Git batch source checksum mismatch")
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o444
            tar.addfile(item, io.BytesIO(data))
        if offset != len(batch):
            raise ValueError("unexpected trailing Git batch output")
        data = json.dumps(manifest).encode()
        item = tarfile.TarInfo(MANIFEST)
        item.size = len(data)
        tar.addfile(item, io.BytesIO(data))
    return output.getvalue()


def status(root: Path, env: dict[str, str], port: int) -> dict[str, Any]:
    name = selected(root)
    path = release(root, name)
    owners = json.loads((root / OWNED).read_text()) if (root / OWNED).exists() else {}
    proof = owners.get(name)
    if proof:
        verify_source(path, proof["blobs"])
    data = []
    for file in sorted((path / "data").rglob("*")):
        if file.is_file():
            raw = file.read_bytes()
            data.append(
                {
                    "path": str(file),
                    "git_blob": (proof or {})
                    .get("blobs", {})
                    .get(str(file.relative_to(path))),
                    "actual_blob": hashlib.sha1(
                        b"blob " + str(len(raw)).encode() + b"\0" + raw
                    ).hexdigest(),
                }
            )
    result: dict[str, Any] = {
        "selected": name,
        "state": json.loads((root / STATE).read_text())
        if (root / STATE).exists()
        else None,
        "source": {
            "path": str(path),
            "revision": (proof or {}).get("revision"),
            "git_verified": bool(proof),
            "data": data,
        },
        "service": {
            key: value for key, value in unit(SERVICE).items() if key != "ExecStart"
        },
        "timer": {
            key: value for key, value in unit(TIMER).items() if key != "ExecStart"
        },
        "worker": {
            key: value for key, value in unit(WORKER).items() if key != "ExecStart"
        },
    }
    try:
        result["actual"] = get(port, "/resource/version?ready=1", env)
        result["process"] = check_process(root, name)
        result["actual_available"] = True
    except (OSError, RuntimeError, http.client.HTTPException) as error:
        result["actual_available"] = False
        result["actual_error"] = type(error).__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=[
            "prepare",
            "activate",
            "verify",
            "rollback",
            "prune",
            "discard",
            "status",
        ],
    )
    parser.add_argument("--host")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--root", type=Path, default=Path("/opt/linker-engine"))
    parser.add_argument("--env-file", type=Path, default=Path("/etc/linker-engine.env"))
    parser.add_argument("--name")
    parser.add_argument("--expected-current")
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--previous-revision")
    parser.add_argument("--port", type=int, default=8901)
    parser.add_argument("--wait-worker-seconds", type=float, default=0)
    parser.add_argument(
        "--protect",
        action="append",
        default=[],
        help="exact-version=owned-interpreter-dependency-reason",
    )
    args = parser.parse_args()
    if args.operation in {"prepare", "activate"} and (
        not args.name or not args.expected_current
    ):
        parser.error("prepare/activate require --name and --expected-current")
    if args.operation == "rollback" and not args.expected_current:
        parser.error("rollback requires the freshly inspected --expected-current")
    if args.operation == "discard" and (not args.name or not args.revision):
        parser.error("discard requires exact --name and --revision")
    if (
        args.host
        and args.operation == "prepare"
        and (not args.repository or not args.revision or not args.previous_revision)
    ):
        parser.error(
            "prepare requires --repository, --revision and --previous-revision"
        )
    protected = dict(pair.split("=", 1) for pair in args.protect)
    if any(
        not VERSION.fullmatch(name) or not reason.strip()
        for name, reason in protected.items()
    ):
        parser.error(
            "protected interpreter needs an exact version and ownership reason"
        )
    if args.name in protected:
        parser.error("a new candidate cannot be an existing protected interpreter")
    if (
        args.wait_worker_seconds < 0
        or args.wait_worker_seconds == float("inf")
        or args.wait_worker_seconds != args.wait_worker_seconds
    ):
        parser.error("worker wait must be finite and nonnegative")
    if not 0 < args.port < 65536:
        parser.error("invalid private loopback port")
    if args.host:
        forwarded = [a for a in sys.argv[1:]]
        i = forwarded.index("--host")
        del forwarded[i : i + 2]
        for flag in (
            ("--repository", "--revision", "--previous-revision")
            if args.operation == "prepare"
            else ("--repository", "--previous-revision")
        ):
            if flag in forwarded:
                i = forwarded.index(flag)
                del forwarded[i : i + 2]
        body = (
            archive(args.repository, args.revision, args.previous_revision)
            if args.operation == "prepare"
            else None
        )
        remote_output = command(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "--",
                args.host,
                "python3 -c "
                + shlex.quote(Path(__file__).read_text())
                + " "
                + shlex.join([*forwarded, "--remote"]),
            ],
            body=body,
            timeout=480,
        )
        print(remote_output.decode().strip())
        return 0
    if not args.remote:
        parser.error(
            "use --host for the deployment host; direct host execution requires --remote"
        )
    root = args.root
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("existing real runtime root required")
    env = environment(args.env_file)
    env.setdefault("LINKER_ENGINE_CACHE", str(root / "state/cache"))
    if args.operation == "prepare":
        result = prepare(
            root,
            args.name,
            args.expected_current,
            sys.stdin.buffer.read(),
            env,
            dict(pair.split("=", 1) for pair in args.protect),
        )
    elif args.operation == "activate":
        result = activate(root, args.name, args.expected_current, env, args.port)
    elif args.operation == "verify":
        result = verify(root, env, args.port, args.wait_worker_seconds)
    elif args.operation == "rollback":
        result = rollback(root, args.expected_current, env, args.port)
    elif args.operation == "prune":
        result = prune(root, dict(pair.split("=", 1) for pair in args.protect))
    elif args.operation == "discard":
        result = discard(root, args.name, args.revision)
    else:
        result = status(root, env, args.port)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    **(
                        error.diagnostic
                        if isinstance(error, OperatorError)
                        else {
                            "phase": sys.argv[1] if len(sys.argv) > 1 else "arguments",
                            "reason": str(error)
                            if type(error) in {RuntimeError, ValueError}
                            else type(error).__name__,
                        }
                    ),
                    "error": type(error).__name__,
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
