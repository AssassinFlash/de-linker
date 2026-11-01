"""Publish a prepared Genie runtime with one native knowledge generation.

No staging, dependency installation, Engine action or scheduler management occurs.
Run from the final immutable Mac source, with the existing scheduler paused.
A private journal retains only the exact lease for ACK recovery, never account keys.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import runpy
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from linker_genie.embedding import Embedder, Passage

if __package__ in {None, ""} and "__file__" in globals():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

UNITS = ("linker-genie.service", "linker-genie-judge.service")


class CachedEmbedder:
    """The complete native encoder interface, refusing every computed vector."""

    def __init__(self, underlying: Embedder) -> None:
        self.fingerprint = underlying.fingerprint
        self.model = underlying.model
        self.dimensions = underlying.dimensions

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        raise RuntimeError("paired cached-only release refused missing embeddings")

    def embed_query(self, text: str) -> bytes:
        raise RuntimeError("paired cached-only release refused query embedding")


def running(root: Path, version: str) -> dict[str, int]:
    """Prove both actual processes run from the selected immutable release."""
    result = {}
    for unit in UNITS:
        observed = subprocess.run(
            ["systemctl", "show", unit, "--property=MainPID,ActiveState,SubState"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        fields = dict(
            line.split("=", 1) for line in observed.stdout.splitlines() if "=" in line
        )
        pid = int(fields.get("MainPID", "0"))
        if (
            fields.get("ActiveState") != "active"
            or fields.get("SubState") != "running"
            or pid < 1
        ):
            raise RuntimeError("Genie process is not running")
        if Path(f"/proc/{pid}/cwd").resolve(strict=True) != (root / version).resolve():
            raise RuntimeError("Genie process cwd differs from the selected runtime")
        result[unit] = pid
    return result


def identity(source: Path) -> dict[str, str]:
    """Measure source bytes, independent of deployment metadata or a live index."""
    return {
        "recipe": runpy.run_path(str(source / "index/preparation.py"))[
            "recipe_revision"
        ](source),
        "serving": runpy.run_path(str(source / "src/linker_genie/preparation.py"))[
            "serving_revision"
        ](source),
    }


def remote(request: dict[str, Any]) -> dict[str, Any]:
    """Stdlib-only VPS operation; current is changed only under selector CAS."""
    root = Path(request["runtime_root"])
    candidate, previous = request["candidate"], request["previous"]
    for name in (candidate, previous):
        if not isinstance(name, str) or not re.fullmatch(
            r"[0-9]{8}T[0-9]{12}Z(?:-[0-9a-f]{8,40})?", name
        ):
            raise ValueError("invalid prepared runtime version")
    if not root.is_absolute() or root.is_symlink() or candidate == previous:
        raise ValueError("invalid runtime root or pair")
    for name in (candidate, previous):
        source = root / name
        if source.is_symlink() or not source.is_dir():
            raise ValueError("prepared runtime must be an existing real directory")
        if not (source / ".venv/bin/python").is_file():
            raise ValueError("prepared runtime has no installed interpreter")
    measured = identity(root / candidate)
    if measured != request["identity"]:
        raise ValueError("prepared VPS runtime differs from the final Mac source")
    selector = root / "current"
    if not selector.is_symlink():
        raise ValueError("runtime selector must be a symlink")

    def selected() -> str:
        target = selector.resolve(strict=True)
        if target.parent != root.resolve() or target.name not in (previous, candidate):
            raise RuntimeError("runtime selector changed outside the expected pair")
        return target.name

    if request["action"] == "status":
        return {"current": selected(), **measured}
    if request["action"] not in {"activate", "restore"}:
        raise ValueError("unknown runtime action")
    with (root / ".paired-release.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        live = selected()
        target = candidate if request["action"] == "activate" else previous
        if live == target and request["action"] == "activate":
            return {"current": live, "pids": running(root, live), **measured}
        # The prepared unit definitions must continue to execute the selector,
        # not an old absolute release or an unrelated service.
        for unit in UNITS:
            result = subprocess.run(
                ["systemctl", "show", unit, "--property=ExecStart", "--value"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if str(root / "current") + "/.venv/bin/" not in result.stdout:
                raise RuntimeError("Genie unit does not execute this runtime selector")
            if request["action"] == "activate":
                subprocess.run(
                    ["systemctl", "is-active", "--quiet", unit], check=True, timeout=10
                )
        subprocess.run(["systemctl", "stop", *UNITS], check=True, timeout=45)
        temporary = root / f".paired-current-{os.getpid()}"
        try:
            temporary.symlink_to(target)
            os.replace(temporary, selector)
        finally:
            temporary.unlink(missing_ok=True)
        subprocess.run(["systemctl", "start", *UNITS], check=True, timeout=45)
        for unit in UNITS:
            subprocess.run(
                ["systemctl", "is-active", "--quiet", unit], check=True, timeout=10
            )
        if identity(root / candidate) != measured:
            raise RuntimeError("prepared source changed during runtime selection")
        return {"current": selected(), "pids": running(root, target), **measured}


class Runtime:
    def __init__(self, host: str, request: dict[str, Any]) -> None:
        self.host, self.request = host, request

    def call(self, action: str) -> dict[str, Any]:
        # Ship this reviewed stdlib helper in memory. No remote file, credential
        # argument, persistent tunnel or dependency installation is introduced.
        program = Path(__file__).read_text()
        command = "python3 -c " + shlex.quote(program) + " --remote"
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "--", self.host, command],
            input=json.dumps({**self.request, "action": action}),
            capture_output=True,
            text=True,
            check=False,
            timeout=150,
        )
        if result.returncode:
            raise RuntimeError(
                f"runtime.{action} failed; inspect exact selector and Genie unit state"
            )
        value: dict[str, Any] = json.loads(result.stdout)
        if value.get("current") not in {
            self.request["candidate"],
            self.request["previous"],
        }:
            raise RuntimeError("invalid remote runtime receipt")
        return value


def save(path: Path, value: dict[str, Any]) -> None:
    """One bounded private lease journal; never overwrite another task's file."""
    temporary = path.with_suffix(path.suffix + ".next")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_native_ready(host: str, wp_root: str) -> dict[str, Any]:
    """Privileged existing SSH/WP-CLI read, projecting no lease capability."""
    php = r"""<?php
$state = get_option(\Linker\Commerce\Products\Publication\PreparationJobs::OPTION, array());
$job = $state['knowledge'] ?? array();
$keys = array('job_id','worker_id','status','source_revision','model_identity_revision',
 'recipe_revision','loaded_revision','loaded_model_identity_revision','loaded_recipe_revision',
 'index_version','activation_epoch','loaded_activation_epoch','expected_serving_revision',
 'serving_revision','lease_expires_at','loaded_products','materialization_complete',
 'preparation_complete','unprepared_documents');
$manifest = \Linker\Commerce\Products\Publication::manifest();
echo wp_json_encode(array('job'=>array_intersect_key($job,array_flip($keys)),
 'lease_token_present'=>isset($job['lease_token']),
 'current_source'=>$manifest['source_revision'],
 'current_model_identity'=>$manifest['model_identity_revision']));
"""
    command = shlex.join(["/usr/local/bin/wp", "--path=" + wp_root, "eval-file", "-"])
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "--", host, command],
        input=php,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    if result.returncode:
        raise RuntimeError("native_ready SSH/WP readback failed")
    value: dict[str, Any] = json.loads(result.stdout)
    return value


def validate_ready(
    state: dict[str, Any], proof: dict[str, Any], loaded: dict[str, Any]
) -> None:
    """An expired capability/409 is never evidence; compare durable native ACK."""
    job, acknowledged = state["job"], proof.get("job", {})
    identities = state["request"]["identity"]
    expected = {
        "job_id": job["job_id"],
        "worker_id": state["worker_id"],
        "status": "ready",
        "source_revision": job["source_revision"],
        "loaded_revision": job["source_revision"],
        "model_identity_revision": job["model_identity_revision"],
        "loaded_model_identity_revision": job["model_identity_revision"],
        "recipe_revision": identities["recipe"],
        "loaded_recipe_revision": identities["recipe"],
        "expected_serving_revision": identities["serving"],
        "serving_revision": identities["serving"],
        "activation_epoch": job["activation_epoch"],
        "loaded_activation_epoch": job["activation_epoch"],
        "index_version": state["index"]["version"],
        "lease_expires_at": 0,
    }
    actual_expected = {
        key: expected[key]
        for key in (
            "source_revision",
            "model_identity_revision",
            "recipe_revision",
            "expected_serving_revision",
            "serving_revision",
            "activation_epoch",
            "index_version",
        )
    }
    if (
        proof.get("lease_token_present") is not False
        or proof.get("current_source") != job["source_revision"]
        or proof.get("current_model_identity") != job["model_identity_revision"]
        or any(acknowledged.get(key) != value for key, value in expected.items())
        or any(loaded.get(key) != value for key, value in actual_expected.items())
    ):
        raise RuntimeError(
            "durable native ready identity differs from this exact release"
        )
    products = {
        str(row["product_id"]): row["product_revision"] for row in loaded["products"]
    }
    native_products = acknowledged.get("loaded_products")
    if native_products == []:
        native_products = {}
    if products != native_products:
        raise RuntimeError(
            "durable native ready products differ from actual loaded products"
        )
    for key in (
        "materialization_complete",
        "preparation_complete",
        "unprepared_documents",
    ):
        if acknowledged.get(key) != loaded.get(key):
            raise RuntimeError(
                "durable native ready coverage differs from actual loaded coverage"
            )
    if loaded.get("materialization_complete") is not True:
        raise RuntimeError("actual loaded generation is not materialized")


class RuntimeControl(Protocol):
    def call(self, action: str) -> dict[str, Any]: ...


class PairedPublisher:
    def __init__(
        self, runtime: RuntimeControl, journal: Path, state: dict[str, Any], loaded: Any
    ) -> None:
        self.runtime, self.journal, self.state = runtime, journal, state
        self.loaded = loaded

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        from publish_index import (
            ActivationOutcomeUnconfirmed,
            NativeVerificationRejected,
            publish,
        )

        hook_returned = False
        manifest = json.loads((Path(args[0]) / "manifest.json").read_text())
        self.state["index"] = {
            "version": manifest["version"],
            "sha256": manifest["file"]["sha256"],
        }
        save(self.journal, self.state)

        def switch() -> None:
            nonlocal hook_returned
            self.state["phase"] = "runtime_switch"
            save(self.journal, self.state)
            self.runtime.call("activate")
            # Persist before publish can send any activation request. An
            # interrupted/lost response is now conservative, never rolled back.
            self.state["phase"] = "activation_possible"
            save(self.journal, self.state)
            hook_returned = True

        try:
            result: dict[str, Any] = publish(*args, **kwargs, before_activate=switch)
        except BaseException as error:
            if not hook_returned or isinstance(error, NativeVerificationRejected):
                self.runtime.call("restore")
                if self.loaded() != self.state["before_loaded"]:
                    raise RuntimeError(
                        "old runtime restored but old loaded pair is unconfirmed"
                    ) from error
                self.state["phase"] = "restored_before_activation"
                save(self.journal, self.state)
            raise
        self.state["phase"] = "activated"
        try:
            save(self.journal, self.state)
        except OSError as error:
            raise ActivationOutcomeUnconfirmed(
                "activation confirmed; lease journal update failed"
            ) from error
        return result


def main(argv: list[str] | None = None) -> int:
    from install_publication_worker import load_private_environment

    env_parser = argparse.ArgumentParser(add_help=False)
    env_parser.add_argument("--env-file", type=Path)
    env_args, _ = env_parser.parse_known_args(argv)
    if env_args.env_file is not None:
        load_private_environment(env_args.env_file)
    import publication_worker as worker_module
    from index import build, inventory
    from linker_genie.preparation import RUNTIME_SERVING_REVISION

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Existing mode-0600 worker environment; never printed",
    )
    parser.add_argument(
        "command", choices=["preflight", "publish", "resume-ack", "confirm-ready"]
    )
    parser.add_argument(
        "--wp-host", help="Existing privileged WordPress SSH alias; confirm-ready only"
    )
    parser.add_argument(
        "--wp-root", help="Verified existing WordPress root; confirm-ready only"
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--runtime-root", default="/opt/linker-genie")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--loaded-url", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--lease-seconds", type=int, default=7200)
    parser.add_argument(
        "--rest-config", type=Path, default=inventory.DEFAULT_REST_CONFIG
    )
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1]
    measured = identity(source)
    if measured["serving"] != RUNTIME_SERVING_REVISION:
        raise RuntimeError("imported runtime does not belong to this Mac source")
    request = {
        "runtime_root": args.runtime_root,
        "candidate": args.candidate,
        "previous": args.previous,
        "identity": measured,
    }
    runtime = Runtime(args.host, request)
    selected = runtime.call("status")
    if args.command == "preflight":
        print(json.dumps(selected))
        return 0
    if not args.journal.is_absolute() or not args.journal.parent.is_dir():
        raise ValueError("lease journal needs an existing private absolute parent")
    if args.journal.parent.stat().st_mode & 0o077:
        raise ValueError("lease journal parent must be private")
    state: dict[str, Any] = {
        "request": request,
        "host": args.host,
        "worker_id": args.worker_id,
        "phase": "prepared",
    }
    if args.command == "publish":
        if args.journal.exists() or selected["current"] != args.previous:
            raise RuntimeError(
                "publish requires a new journal and the original selector"
            )
    else:
        if args.journal.is_symlink() or args.journal.stat().st_mode & 0o077:
            raise ValueError("lease journal must be a private regular file")
        state = json.loads(args.journal.read_text())
        if any(
            state.get(k) != v
            for k, v in (
                ("request", request),
                ("host", args.host),
                ("worker_id", args.worker_id),
            )
        ):
            raise RuntimeError("ACK recovery belongs to a different release")
        if selected["current"] != args.candidate or state.get("phase") not in {
            "activation_possible",
            "activated",
            "ready",
        }:
            raise RuntimeError(
                "ACK recovery requires the selected candidate and inspected activation"
            )

    if args.command == "confirm-ready":
        from publish_index import _inspect_activation

        if not args.wp_host or not args.wp_root or not Path(args.wp_root).is_absolute():
            raise ValueError(
                "confirm-ready requires the privileged WP SSH alias and absolute root"
            )
        jobs = os.environ["LINKER_PUBLICATION_JOBS_URL"].rstrip("/")
        activation = {
            "verify_url": jobs + "/claim",
            "epoch": state["job"]["activation_epoch"],
            "job_id": state["job"]["job_id"],
            "source_revision": state["job"]["source_revision"],
            "model_identity_revision": state["job"]["model_identity_revision"],
            "recipe_revision": measured["recipe"],
            "serving_revision": measured["serving"],
        }
        proof = read_native_ready(args.wp_host, args.wp_root)
        loaded = worker_module.read_loaded(
            args.loaded_url, os.environ["GENIE_SERVICE_TOKEN"], args.host
        )
        _inspect_activation(
            args.host,
            str(Path(args.runtime_root) / "index"),
            state["index"]["version"],
            state["index"]["sha256"],
            activation,
        )
        validate_ready(state, proof, loaded)
        if (
            read_native_ready(args.wp_host, args.wp_root) != proof
            or runtime.call("status")["current"] != args.candidate
        ):
            raise RuntimeError(
                "native ready proof or runtime selector changed during confirmation"
            )
        args.journal.unlink()
        print("paired_release native_ready_confirmed=true")
        return 0

    class ReleaseWorker(worker_module.Worker):
        def claim(
            self,
            loaded_receipt: dict[str, Any] | None = None,
            loaded_unavailable: bool = False,
        ) -> dict[str, Any] | None:
            if args.command == "resume-ack":
                # Verify the recorded exact lease; never call ordinary claim,
                # which could mint a replacement job after expiry/source change.
                job: dict[str, Any] = state["job"]
                self._active_job = job
                activation = self.activation()
                response = self.client.post(
                    self.jobs + "/claim", json=activation["verify_body"]
                )
                response.raise_for_status()
                if response.json().get("verified") is not True:
                    raise RuntimeError("same native lease is no longer available")
                from publish_index import _inspect_activation

                activation.update(
                    loaded_url=args.loaded_url,
                    service_token=os.environ["GENIE_SERVICE_TOKEN"],
                )
                _inspect_activation(
                    args.host,
                    str(Path(args.runtime_root) / "index"),
                    state["index"]["version"],
                    state["index"]["sha256"],
                    activation,
                )
                return {**job, "ack_only": True}
            if loaded_unavailable or loaded_receipt is None:
                raise RuntimeError(
                    "paired release requires the actual original loaded pair"
                )
            next_job = super().claim(loaded_receipt, loaded_unavailable)
            if next_job is not None:
                state["before_loaded"] = loaded_receipt
                state["job"] = next_job
                save(args.journal, state)
            return next_job

        def ack(
            self, job: dict[str, Any], loaded: str, *values: Any, **fields: Any
        ) -> None:
            super().ack(job, loaded, *values, require_complete=bool(loaded), **fields)
            if loaded:
                state["phase"] = "ready"
                save(args.journal, state)

    def cached_embedder(model: str) -> Embedder:
        return CachedEmbedder(build.document_embedder(model))

    worker_args = [
        "--host",
        args.host,
        "--root",
        str(Path(args.runtime_root) / "index"),
        "--loaded-url",
        args.loaded_url,
        "--worker-id",
        args.worker_id,
        "--lease-seconds",
        str(args.lease_seconds),
        "--rest-config",
        str(args.rest_config),
    ]
    if args.command == "publish":
        save(args.journal, state)
    result = worker_module.main(
        worker_args,
        publisher=PairedPublisher(
            runtime,
            args.journal,
            state,
            lambda: worker_module.read_loaded(
                args.loaded_url, os.environ["GENIE_SERVICE_TOKEN"], args.host
            ),
        ),
        worker_factory=ReleaseWorker,
        embedding_factory=cached_embedder,
        busy_exit=1,
    )
    if (
        result == 0
        and state.get("phase") == "ready"
        and runtime.call("status")["current"] == args.candidate
    ):
        args.journal.unlink(missing_ok=True)
    else:
        result = 1
        print(
            "Paired release incomplete: retain journal; inspect activation before recovery.",
            file=sys.stderr,
        )
    return result


if __name__ == "__main__":
    if sys.argv[1:] == ["--remote"]:
        try:
            print(json.dumps(remote(json.load(sys.stdin))))
        except Exception:
            # No subprocess output, environment or secret capability is emitted.
            sys.exit(1)
    else:
        try:
            sys.exit(main())
        except Exception as error:
            from publication_worker import report_failure

            report_failure("paired_release", error)
            print(
                f"paired_release error={type(error).__name__}; inspect private journal and native selector",
                file=sys.stderr,
            )
            sys.exit(1)
