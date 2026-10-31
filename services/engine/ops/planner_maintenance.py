"""One bounded Mac invocation of the existing Planner backup/retention contracts.

No daemon, network retry loop or alternative collector. Outside the UTC window,
or after this day's attempt, even SSH is skipped. The installed native operator
owns admission, stopped writers, final mark/sweep and paired recovery.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import syslog
import tarfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from linker_engine.planning import archive
from linker_engine.planning.retention import independent_snapshot
from linker_engine.planning.storage import Blobs

# The existing native lock, verifier and maintenance entry run from the selected
# executable. Request data is stdin-only; service credentials never leave it.
REMOTE = r"""
import fcntl, hashlib, inspect, json, os, pathlib, pwd, re, runpy, shutil, signal, sqlite3, struct, sys
def interrupted(*args): raise KeyboardInterrupt()
signal.signal(signal.SIGHUP, interrupted); signal.signal(signal.SIGTERM, interrupted)
p=json.loads(sys.stdin.buffer.readline()); root=pathlib.Path(p['root'])
def expired(*args): raise TimeoutError('maintenance_budget_expired')
signal.signal(signal.SIGALRM,expired)
# The native mutator already bounds its command groups and owns finally.
# A second alarm must never interrupt that recovery. The caller reserves
# additional time derived from these existing process budgets for apply/cleanup.
if p['action']!='apply': signal.alarm(max(1,int(p['budget'])))
selected=json.loads((root/'selection.json').read_text())['current']
if p.get('selected') and selected!=p['selected']: raise RuntimeError('selection_changed')
m=runpy.run_path(str(pathlib.Path(selected).parents[1]/'ops/planner_release.py'))
r=m['Release'](pathlib.Path(selected)); assert r.root==root
if 'when_idle' not in inspect.signature(m['maintain']).parameters: raise RuntimeError('maintenance_operator_upgrade_required')
source=pathlib.Path(r.runtime['directory']); recovery=root/'state'/('retention-recovery-'+p['owner'][:8])
sys.path[:0]=[str(r.path/'src'),str(r.path/'ops')]
from linker_engine.planning.dependencies import cas_lock
from linker_engine.planning.canonical import encode
from linker_engine.planning.retention import independent_snapshot
from planner_maintenance import recovery_marker, recovery_owner_file, remove_recovery
def marker():
    return recovery_marker(recovery,p['owner'],pwd.getpwnam(r.spec['user']).pw_uid)
def ready():
    identity=r.probe()
    if not r.ready(identity): raise RuntimeError('pair_not_ready')
    return identity
def service_uid():
    account=pwd.getpwnam(r.spec['user']); os.setgroups([]); os.setgid(account.pw_gid); os.setuid(account.pw_uid)
action=p['action']
if action=='plan':
    identity=ready(); control=r.operator('control','status')
    result={'selected':selected,'runtime':identity['runtime_sha256'],'recovery':marker(),
            'recovery_seconds':12*r.spec['start_seconds']+r.spec['stop_seconds']+r.policy['drain_timeout_seconds']+10}
    if control['draining'] or control['pending']: result.update(status='busy')
    else: result.update(status='idle',plan=r.operator('retention'))
elif action=='snapshot':
    ready(); control=r.operator('control','status')
    if control['draining'] or control['pending']: raise RuntimeError('busy_before_snapshot')
    service_uid()
    with cas_lock(source/'blobs',exclusive=False):
        c=sqlite3.connect((source/'workspace.sqlite').as_uri()+'?mode=ro',uri=True); target=sqlite3.connect(':memory:')
        try: c.backup(target); database=target.serialize()
        finally: target.close(); c.close()
        sizes={}
        for prefix in sorted((source/'blobs').iterdir()):
            if re.fullmatch('[a-f0-9]{2}',prefix.name):
                assert prefix.is_dir() and prefix.resolve()==prefix
                for item in sorted(prefix.iterdir()):
                    if re.fullmatch('[a-f0-9]{64}',item.name):
                        assert item.is_file() and item.resolve()==item and item.name[:2]==prefix.name
                        sizes[item.name]=item.stat().st_size
        manifest=encode({'schema':1,'database_sha256':hashlib.sha256(database).hexdigest(),'blobs':sorted(sizes)})
        missing=sorted(set(sizes)-set(p['known']))
        header=json.dumps({'database_bytes':len(database),'manifest_bytes':len(manifest),'sizes':sizes,'missing':missing}).encode()
        out=sys.stdout.buffer; out.write(struct.pack('>I',len(header))+header+database+manifest)
        for sha in missing:
            with (source/'blobs'/sha[:2]/sha).open('rb') as f:
                shutil.copyfileobj(f,out,1024*1024)
        out.flush()
        if sys.stdin.buffer.readline()!=b'verified\n': raise RuntimeError('snapshot_not_acknowledged')
        out.write(b'ACKED\n'); out.flush()
    sys.exit(0)
elif action=='stage':
    with m['locked'](root):
      if marker() is not None: raise RuntimeError('previous_recovery_requires_cleanup')
      service_uid(); created=False; owned=False; owner_file=recovery_owner_file(recovery,p['owner'])
      try:
        with cas_lock(source/'blobs',exclusive=False):
            note={'owner':p['owner'],'database_sha256':p['database_sha256'],'manifest_sha256':p['manifest_sha256']}
            # Publish ownership before any directory/data; a partial marker
            # with no directory is reconstructable and never grants tree deletion.
            with owner_file.open('x') as f:
                owned=True; os.chmod(owner_file,0o600); f.write(json.dumps(note)); f.flush(); os.fsync(f.fileno())
            recovery.mkdir(mode=0o700); created=True
            seen=set()
            with __import__('tarfile').open(fileobj=sys.stdin.buffer,mode='r|') as tar:
                for item in tar:
                    assert item.isfile() and item.name in {'workspace.sqlite','backup.json'} and item.name not in seen
                    seen.add(item.name); entry=recovery/item.name
                    with entry.open('xb') as f: os.chmod(entry,0o600); f.write(tar.extractfile(item).read()); f.flush(); os.fsync(f.fileno())
            assert seen=={'workspace.sqlite','backup.json'}
            assert hashlib.sha256((recovery/'workspace.sqlite').read_bytes()).hexdigest()==p['database_sha256']
            assert hashlib.sha256((recovery/'backup.json').read_bytes()).hexdigest()==p['manifest_sha256']
            manifest=json.loads((recovery/'backup.json').read_text()); (recovery/'blobs').mkdir(mode=0o700)
            for sha in manifest['blobs']:
                assert re.fullmatch('[a-f0-9]{64}',sha)
                old=source/'blobs'/sha[:2]/sha; dest=recovery/'blobs'/sha[:2]/sha
                # Archives can retain bytes already swept from the live CAS.
                # This invocation's snapshot is fresh, so every declared byte
                # must still exist; otherwise refuse rather than weaken recovery.
                assert old.is_file() and old.resolve()==old
                dest.parent.mkdir(mode=0o700,exist_ok=True); os.link(old,dest)
            result={'staged':True}
      except BaseException as error:
        try:
            if created: shutil.rmtree(recovery)
            if owned: owner_file.unlink(missing_ok=True)
        except BaseException as cleanup_error: error.add_note('stage cleanup pending: '+type(cleanup_error).__name__)
        raise
elif action=='apply':
    assert marker()['database_sha256']==p['database_sha256']
    result=m['maintain'](r,apply=True,recovery=recovery,when_idle=True)
    ready(); control=r.operator('control','status')
    result['restored']=not control['draining']
elif action=='cleanup':
    with m['locked'](root):
        ready()
        result=remove_recovery(recovery,p['owner'],p,pwd.getpwnam(r.spec['user']).pw_uid)
else: raise RuntimeError('unknown_maintenance_action')
print(json.dumps(result))
"""

BOOTSTRAP = """import json,os,pathlib,re,sys
root=pathlib.Path(sys.argv[1]); p=pathlib.Path(json.loads((root/'selection.json').read_text())['current'])
assert p.parent.name=='.deploy' and p.name=='spec.json' and p.parents[2]==root/'releases' and re.fullmatch('[a-f0-9]{64}',p.parents[1].name)
exe=p.parents[1]/'.venv/bin/python'; os.execv(str(exe),[str(exe),'-B','-c',sys.argv[2]])
"""


@dataclass(frozen=True)
class Policy:
    host: str
    root: Path
    archives: Path
    owner: str
    hour_utc: int = 2
    window_minutes: int = 60
    budget_seconds: int = 600

    def validate(self) -> None:
        if (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.host) is None
            or re.fullmatch(r"/opt/linker-planner(?:-[a-z0-9-]+)?", str(self.root))
            is None
            or re.fullmatch(r"[a-f0-9]{32}", self.owner) is None
            or not 0 <= self.hour_utc <= 23
            or not 1 <= self.window_minutes <= 60
            or self.budget_seconds <= 0
        ):
            raise ValueError("invalid maintenance policy")
        if (
            not self.archives.is_absolute()
            or self.archives.resolve() != self.archives
            or not self.archives.is_dir()
            or self.archives.stat().st_uid != os.getuid()
            or self.archives.stat().st_mode & 0o077
        ):
            raise ValueError("private existing archive directory required")

    def in_window(self, now: dt.datetime) -> bool:
        utc = now.astimezone(dt.UTC)
        minute = utc.hour * 60 + utc.minute
        return self.hour_utc * 60 <= minute < self.hour_utc * 60 + self.window_minutes


def recovery_owner_file(recovery: Path, owner: str) -> Path:
    return recovery.with_name("." + recovery.name + "." + owner + ".owner")


def recovery_marker(recovery: Path, owner: str, uid: int) -> dict[str, Any] | None:
    marker = recovery_owner_file(recovery, owner)
    if not recovery.exists() and not marker.exists():
        return None
    if (
        recovery.resolve() != recovery
        or marker.resolve() != marker
        or not marker.is_file()
        or marker.stat().st_uid != uid
        or marker.stat().st_nlink != 1
    ):
        raise RuntimeError("foreign_recovery_path_or_owner")
    try:
        value: dict[str, Any] = json.loads(marker.read_text())
        if not isinstance(value, dict):
            raise ValueError("incomplete_owner_marker")
        if value.get("owner") != owner:
            raise RuntimeError("foreign_recovery_owner")
        if not all(
            re.fullmatch(r"[a-f0-9]{64}", value.get(k, ""))
            for k in ("database_sha256", "manifest_sha256")
        ):
            raise ValueError("incomplete_owner_marker")
        return value
    except (ValueError, TypeError):
        if recovery.exists():
            raise RuntimeError("recovery_owner_marker_unreadable") from None
        return {"owner": owner, "incomplete_marker": True}


def remove_recovery(
    recovery: Path, owner: str, expected: dict[str, Any], uid: int
) -> dict[str, Any]:
    note = recovery_marker(recovery, owner, uid)
    if note is None:
        return {"removed": False, "freed_bytes": 0}
    if note.get("incomplete_marker"):
        if not expected.get("incomplete_marker") or recovery.exists():
            raise RuntimeError("recovery_marker_changed")
    elif any(note[k] != expected[k] for k in ("database_sha256", "manifest_sha256")):
        raise RuntimeError("recovery_archive_changed")
    before = os.statvfs(recovery.parent).f_bavail * os.statvfs(recovery.parent).f_frsize
    if recovery.exists():
        shutil.rmtree(recovery)
    # Ownership survives every partial rmtree, and disappears only after data.
    recovery_owner_file(recovery, owner).unlink()
    descriptor = os.open(recovery.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {
        "removed": True,
        "freed_bytes": os.statvfs(recovery.parent).f_bavail
        * os.statvfs(recovery.parent).f_frsize
        - before,
    }


def _write(path: Path, raw: bytes) -> None:
    temporary = path.with_name("." + path.name + ".planner-maintenance.tmp")
    owned = False
    try:
        with temporary.open("xb") as stream:
            owned = True
            os.chmod(temporary, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if owned:
            temporary.unlink(missing_ok=True)


def _finish(process: subprocess.Popen[bytes]) -> None:
    # The launcher may exit before its proxy/helper descendant.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


class Remote:
    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        self.deadline = time.monotonic() + policy.budget_seconds
        self.selected: str | None = None
        self.last_action = "local_recovery"
        self.recovery_seconds = 0.0

    def remaining(self, recovery: bool = False) -> float:
        value = (
            self.deadline
            + (self.recovery_seconds if recovery else 0)
            - time.monotonic()
        )
        if value <= 0:
            raise TimeoutError("maintenance_budget_expired")
        return value

    def start(self, action: str, values: dict[str, Any]) -> subprocess.Popen[bytes]:
        reserve = action == "cleanup"
        budget = self.remaining(reserve)
        self.last_action = action
        command = shlex.join(
            [
                "env",
                "-i",
                "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE=1",
                "python3",
                "-B",
                "-c",
                BOOTSTRAP,
                str(self.policy.root),
                REMOTE,
            ]
        )
        process = subprocess.Popen(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ControlMaster=no",
                "-o",
                "ControlPath=none",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "ServerAliveInterval=15",
                "-o",
                "ServerAliveCountMax=2",
                "--",
                self.policy.host,
                command,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            bufsize=0,
        )
        assert process.stdin is not None
        request = {
            "root": str(self.policy.root),
            "owner": self.policy.owner,
            "action": action,
            "selected": self.selected,
            "budget": budget,
            **values,
        }
        try:
            payload = memoryview(json.dumps(request).encode() + b"\n")
            while payload:
                if not select.select([], [process.stdin], [], self.remaining(reserve))[
                    1
                ]:
                    raise TimeoutError("request_stream_timeout")
                size = os.write(process.stdin.fileno(), payload)
                payload = payload[size:]
        except BaseException:
            _finish(process)
            raise
        return process

    def call(self, action: str, **values: Any) -> dict[str, Any]:
        payload = values.pop("payload", b"")
        process = self.start(action, values)
        try:
            out, error = process.communicate(
                input=payload, timeout=self.remaining(action in {"apply", "cleanup"})
            )
            if process.returncode:
                safe = re.findall(
                    rb"(?:RuntimeError|ValueError|TimeoutError): ([a-z_]+)\s*$", error
                )
                reason = (
                    safe[-1].decode() if safe else "exit_" + str(process.returncode)
                )
                raise RuntimeError("remote_" + action + "_" + reason)
            result: dict[str, Any] = json.loads(out)
            return result
        finally:
            _finish(process)

    def exact(self, stream: IO[bytes], count: int) -> bytes:
        pieces = []
        while count:
            if not select.select([stream], [], [], self.remaining())[0]:
                raise TimeoutError("snapshot_stream_timeout")
            raw = os.read(stream.fileno(), min(count, 1024 * 1024))
            if not raw:
                raise RuntimeError("snapshot_stream_ended")
            pieces.append(raw)
            count -= len(raw)
        return b"".join(pieces)

    @contextmanager
    def snapshot(self, known: list[str]) -> Iterator[tuple[dict[str, Any], Any]]:
        process = self.start("snapshot", {"known": known})
        assert process.stdout is not None and process.stdin is not None
        try:
            length = struct.unpack(">I", self.exact(process.stdout, 4))[0]
            if not 0 < length <= 8 * 1024 * 1024:
                raise ValueError("snapshot_header_exceeds_budget")
            header = json.loads(self.exact(process.stdout, length))
            yield header, lambda count: self.exact(process.stdout, count)
            process.stdin.write(b"verified\n")
            process.stdin.flush()
            if self.exact(process.stdout, 6) != b"ACKED\n":
                raise RuntimeError("snapshot_acknowledgement_missing")
            process.wait(timeout=self.remaining())
            if process.returncode:
                raise RuntimeError("snapshot_remote_failed")
        finally:
            _finish(process)


class Archives:
    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        self.path = policy.archives / "RECOVERY-POINTS.json"
        self.registry: dict[str, Any] = json.loads(self.path.read_text())
        source = self.registry.get("source", {})
        if source.get("host") != policy.host or source.get("root") != str(policy.root):
            raise ValueError("recovery_registry_source_mismatch")
        if self.registry.get("maintenance_owner", policy.owner) != policy.owner:
            raise ValueError("maintenance_owner_changed")

    def entries(self) -> list[dict[str, Any]]:
        return [
            e
            for e in self.registry["entries"]
            if e["kind"] == "verified_workspace_archive"
        ]

    def latest(self) -> Path:
        path = Path(self.registry["latest_verified_recovery"])
        if path.parent != self.policy.archives or path.resolve() != path:
            raise ValueError("unmanaged_recovery_path")
        if not any(e["path"] == str(path) for e in self.entries()):
            raise ValueError("unregistered_recovery")
        return path

    def verify(self, path: Path) -> dict[str, Any]:
        return independent_snapshot(path, self.policy.root / "state/workspace")

    def save(self) -> None:
        _write(self.path, json.dumps(self.registry, indent=1, sort_keys=True).encode())

    def find(self, marker: dict[str, Any]) -> Path:
        for entry in self.entries():
            path = Path(entry["path"])
            if (
                entry["database"]["sha256"] == marker["database_sha256"]
                and entry["manifest"]["sha256"] == marker["manifest_sha256"]
            ):
                self.verify(path)
                return path
        raise RuntimeError("owned_recovery_has_no_verified_local_archive")

    def publish(self, remote: Remote, now: dt.datetime) -> Path:
        basis = self.latest()
        prior = self.verify(basis)
        known = prior["blobs"]
        assert isinstance(known, list)
        incoming = self.policy.archives / (".incoming-maintenance-" + self.policy.owner)
        if incoming.exists():
            state = json.loads(self.status_path.read_text())
            if (
                state.get("owner") != self.policy.owner
                or incoming.resolve() != incoming
            ):
                raise RuntimeError("interrupted_snapshot_requires_inspection")
            # The local singleton lock excludes its old writer. No GC is
            # admitted before publish/verify, so this partial is reconstructable.
            shutil.rmtree(incoming)
        destination = self.policy.archives / (
            "archive-" + now.strftime("%Y%m%dT%H%M%SZ") + "-" + self.policy.owner[:8]
        )
        if destination.exists():
            raise RuntimeError("snapshot_destination_exists")
        state = json.loads(self.status_path.read_text())
        state["pending_archive"] = str(destination)
        _write(self.status_path, json.dumps(state).encode())
        created = False
        try:
            with remote.snapshot(known) as (header, read):
                database = read(header["database_bytes"])
                manifest_bytes = read(header["manifest_bytes"])
                manifest = json.loads(manifest_bytes)
                if manifest["database_sha256"] != hashlib.sha256(database).hexdigest():
                    raise ValueError("snapshot_database_hash_mismatch")
                # Reuse a complete snapshot with exactly the same DB and bytes.
                if manifest == prior:
                    if header["missing"]:
                        raise ValueError("inconsistent_snapshot_delta")
                    state.pop("pending_archive", None)
                    _write(self.status_path, json.dumps(state).encode())
                    return basis
                incoming.mkdir(mode=0o700)
                created = True
                _write(incoming / "workspace.sqlite", database)
                _write(incoming / "backup.json", manifest_bytes)
                (incoming / "blobs").mkdir(mode=0o700)
                for sha in manifest["blobs"]:
                    target = incoming / "blobs" / sha[:2] / sha
                    target.parent.mkdir(mode=0o700, exist_ok=True)
                    if sha not in header["missing"]:
                        old = basis / "blobs" / sha[:2] / sha
                        if (
                            old.resolve() != old
                            or old.stat().st_size != header["sizes"][sha]
                        ):
                            raise ValueError("snapshot_reuse_byte_mismatch")
                        os.link(old, target)
                for sha in header["missing"]:
                    raw = read(header["sizes"][sha])
                    if hashlib.sha256(raw).hexdigest() != sha:
                        raise ValueError("snapshot_delta_hash_mismatch")
                    _write(incoming / "blobs" / sha[:2] / sha, raw)
                self.verify(incoming)
                archive._publish(incoming, destination)
            self.registry["entries"].append(
                {
                    "kind": "verified_workspace_archive",
                    "path": str(destination),
                    "created_at_utc": now.isoformat(),
                    "database": {"sha256": manifest["database_sha256"]},
                    "manifest": {"sha256": hashlib.sha256(manifest_bytes).hexdigest()},
                }
            )
            self.registry["latest_verified_recovery"] = str(destination)
            self.save()
            state.pop("pending_archive", None)
            _write(self.status_path, json.dumps(state).encode())
            return destination
        finally:
            if created and incoming.exists():
                shutil.rmtree(incoming)

    @property
    def status_path(self) -> Path:
        return self.policy.archives / ("maintenance-" + self.policy.owner + ".json")

    def interrupted_publish(self, state: dict[str, Any]) -> None:
        """Register a verified rename whose caller died before registry commit."""
        candidate = state.get("pending_archive")
        if not candidate:
            return
        path = Path(candidate)
        if path.parent != self.policy.archives or path.resolve() != path:
            raise ValueError("unmanaged_interrupted_archive")
        if path.exists() and not any(e["path"] == str(path) for e in self.entries()):
            manifest = self.verify(path)
            self.registry["entries"].append(
                {
                    "kind": "verified_workspace_archive",
                    "path": str(path),
                    "database": {"sha256": manifest["database_sha256"]},
                    "manifest": {"sha256": _metadata(path)["manifest_sha256"]},
                }
            )
            self.registry["latest_verified_recovery"] = str(path)
            self.save()
        state.pop("pending_archive", None)
        _write(self.status_path, json.dumps(state).encode())

    def rotate(self, current: Path) -> None:
        """Retain N=3 managed archives and every explicit DB baseline binding."""
        self.verify(current)
        protected = {str(current)}
        for entry in self.registry["entries"]:
            if entry["kind"] != "db_only_snapshot":
                if entry.get("protected"):
                    protected.add(entry["path"])
                continue
            database = Path(entry["path"])
            if hashlib.sha256(database.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("protected_baseline_changed")
            try:
                closure = archive._check_database(database, Blobs(current / "blobs"))
            except Exception:
                binding = entry.get("independent_local_CAS_binding", {})
                if not binding.get("archive"):
                    raise ValueError(
                        "baseline_has_no_independent_CAS_binding"
                    ) from None
                bound = Path(binding["archive"])
                if not any(e["path"] == str(bound) for e in self.entries()):
                    raise ValueError("unregistered_baseline_CAS_binding") from None
                self.verify(bound)
                archive._check_database(database, Blobs(bound / "blobs"))
                protected.add(binding["archive"])
            else:
                entry["independent_local_CAS_binding"] = {
                    "archive": str(current),
                    "depends_on_remote_source_CAS": False,
                    "verified_reference_closure": len(closure),
                }
        entries = sorted(
            self.entries(), key=lambda e: Path(e["path"]).name, reverse=True
        )
        keep = set(protected)
        for entry in entries:
            if len(keep) < 3:
                keep.add(entry["path"])
        if len(keep) > 3:
            raise RuntimeError("explicit_recovery_references_exceed_N3")
        for entry in entries:
            if entry["path"] in keep:
                continue
            path = Path(entry["path"])
            if path.parent != self.policy.archives or path.resolve() != path:
                raise ValueError("unmanaged_retirement_path")
            pending = self.registry.get("retirement_pending", {})
            resuming = (
                pending.get("path") == str(path)
                and pending.get("owner") == self.policy.owner
            )
            if not path.exists() and resuming:
                self.registry["entries"].remove(entry)
                self.registry.pop("retirement_pending", None)
                self.save()
                continue
            # The durable intent follows full verification. A partial rmtree
            # cannot be verified again; it remains the same exact owned path.
            if not resuming:
                self.verify(path)
            handles = subprocess.run(
                ["lsof", "-t", "+D", str(path)], capture_output=True, timeout=15
            )
            if handles.returncode not in (0, 1) or handles.stdout:
                raise RuntimeError("retired_archive_has_readers")
            self.registry["retirement_pending"] = {
                "path": str(path),
                "owner": self.policy.owner,
            }
            self.save()
            shutil.rmtree(path)
            self.registry["entries"].remove(entry)
            self.registry.pop("retirement_pending", None)
            self.save()
        self.save()


def _metadata(path: Path) -> dict[str, str]:
    return {
        "database_sha256": hashlib.sha256(
            (path / "workspace.sqlite").read_bytes()
        ).hexdigest(),
        "manifest_sha256": hashlib.sha256(
            (path / "backup.json").read_bytes()
        ).hexdigest(),
    }


def _metadata_tar(path: Path) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name in ("workspace.sqlite", "backup.json"):
            item = tar.gettarinfo(str(path / name), arcname=name)
            item.mode, item.uid, item.gid, item.uname, item.gname = 0o600, 0, 0, "", ""
            with (path / name).open("rb") as source:
                tar.addfile(item, source)
    return stream.getvalue()


def run(policy: Policy, remote: Remote, now: dt.datetime) -> dict[str, Any]:
    now = now.astimezone(dt.UTC)
    if not policy.in_window(now):
        return {"status": "skipped", "reason": "outside_UTC_window"}
    state_path = policy.archives / ("maintenance-" + policy.owner + ".json")
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state.get("attempt_day") == now.date().isoformat():
        return {"status": "skipped", "reason": "already_attempted_today"}
    if state and state.get("owner") != policy.owner:
        raise ValueError("foreign_maintenance_state")
    store = Archives(policy)
    store.interrupted_publish(state)
    if len(store.entries()) > 3:
        store.rotate(store.latest())
    state.update(attempt_day=now.date().isoformat(), owner=policy.owner)
    _write(state_path, json.dumps(state).encode())
    view = remote.call("plan")
    remote.selected = view["selected"]
    remote.recovery_seconds = float(view["recovery_seconds"])
    old_recovery = view.get("recovery")
    if old_recovery:
        if not old_recovery.get("incomplete_marker"):
            store.find(old_recovery)
        remote.call("cleanup", **old_recovery)
    if view["status"] == "busy":
        return {"status": "skipped", "reason": "busy"}
    plan = view["plan"]
    if not plan["candidate_count"] and not plan["temporary_count"]:
        return {"status": "noop", "candidate_count": 0}
    # The owner belongs to the namespace, not this day's invocation/release.
    # Persist it before creating a snapshot or remote root, so an upgrade cannot
    # silently select a new owner and abandon the previous owned resources.
    store.registry["maintenance_owner"] = policy.owner
    store.save()
    recovery = store.publish(remote, now)
    store.rotate(recovery)
    metadata = _metadata(recovery)
    result: dict[str, Any] = {}
    failure: BaseException | None = None
    try:
        remote.call("stage", payload=_metadata_tar(recovery), **metadata)
        result = remote.call("apply", **metadata)
    except BaseException as error:
        failure = error
        raise
    finally:
        try:
            cleanup = remote.call("cleanup", **metadata)
            result["freed_bytes"] = cleanup["freed_bytes"]
        except BaseException as error:
            if failure is None:
                raise
            failure.add_note("owned recovery cleanup pending: " + type(error).__name__)
    outcome = (
        "skipped"
        if result.get("mode") == "skipped"
        else "noop"
        if result.get("mode") == "noop"
        else "complete"
    )
    return {"status": outcome, **result, "archive": str(recovery)}


def interrupted(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


@contextmanager
def interruption_signals() -> Iterator[None]:
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGHUP)}
    for sig in previous:
        signal.signal(sig, interrupted)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main() -> int:
    with interruption_signals():
        return _main()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--root", type=Path, default=Path("/opt/linker-planner"))
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--hour-utc", type=int, default=2)
    parser.add_argument("--window-minutes", type=int, default=60)
    parser.add_argument("--budget-seconds", type=int, default=600)
    args = parser.parse_args()
    policy = Policy(**vars(args))
    changed = True
    remote = Remote(policy)
    try:
        policy.validate()
        # The inode is retained with the registry; never unlink a lock with waiters.
        with (policy.archives / "maintenance.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            status_path = policy.archives / ("maintenance-" + policy.owner + ".json")
            # Only these component-owned atomic writes are reconstructable.
            # The held singleton lock and bound registry exclude their writers;
            # partial bytes from a hard kill are never a second recovery copy.
            for target in (status_path, policy.archives / "RECOVERY-POINTS.json"):
                pending = target.with_name(
                    "." + target.name + ".planner-maintenance.tmp"
                )
                if pending.exists() or pending.is_symlink():
                    Archives(policy)
                    if (
                        pending.is_symlink()
                        or not pending.is_file()
                        or pending.stat().st_uid != os.getuid()
                    ):
                        raise ValueError("foreign_atomic_maintenance_file")
                    pending.unlink()
            prior = json.loads(status_path.read_text()) if status_path.exists() else {}
            try:
                result = run(policy, remote, dt.datetime.now(dt.UTC))
            except BaseException as error:
                result = failure_result(error, remote.last_action)
            # Keep one small operational status, never candidate lists/customer
            # records. Atomic replacement preserves the daily-attempt marker.
            result = {
                k: v
                for k, v in result.items()
                if k
                in {
                    "status",
                    "reason",
                    "mode",
                    "deleted_count",
                    "deleted_bytes",
                    "candidate_count",
                    "temporary_deleted_count",
                    "freed_bytes",
                    "restored",
                    "archive",
                    "phase",
                    "cleanup_pending",
                }
            }
            current = (
                json.loads(status_path.read_text()) if status_path.exists() else {}
            )
            if current and current.get("owner") not in {None, policy.owner}:
                raise ValueError("foreign_maintenance_state")
            changed = prior.get("last_check") != result
            current.update(
                owner=policy.owner,
                checked_at=dt.datetime.now(dt.UTC).isoformat(),
                last_check=result,
            )
            # Hourly local no-work checks must not erase the most recent real
            # attempt/failure. Retain only one of each, never an event history.
            if result["status"] in {"error", "complete"}:
                current["last_result"] = result
                current["last_attempt_at"] = dt.datetime.now(dt.UTC).isoformat()
            if result["status"] == "error":
                current["last_failure"] = result
                current["last_failure_at"] = dt.datetime.now(dt.UTC).isoformat()
            _write(status_path, json.dumps(current, sort_keys=True).encode())
    except BlockingIOError:
        result = {"status": "skipped", "reason": "local_maintenance_busy"}
    except BaseException as error:
        result = failure_result(error, remote.last_action)
    message = "linker-planner-maintenance " + json.dumps(result, sort_keys=True)
    if changed or result["status"] == "complete":
        syslog.syslog(
            syslog.LOG_ERR if result["status"] == "error" else syslog.LOG_INFO, message
        )
    print(message, flush=True)
    return 1 if result["status"] == "error" else 0


def failure_result(error: BaseException, phase: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "error",
        "reason": type(error).__name__,
        "phase": phase,
    }
    if isinstance(error, RuntimeError) and re.fullmatch(r"[a-zA-Z0-9_]+", str(error)):
        result["reason"] = str(error)
    if any("cleanup pending" in note for note in getattr(error, "__notes__", [])):
        result["cleanup_pending"] = True
    return result


if __name__ == "__main__":
    sys.exit(main())
