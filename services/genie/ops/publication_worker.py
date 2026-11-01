"""One automatic Mac knowledge preparation job, claimed from Woo's durable queue.

Runs under launchd (install_publication_worker.py). Heavy parsing stays on the Mac.
The worker never grants publication: late jobs are rejected by Woo and every
runtime read independently checks current permission. Credentials are env-only.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import syslog
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

# launchd invokes an absolute script path with the locked environment's Python.
# Script entry does not add the project root to sys.path; this is local bootstrap,
# not a user PYTHONPATH requirement or a global interpreter setting.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from index import build, inventory, parse  # noqa: E402
from index.paths import INDEX_DIR, INVENTORY_PATH, PARSED_DIR, PDF_DIR  # noqa: E402
from index.preparation import recipe_revision  # noqa: E402
from index.publication import inventory as fetch_inventory  # noqa: E402
from linker_genie.embedding import Embedder  # noqa: E402
from linker_genie.preparation import RUNTIME_SERVING_REVISION  # noqa: E402
from linker_genie.publication import Snapshot, knowledge_progress  # noqa: E402
from publish_index import (  # noqa: E402
    ActivationOutcomeUnconfirmed,
    NativeVerificationRejected,
    PreActivationDeferred,
    publish,
)

ACK_RECOVERY_PROTOCOL = "native-knowledge-ack-recovery-v1"
# Match the native activation verifier: three attempts, one/two-second backoff,
# and the publication client's 20-second request bound, within the original lease.
ACK_ATTEMPTS = 3
ACK_TIMEOUT = 20.0


def report_failure(phase: str, error: BaseException) -> None:
    """Report only code location and safe error metadata to the system log."""
    details = [
        "linker-knowledge-publication",
        f"phase={phase}",
        f"error={type(error).__name__}",
    ]
    if isinstance(error, NativeVerificationRejected) and error.reason in {
        "retry_exhausted",
        "http_rejected",
        "expired",
        "response_identity",
        "invalid_response",
    }:
        details.append(f"native_verify={error.reason}")
        if type(error.status) is int and 100 <= error.status <= 599:
            details.append(f"http_status={error.status}")
        if error.transport:
            details.append("transport=remote")
        if error.cleanup_unconfirmed:
            details.append("upload_cleanup=unconfirmed")
    # PublicationUnavailable deliberately hides request details, but retains
    # its cause. Report only its safe type/status so an outage is diagnosable.
    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, httpx.HTTPStatusError):
            if cause is not error:
                details.append("cause=HTTPStatusError")
            details.append(f"http_status={cause.response.status_code}")
            break
        if isinstance(cause, httpx.TransportError):
            allowed = {
                "ConnectError",
                "ConnectTimeout",
                "ReadError",
                "ReadTimeout",
                "WriteError",
                "WriteTimeout",
                "RemoteProtocolError",
                "PoolTimeout",
            }
            name = type(cause).__name__
            details.append(
                f"transport={name if name in allowed else 'other_transport'}"
            )
            break
        cause = cause.__cause__
    if isinstance(error, OSError) and isinstance(error.errno, int):
        details.append(f"errno={error.errno}")
    trace = error.__traceback__
    if trace is not None:
        while trace.tb_next is not None:
            trace = trace.tb_next
        filename = Path(trace.tb_frame.f_code.co_filename).name
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,97}\.py", filename):
            details.append(f"location={filename}:{trace.tb_lineno}")
    message = " ".join(details)
    try:
        syslog.syslog(syslog.LOG_ERR, message)
    except OSError:
        print(message, file=sys.stderr)


_LOADED_PROGRAM = """import json, sys, urllib.request
try:
    data = json.load(sys.stdin)
    request = urllib.request.Request(data['url'], data=b'{}', method='POST', headers={
        'Content-Type': 'application/json', 'X-Linker-Service-Token': data['token']})
    with urllib.request.urlopen(request, timeout=20) as response:
        loaded = json.load(response)
    loaded['preparation_complete'] = loaded.get('preparation_complete') is True
    loaded['materialization_complete'] = loaded.get('materialization_complete') is True
    loaded['recipe_revision'] = loaded.get('recipe_revision', '')
    loaded['model_identity_revision'] = loaded.get('model_identity_revision', '')
    loaded['expected_serving_revision'] = loaded.get('expected_serving_revision', '')
    loaded['serving_revision'] = loaded.get('serving_revision', '')
    loaded['activation_epoch'] = loaded.get('activation_epoch', 0)
    loaded['unprepared_documents'] = loaded.get('unprepared_documents', [])
    print(json.dumps({key: loaded[key] for key in ('index_version', 'source_revision', 'model_identity_revision', 'recipe_revision', 'expected_serving_revision', 'serving_revision', 'activation_epoch', 'products', 'materialization_complete', 'preparation_complete', 'unprepared_documents')}))
except Exception:
    sys.exit(1)
"""


def read_loaded(url: str, token: str, host: str | None = None) -> dict[str, Any]:
    """Ask the serving process on its loopback, using one managed SSH call.

    The token travels in stdin, never SSH arguments, a temporary script or logs.
    No persistent forwarding process is needed for the automatic Mac worker.
    """
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.path != "/knowledge/loaded"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("loaded verification requires the private service loopback")
    if host is None:
        response = httpx.post(
            url, json={}, timeout=20, headers={"X-Linker-Service-Token": token}
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "--",
            host,
            "python3 -c " + shlex.quote(_LOADED_PROGRAM),
        ],
        input=json.dumps({"url": url, "token": token}),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("running Genie loaded verification failed")
    result = json.loads(completed.stdout)
    if not isinstance(result, dict):
        raise RuntimeError("running Genie returned invalid loaded verification")
    return result


def record_build(index_dir: Path, directory: Path) -> None:
    """Journal exactly the generation just created by this worker invocation."""
    if directory.resolve().parent != (index_dir / "builds").resolve():
        raise ValueError("worker generation is outside the builds root")
    try:
        marker = directory / ".publication-worker-owned"
        marker.write_text("publication-worker")
        (index_dir / "publication-worker-pending.json").write_text(
            json.dumps({"path": str(directory.resolve())})
        )
    except Exception:
        # The builder just created this exact directory; registration failure
        # cannot leave an untracked failed output behind.
        shutil.rmtree(directory)
        raise


def pending_build(index_dir: Path) -> Path | None:
    """Only an explicit owned pending record permits failed-run cleanup."""
    ledger = index_dir / "publication-worker-pending.json"
    if not ledger.is_file():
        return None
    data = json.loads(ledger.read_text())
    directory = Path(data["path"]).resolve()
    if directory.parent != (index_dir / "builds").resolve():
        raise RuntimeError("pending worker build escaped its owned root")
    if (
        directory.is_dir()
        and (directory / ".publication-worker-owned").read_text()
        != "publication-worker"
    ):
        raise RuntimeError("pending build has no worker ownership marker")
    return directory


def discard_pending(index_dir: Path) -> None:
    """Remove only this worker's failed/abandoned pending generation."""
    directory = pending_build(index_dir)
    if directory is not None and directory.is_dir():
        shutil.rmtree(directory)
    (index_dir / "publication-worker-pending.json").unlink(missing_ok=True)


def validated_pending(
    index_dir: Path, activation: dict[str, Any], expected_index: dict[str, Any]
) -> Path:
    """Recheck an explicitly resumed generation against its original live lease."""
    directory = pending_build(index_dir)
    if directory is None or not directory.is_dir():
        raise RuntimeError("the deferred generation is missing")
    manifest_path, index_path = directory / "manifest.json", directory / "index.sqlite"
    if any(
        path.is_symlink() or not path.is_file() for path in (manifest_path, index_path)
    ):
        raise RuntimeError("the deferred generation files are not regular")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "version": expected_index.get("version"),
        "source_revision": activation.get("source_revision"),
        "model_identity_revision": activation.get("model_identity_revision"),
        "recipe_revision": activation.get("recipe_revision"),
        "serving_revision": activation.get("serving_revision"),
        "activation_epoch": activation.get("epoch"),
    }
    with index_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest.get("file"), dict)
        or directory.name != expected["version"]
        or manifest["file"].get("name") != "index.sqlite"
        or manifest["file"].get("sha256") != digest
        or expected_index.get("sha256") != digest
        or any(manifest.get(key) != value for key, value in expected.items())
    ):
        raise RuntimeError("the deferred generation identity or checksum differs")
    db = sqlite3.connect(index_path.as_uri() + "?mode=ro", uri=True)
    try:
        meta = dict(db.execute("SELECT key,value FROM meta"))
    finally:
        db.close()
    if any(meta.get(key) != str(value) for key, value in expected.items()):
        raise RuntimeError("the deferred index metadata differs")
    return directory


def retain_builds(index_dir: Path, current: Path) -> None:
    """Keep current and one prior worker-owned build; unrelated evidence stays.

    This is the bounded runtime retention from docs/agents/local-storage.md.
    A ledger entry alone can never delete outside this worker's builds root.
    """
    root = (index_dir / "builds").resolve()
    current = current.resolve()
    if current.parent != root or not current.is_dir():
        raise ValueError("prepared build is outside the worker builds directory")
    ledger = index_dir / "publication-worker-releases.json"
    raw = json.loads(ledger.read_text()) if ledger.is_file() else []
    owned: list[str] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, str):
            continue
        path = Path(item).resolve()
        if path.parent == root and path.is_dir() and str(path) not in owned:
            owned.append(str(path))
    owned = [item for item in owned if item != str(current)] + [str(current)]
    for old in owned[:-2]:
        shutil.rmtree(Path(old))
    ledger.write_text(json.dumps(owned[-2:], indent=1))


def retain_review_build(index_dir: Path, error: NativeVerificationRejected) -> Path:
    """Keep at most one validated exhausted build, for review only."""
    if error.reason != "retry_exhausted":
        raise RuntimeError("only exhausted verification can retain a review build")
    ledger = index_dir / "publication-worker-pending.json"
    raw = json.loads(ledger.read_text())
    recorded = Path(raw["path"])
    directory = pending_build(index_dir)
    identity = error.identity
    if (
        directory is None
        or recorded.is_symlink()
        or not directory.is_dir()
        or directory.parent != (index_dir / "builds").resolve()
        or directory.name != identity.get("version")
        or not isinstance(identity.get("job_id"), str)
        or not identity["job_id"]
        or type(identity.get("activation_epoch")) is not int
        or identity["activation_epoch"] < 1
        or not isinstance(identity.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) is None
    ):
        raise RuntimeError("review candidate ownership or identity differs")
    manifest_path, index_path = directory / "manifest.json", directory / "index.sqlite"
    if any(
        path.is_symlink() or not path.is_file() for path in (manifest_path, index_path)
    ):
        raise RuntimeError("review candidate files are not regular")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with index_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    expected = {
        name: identity.get(name)
        for name in (
            "version",
            "source_revision",
            "model_identity_revision",
            "recipe_revision",
            "serving_revision",
            "activation_epoch",
        )
    }
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest.get("file"), dict)
        or manifest["file"].get("name") != "index.sqlite"
        or manifest["file"].get("sha256") != digest
        or digest != identity["sha256"]
        or type(manifest.get("activation_epoch")) is not int
        or any(manifest.get(key) != value for key, value in expected.items())
    ):
        raise RuntimeError("review candidate manifest or hash differs")
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    try:
        meta = dict(db.execute("SELECT key,value FROM meta"))
    finally:
        db.close()
    if any(meta.get(key) != str(value) for key, value in expected.items()):
        raise RuntimeError("review candidate SQLite identity differs")
    quarantine = index_dir.resolve() / "publication-review-builds"
    if quarantine.is_symlink() or (quarantine.exists() and not quarantine.is_dir()):
        raise RuntimeError("review candidate root is unsafe")
    quarantine.mkdir(mode=0o700, exist_ok=True)
    if quarantine.stat().st_mode & 0o077 or any(quarantine.iterdir()):
        raise RuntimeError("review candidate slot is not private and empty")
    (directory / ".publication-review.json").write_text(
        json.dumps(
            {
                **identity,
                "reason": "native verification retries exhausted",
                "usage": "review only; a new native lease and reviewed rebinding are required",
            }
        ),
        encoding="utf-8",
    )
    destination = quarantine / directory.name
    directory.rename(destination)
    return destination


def _valid_loaded_observation(value: Any) -> bool:
    """Known diagnostic shape, distinct from a transport error or partial body."""
    if not isinstance(value, dict) or any(
        not isinstance(value.get(key), str)
        for key in (
            "source_revision",
            "model_identity_revision",
            "recipe_revision",
            "expected_serving_revision",
            "serving_revision",
            "index_version",
        )
    ):
        return False
    if (
        not value["serving_revision"]
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", value["index_version"])
        or type(value.get("activation_epoch")) is not int
        or value["activation_epoch"] < 0
        or not isinstance(value.get("products"), list)
    ):
        return False
    products = value["products"]
    return not any(
        not isinstance(product, dict)
        or type(product.get("product_id")) is not int
        or product["product_id"] < 1
        or not isinstance(product.get("product_revision"), str)
        or not product["product_revision"]
        for product in products
    ) and len({product["product_id"] for product in products}) == len(products)


class Worker:
    def __init__(
        self,
        jobs_url: str,
        user: str,
        password: str,
        worker_id: str,
        lease_seconds: int,
        *,
        transport: httpx.BaseTransport | None = None,
        recipe: str | None = None,
        serving: str | None = None,
    ) -> None:
        self.jobs = jobs_url.rstrip("/")
        self.worker_id, self.lease = worker_id, lease_seconds
        self.recipe = recipe_revision() if recipe is None else recipe
        self.serving = RUNTIME_SERVING_REVISION if serving is None else serving
        self._credentials = (user, password)
        self._active_job: dict[str, Any] | None = None
        self._published = False
        self.client = httpx.Client(
            auth=(user, password),
            timeout=120,
            transport=transport,
            headers={"Cache-Control": "no-cache"},
        )

    def claim(
        self,
        loaded_receipt: dict[str, Any] | None = None,
        loaded_unavailable: bool = False,
    ) -> dict[str, Any] | None:
        response = self.client.post(
            self.jobs + "/claim",
            json={
                "consumer": "knowledge",
                "identity_protocol": "native-model-identification-v1",
                "ack_recovery_protocol": ACK_RECOVERY_PROTOCOL,
                "worker_id": self.worker_id,
                "lease_seconds": self.lease,
                "recipe_revision": self.recipe,
                "loaded_receipt": loaded_receipt,
                "loaded_unavailable": loaded_unavailable,
            },
        )
        response.raise_for_status()
        job: dict[str, Any] | None = response.json()["job"]
        return job

    def activation(self) -> dict[str, Any]:
        """Private stdin-only activation fence for this exact leased generation."""
        job = self._active_job
        if (
            job is None
            or type(job.get("activation_epoch")) is not int
            or job["activation_epoch"] < 1
        ):
            raise RuntimeError("index activation requires a current native lease epoch")
        return {
            "epoch": job["activation_epoch"],
            "lease_expires_at": job.get("lease_expires_at"),
            "job_id": job["job_id"],
            "source_revision": job["source_revision"],
            "model_identity_revision": job["model_identity_revision"],
            "recipe_revision": self.recipe,
            "serving_revision": self.serving,
            "verify_url": self.jobs + "/claim",
            "verify_body": {
                "operation": "verify",
                "consumer": "knowledge",
                "job_id": job["job_id"],
                "source_revision": job["source_revision"],
                "model_identity_revision": job["model_identity_revision"],
                "recipe_revision": self.recipe,
                "lease_token": job["lease_token"],
                "activation_epoch": job["activation_epoch"],
            },
            "username": self._credentials[0],
            "password": self._credentials[1],
        }

    def lease_expiry(self) -> int:
        """The compiler may retry only while its native lease remains current."""
        expiry = self.activation().get("lease_expires_at")
        if type(expiry) is not int or expiry <= time.time() + 1:
            raise RuntimeError("native knowledge lease expired or missing")
        return expiry

    def publication_confirmed(self) -> None:
        """Native publish returned; later progress/readback errors cannot cancel it."""
        self._published = True

    def ack(
        self,
        job: dict[str, Any],
        loaded: str,
        error: str = "",
        products: list[dict[str, Any]] | None = None,
        preparation_complete: bool = False,
        unprepared_documents: list[dict[str, Any]] | None = None,
        materialization_complete: bool = False,
        index_version: str = "",
        loaded_recipe_revision: str = "",
        serving_revision: str = "",
        loaded_model_identity_revision: str = "",
        *,
        require_complete: bool = False,
    ) -> None:
        body = {
            "job_id": job["job_id"],
            "lease_token": job["lease_token"],
            "source_revision": job["source_revision"],
            "loaded_revision": loaded,
            "model_identity_revision": job.get("model_identity_revision", ""),
            "loaded_model_identity_revision": loaded_model_identity_revision,
            "status": "ready" if loaded else "failed",
            "error": error,
            "prepared_products": products or [],
            "preparation_complete": preparation_complete,
            "unprepared_documents": unprepared_documents or [],
            "recipe_revision": self.recipe,
            "loaded_recipe_revision": loaded_recipe_revision,
            "index_version": index_version,
            "materialization_complete": materialization_complete,
            "expected_serving_revision": self.serving,
            "serving_revision": serving_revision,
            "activation_epoch": job.get("activation_epoch", 0),
        }
        for attempt in range(ACK_ATTEMPTS if loaded else 1):
            remaining = 0.0
            if loaded:
                expiry = job.get("lease_expires_at")
                if type(expiry) is not int or expiry - time.time() <= 1:
                    raise RuntimeError("native knowledge ACK lease expired or missing")
                remaining = expiry - time.time() - 1
            try:
                if loaded:
                    response = self.client.post(
                        self.jobs + "/ack",
                        json=body,
                        timeout=min(ACK_TIMEOUT, remaining),
                    )
                else:
                    response = self.client.post(self.jobs + "/ack", json=body)
                response.raise_for_status()
                receipt = response.json()
                if receipt.get("accepted") is not True:
                    raise RuntimeError(
                        "Woo did not acknowledge the prepared generation"
                    )
                if require_complete and receipt.get("complete") is not True:
                    raise RuntimeError(
                        "Woo accepted the generation but native readiness remains incomplete"
                    )
                return
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                if (
                    not loaded
                    or attempt + 1 == ACK_ATTEMPTS
                    or (
                        isinstance(error, httpx.HTTPStatusError)
                        and error.response.status_code < 500
                    )
                ):
                    raise
                delay = float(2**attempt)
                if job["lease_expires_at"] - time.time() <= delay + 1:
                    raise RuntimeError(
                        "native knowledge lease expires before ACK retry"
                    ) from error
                knowledge_progress(
                    "ready_ack", "backoff", attempt=attempt + 1, seconds=delay
                )
                time.sleep(delay)

    def one(self, prepare: Any, loaded: Any) -> bool:
        before = None
        unavailable = False
        if self.recipe:
            try:
                before = loaded()
                if not isinstance(before, dict) or not _valid_loaded_observation(
                    before
                ):
                    raise RuntimeError("loaded observation is incomplete or malformed")
            except (Exception, SystemExit) as error:
                report_failure("loaded_observation", error)
                before = None
                unavailable = True
        job = self.claim(before, unavailable)
        if job is None:
            return False
        phase = "job_validation"
        self._published = False
        recovering = job.get("ack_only") is True
        knowledge_progress(phase, "start")
        try:
            self._active_job = job
            snapshot = Snapshot.read(job["manifest"])
            revision = snapshot.source_revision
            if (
                not snapshot.model_identity_revision
                or snapshot.model_identity_revision
                != job.get("model_identity_revision")
            ):
                raise RuntimeError(
                    "job model identity differs from its claimed manifest"
                )
            if revision != job["source_revision"]:
                raise RuntimeError(
                    "job manifest revision differs from its claimed source"
                )
            if job.get("recipe_revision", "") not in {"", self.recipe}:
                raise RuntimeError("job recipe differs from the running worker")
            if self.recipe and (
                type(job.get("activation_epoch")) is not int
                or job["activation_epoch"] < 1
            ):
                raise RuntimeError("native knowledge job has no activation lease epoch")
            if recovering:
                phase = "ack_recovery"
                knowledge_progress(phase, "start")
                if not isinstance(before, dict) or not _valid_loaded_observation(
                    before
                ):
                    raise RuntimeError(
                        "ACK recovery requires a complete loaded observation"
                    )
                version = before["index_version"]
            else:
                phase = "prepare"
                knowledge_progress(phase, "start")
                version = prepare(job["manifest"])
                self.publication_confirmed()
            phase = "loaded_readback"
            knowledge_progress(phase, "start")
            actual = loaded()
            phase = "loaded_validation"
            knowledge_progress(phase, "start")
            if (
                actual.get("source_revision") != revision
                or actual.get("model_identity_revision")
                != snapshot.model_identity_revision
                or actual.get("index_version") != version
                or not isinstance(version, str)
                or not version
                or (bool(self.recipe) and actual.get("recipe_revision") != self.recipe)
                or (
                    bool(self.recipe)
                    and (
                        actual.get("expected_serving_revision") != self.serving
                        or actual.get("serving_revision") != self.serving
                        or type(actual.get("activation_epoch")) is not int
                        or actual.get("activation_epoch") != job["activation_epoch"]
                    )
                )
            ):
                raise RuntimeError(
                    "running Genie has not loaded the prepared generation"
                )
            products = actual.get("products", [])
            expected = {
                pid: product["product_revision"]
                for pid, product in snapshot.products.items()
            }
            if (
                not isinstance(products, list)
                or any(
                    not isinstance(product, dict)
                    or type(product.get("product_id")) is not int
                    or product["product_id"] not in expected
                    or product.get("product_revision")
                    != expected[product["product_id"]]
                    for product in products
                )
                or len({product["product_id"] for product in products}) != len(products)
            ):
                raise RuntimeError("running Genie returned invalid prepared products")
            partial = len(products) < len(snapshot.products)
            complete = (
                actual.get("preparation_complete") is True
                and not partial
                and not actual.get("unprepared_documents")
            )
            phase = "ready_ack"
            knowledge_progress(phase, "start")
            self.ack(
                job,
                str(actual["source_revision"]),
                "Some current document associations still lack proven passages."
                if not complete
                else "",
                products=products,
                preparation_complete=complete,
                unprepared_documents=actual.get("unprepared_documents", []),
                materialization_complete=(
                    actual.get("materialization_complete") is True
                    and not any(
                        row.get("reason") == "document_unparsed"
                        for row in actual.get("unprepared_documents", [])
                    )
                ),
                index_version=version,
                loaded_recipe_revision=actual.get("recipe_revision", ""),
                serving_revision=actual.get("serving_revision", ""),
                loaded_model_identity_revision=actual.get(
                    "model_identity_revision", ""
                ),
            )
        except (
            Exception,
            SystemExit,
        ) as error:  # safe failure, including the native publish CLI
            # No request URL, auth header or exception repr enters Woo/logs.
            report_failure(phase, error)
            if (
                self._published
                or recovering
                or isinstance(error, ActivationOutcomeUnconfirmed)
                or isinstance(error, PreActivationDeferred)
            ):
                # The lost remote process might still pass its in-lock native
                # verification, or an ACK response may be lost after activation.
                # Preserve the original lease for fresh same-owner ACK recovery.
                raise
            try:
                self.ack(job, "", "knowledge preparation or loaded verification failed")
            except (Exception, SystemExit) as ack_error:
                # A transport or stale-job error can leave the job preparing.
                # Keep the original failure and separately expose the ack result.
                report_failure("failure_ack", ack_error)
            raise
        finally:
            self._active_job = None
        return True

    def close(self) -> None:
        self.client.close()


def run_job(
    worker: Worker,
    prepare: Callable[[dict[str, Any]], str],
    loaded: Callable[[], dict[str, Any]],
    index_dir: Path,
    *,
    resume_pending: bool = False,
) -> bool:
    """Own one build through loaded/ack and roll back its rebuildable output."""
    ledger = index_dir / "publication-worker-pending.json"
    if ledger.is_file() and not resume_pending:
        pending = json.loads(ledger.read_text())
        if pending.get("deferred_until", 0) > time.time():
            raise RuntimeError("a deferred generation awaits same-lease review")
    if not resume_pending:
        discard_pending(index_dir)
    deferred = False
    try:
        completed = worker.one(prepare, loaded)
        if completed:
            prepared = pending_build(index_dir)
            if prepared is not None:
                retain_builds(index_dir, prepared)
                (index_dir / "publication-worker-pending.json").unlink(missing_ok=True)
        return completed
    except PreActivationDeferred as error:
        pending = json.loads(ledger.read_text())
        pending["deferred_until"] = error.lease_expires_at
        ledger.write_text(json.dumps(pending))
        deferred = True
        raise
    except NativeVerificationRejected as error:
        if error.reason == "retry_exhausted":
            try:
                retain_review_build(index_dir, error)
            except (Exception, SystemExit) as retention_error:
                report_failure("review_retention", retention_error)
        raise
    finally:
        # Includes build/publish failure, not just failures after a Path returns.
        # A killed process is recovered by the next locked invocation.
        if not deferred and not resume_pending:
            discard_pending(index_dir)


def main(
    argv: Sequence[str] | None = None,
    *,
    publisher: Any = publish,
    worker_factory: Any = Worker,
    embedding_factory: Callable[[str], Embedder] = build.document_embedder,
    busy_exit: int = 0,
    resume_index: dict[str, Any] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rest-config", type=Path, default=inventory.DEFAULT_REST_CONFIG
    )
    parser.add_argument("--worker-id", required=True)
    parser.add_argument(
        "--lease-seconds",
        required=True,
        type=int,
        help="Lease selected from this build machine's measured worst-case build budget",
    )
    parser.add_argument(
        "--host", help="SSH alias of the Genie host; omit for local rehearsal"
    )
    parser.add_argument("--root", default="/opt/linker-genie/index")
    parser.add_argument(
        "--loaded-url",
        required=True,
        help="Private service loopback /knowledge/loaded; --host checks it over the same SSH alias",
    )
    args = parser.parse_args(argv)
    if args.lease_seconds <= 0:
        parser.error("--lease-seconds must be positive")
    if sys.platform != "darwin":
        parser.error("knowledge preparation runs on the Mac build machine")
    jobs = os.environ["LINKER_PUBLICATION_JOBS_URL"]
    user, password = (
        os.environ["LINKER_PUBLICATION_USER"],
        os.environ["LINKER_PUBLICATION_PASSWORD"],
    )
    token = os.environ["GENIE_SERVICE_TOKEN"]
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    # launchd already serializes a job; this also prevents a manual run racing it.
    with (INDEX_DIR / "publication-worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return busy_exit
        worker = worker_factory(
            jobs, user, password, args.worker_id, args.lease_seconds
        )

        def prepare(manifest: dict[str, Any]) -> str:
            phase = "inventory_source"
            phase_started = time.monotonic()
            knowledge_progress(phase, "start")

            def stage(next_phase: str) -> None:
                nonlocal phase, phase_started
                knowledge_progress(
                    phase, "done", seconds=time.monotonic() - phase_started
                )
                knowledge_progress(next_phase, "start")
                phase, phase_started = next_phase, time.monotonic()

            try:
                if resume_index is not None:
                    directory = validated_pending(
                        INDEX_DIR, worker.activation(), resume_index
                    )
                    stage("publish")
                    activation = worker.activation()
                    activation.update(loaded_url=args.loaded_url, service_token=token)
                    report = publisher(
                        directory, args.root, args.host, activation=activation
                    )
                    worker.publication_confirmed()
                    stage("complete")
                    return str(report["index_version"])
                source = inventory.RestClient(args.rest_config)
                # Prevent an operator accidentally building one site and acking another.
                if urlsplit(source.base).netloc != urlsplit(jobs).netloc:
                    raise RuntimeError(
                        "inventory and publication queue belong to different sites"
                    )
                stage("inventory")
                fetch_inventory(source, INVENTORY_PATH, PDF_DIR, manifest)
                stage("parse")
                parse.run(INVENTORY_PATH, PDF_DIR, PARSED_DIR, parse.WORKERS)
                stage("language_setup")
                import py3langid

                from index.tokenizer import HFTokenizer

                stage("embedding_setup")
                embedder = embedding_factory(build.DEFAULT_MODEL)
                stage("tokenizer_setup")
                tokenizer = HFTokenizer.from_pretrained(build.CHUNK_TOKENIZER)
                stage("build")
                directory = build.build(
                    INVENTORY_PATH,
                    PDF_DIR,
                    PARSED_DIR,
                    INDEX_DIR,
                    embedder,
                    tokenizer,
                    lambda text: str(py3langid.classify(text)[0]),
                    activation_epoch=worker.activation()["epoch"],
                    publication_deadline=worker.lease_expiry(),
                    publication_lease=worker.activation(),
                    on_created=lambda directory: record_build(INDEX_DIR, directory),
                )
                stage("activation")
                activation = worker.activation()
                activation.update(loaded_url=args.loaded_url, service_token=token)
                stage("publish")
                report = publisher(
                    directory, args.root, args.host, activation=activation
                )
                worker.publication_confirmed()
                stage("complete")
                return str(report["index_version"])
            except (Exception, SystemExit) as error:
                knowledge_progress(
                    phase, "failed", seconds=time.monotonic() - phase_started
                )
                report_failure(f"prepare.{phase}", error)
                raise

        def loaded() -> dict[str, Any]:
            # The serving process reopens the resolved current file under the same
            # search lock, so a changed symlink alone never satisfies this check.
            return read_loaded(args.loaded_url, token, args.host)

        try:
            run_job(
                worker,
                prepare,
                loaded,
                INDEX_DIR,
                resume_pending=resume_index is not None,
            )
        except (Exception, SystemExit) as error:  # noqa: BLE001 - safe status, no private URLs or credentials
            report_failure("run_job", error)
            print(
                "Knowledge publication needs verification; inspect the native job "
                "and loaded generation.",
                file=sys.stderr,
            )
            return 1
        finally:
            worker.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
