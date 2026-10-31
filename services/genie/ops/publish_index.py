"""Publish a built index, or roll back to the previous one (docs/specs/10-knowledge-index.md).

    uv run python ops/publish_index.py publish <build dir> [--host user@vps] [--root DIR]
    uv run python ops/publish_index.py rollback [--host user@vps] [--root DIR]
    uv run python ops/publish_index.py status [--host user@vps] [--root DIR]

Without --host the root is a directory on this machine: the local rehearsal of the
VPS layout. With --host the same `index_release.py` runs on the VPS over ssh and the
files go up with rsync. The service reads `<root>/current/index.sqlite`.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from index_release import _sha256

RELEASE_SCRIPT = Path(__file__).with_name("index_release.py")
# The VPS layout of the spec (Build 5); `linker_genie.retrieval.DEFAULT_INDEX` reads it.
DEFAULT_ROOT = "/opt/linker-genie/index"
# Three 30-second native verifications, two backoffs and one 30-second loaded
# readback leave 57 seconds for SSH, the activation lock and index hashing.
ACTIVATION_TIMEOUT = 180


class ActivationOutcomeUnconfirmed(RuntimeError):
    """The remote switch may still complete; its Woo lease must not be released."""


class NativeVerificationRejected(RuntimeError):
    """The remote command reported a definite in-lock rejection before journaling."""

    def __init__(
        self,
        reason: str,
        status: int | None,
        transport: bool,
        identity: dict[str, Any],
    ) -> None:
        super().__init__("native Woo lease verification rejected")
        self.reason, self.status, self.transport = reason, status, transport
        self.identity = identity
        self.cleanup_unconfirmed = False


def _native_rejection(
    error: subprocess.CalledProcessError,
    args: tuple[str, ...],
    activation: dict[str, Any],
) -> NativeVerificationRejected | None:
    """Accept only the exact bounded rejection emitted by our remote command."""
    if (
        error.returncode != 72
        or len(args) != 4
        or args[0] != "activate"
        or not isinstance(error.stderr, str)
        or len(error.stderr) > 4096
    ):
        return None
    try:
        value = json.loads(error.stderr)
    except ValueError:
        return None
    keys = {
        "result",
        "reason",
        "http_status",
        "transport",
        "job_id",
        "source_revision",
        "model_identity_revision",
        "recipe_revision",
        "epoch",
    }
    if not isinstance(value, dict) or set(value) != keys:
        return None
    if (
        value.get("result") != "native_verify_rejected"
        or type(value.get("epoch")) is not int
        or type(activation.get("epoch")) is not int
        or value["epoch"] != activation["epoch"]
        or value["epoch"] < 1
        or any(
            not isinstance(activation.get(name), str)
            or not activation[name]
            or value.get(name) != activation[name]
            for name in (
                "job_id",
                "source_revision",
                "recipe_revision",
                "model_identity_revision",
            )
        )
        or type(value.get("transport")) is not bool
    ):
        return None
    reason, status, transport = (
        value["reason"],
        value["http_status"],
        value["transport"],
    )
    if not isinstance(reason, str):
        return None
    if reason == "retry_exhausted":
        valid = (type(status) is int and status == 503 and not transport) or (
            status is None and transport
        )
    elif reason == "http_rejected":
        valid = (
            type(status) is int
            and 100 <= status <= 599
            and status != 503
            and not transport
        )
    else:
        valid = (
            reason in {"expired", "response_identity", "invalid_response"}
            and status is None
            and not transport
        )
    if not valid:
        return None
    identity = {
        "job_id": value["job_id"],
        "source_revision": value["source_revision"],
        "model_identity_revision": value["model_identity_revision"],
        "recipe_revision": value["recipe_revision"],
        "serving_revision": activation.get("serving_revision"),
        "activation_epoch": value["epoch"],
        "version": args[2],
        "sha256": args[3],
    }
    return NativeVerificationRejected(reason, status, transport, identity)


def release(
    host: str | None,
    *args: str,
    activation: dict[str, Any] | None = None,
    owner_token: str | None = None,
    timeout: float | None = None,
) -> dict[str, object]:
    """Run index_release.py with `args` on the host (or here) and return its report."""
    if owner_token is not None:
        discard = len(args) == 3 and args[0] == "discard" and activation is None
        validate = len(args) == 4 and args[0] == "validate"
        if not owner_token or not (discard or validate):
            raise ValueError("invalid upload owner request")
    if activation is not None or owner_token is not None:
        arguments = [
            *args,
            "--owner-stdin" if owner_token is not None else "--activation-stdin",
        ]
        private_input: dict[str, Any] | None
        if owner_token is not None:
            private_input = {"owner_token": owner_token}
            if args[0] == "validate":
                private_input["activation"] = activation
        else:
            private_input = activation
        command = (
            [sys.executable, str(RELEASE_SCRIPT), *arguments]
            if host is None
            else [
                "ssh",
                host,
                "python3 -c "
                + shlex.quote(RELEASE_SCRIPT.read_text(encoding="utf-8"))
                + " "
                + shlex.join(arguments),
            ]
        )
        try:
            result = subprocess.run(
                command,
                input=json.dumps(private_input),
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as error:
            rejected = (
                _native_rejection(error, args, activation)
                if activation is not None
                else None
            )
            if rejected is not None:
                raise rejected from None
            raise
    elif host is None:
        command = [sys.executable, str(RELEASE_SCRIPT), *args]
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout
        )
    else:
        command = ["ssh", host, "python3", "-", *args]
        result = subprocess.run(
            command,
            input=RELEASE_SCRIPT.read_text(encoding="utf-8"),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    report = json.loads(result.stdout)
    if not isinstance(report, dict):
        raise ValueError("invalid index release report")
    return report


def _confirmed_activation(
    report: dict[str, object],
    version: str,
    sha256: str,
    activation: dict[str, Any],
) -> bool:
    """Only a matching current index and complete durable fence prove a switch."""
    expected = {
        "site": str(activation.get("verify_url", "")),
        "consumer": "knowledge",
        "epoch": activation.get("epoch"),
        "job_id": activation.get("job_id"),
        "source_revision": activation.get("source_revision"),
        "model_identity_revision": activation.get("model_identity_revision"),
        "recipe_revision": activation.get("recipe_revision"),
        "serving_revision": activation.get("serving_revision"),
        "index_version": version,
        "sha256": sha256,
    }
    fence = report.get("activation")
    return (
        report.get("current") == version
        and report.get("index_version") == version
        and report.get("sha256_ok") is True
        and report.get("sha256") == sha256
        and type(activation.get("epoch")) is int
        and isinstance(fence, dict)
        and type(fence.get("epoch")) is int
        and fence == expected
    )


def _inspect_activation(
    host: str | None,
    root: str,
    version: str,
    sha256: str,
    activation: dict[str, Any],
) -> dict[str, object]:
    try:
        observed = release(host, "status", root, "--locked", timeout=30)
    except (OSError, ValueError, subprocess.SubprocessError):
        observed = {}
    if not _confirmed_activation(observed, version, sha256, activation):
        raise ActivationOutcomeUnconfirmed("index activation outcome unconfirmed")
    return observed


def publish(
    build_dir: Path,
    root: str,
    host: str | None,
    *,
    activation: dict[str, Any] | None = None,
    before_activate: Callable[[], None] | None = None,
) -> dict[str, object]:
    """Upload and activate; an optional runtime switch follows verified upload.

    The hook runs once, after the host validates this upload's owner, actual
    SQLite/manifest bytes and identities, while current still serves the prior
    index. The caller owns its runtime change and recovery. Activation repeats
    validation and native verification; an ambiguous activation is inspected,
    never replayed. Without a hook the ordinary publication entry is unchanged.
    """
    manifest = json.loads((build_dir / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest["version"])
    expected = str(manifest["file"]["sha256"])
    if _sha256(build_dir / str(manifest["file"]["name"])) != expected:
        raise SystemExit(f"{build_dir}: index.sqlite does not match its manifest")
    prepared = release(
        host, "prepare", root, version, "--reuse-basis", activation=activation
    )
    incoming = str(prepared["incoming"])
    owner_token = str(prepared["owner_token"])
    basis = prepared.get("basis")
    basis = basis if isinstance(basis, str) else None
    target = incoming if host is None else f"{host}:{incoming}"
    discard_upload = True
    try:
        # SQLite still contains compressible text around cached vector pages;
        # stream it through rsync without creating another compressed artifact.
        upload = ["rsync", "-a", "--compress"]
        if basis is not None:
            # Native prepare seeded an independent owned target. checksum
            # rejects equal-size/mtime changes; no-whole-file enables actual
            # delta matching for both local rehearsals and remote uploads.
            upload += [
                "--checksum",
                "--no-whole-file",
                "--stats",
            ]
        subprocess.run(
            upload
            + [
                str(build_dir / "index.sqlite"),
                str(build_dir / "manifest.json"),
                f"{target}/",
            ],
            check=True,
        )
        if before_activate is not None:
            validated = release(
                host,
                "validate",
                root,
                version,
                expected,
                activation=activation,
                owner_token=owner_token,
            )
            if (
                validated.get("validated") is not True
                or validated.get("index_version") != version
                or validated.get("sha256") != expected
            ):
                raise RuntimeError("host has not verified the owned index upload")
            before_activate()
        try:
            report = release(
                host,
                "activate",
                root,
                version,
                expected,
                activation=activation,
                timeout=ACTIVATION_TIMEOUT if activation is not None else None,
            )
            # Activation renamed the incoming directory; no cleanup SSH call is
            # needed and a cleanup failure must not mask a successful switch.
            discard_upload = False
            if activation is not None and not _confirmed_activation(
                report, version, expected, activation
            ):
                report = _inspect_activation(host, root, version, expected, activation)
        except NativeVerificationRejected as error:
            # This bounded, identity-checked response is emitted before journal
            # or switch; an owned upload can be discarded without losing proof.
            discard_upload = False
            try:
                release(host, "discard", root, version, owner_token=owner_token)
            except (OSError, ValueError, subprocess.SubprocessError):
                error.cleanup_unconfirmed = True
            raise
        except (OSError, ValueError, subprocess.SubprocessError):
            if activation is None:
                raise
            # The SSH command can fail after the remote switch. Never replay it.
            # An unconfirmed upload stays owned until native expiry/pruning, so
            # a still-running command or a journal recovery target survives.
            discard_upload = False
            report = _inspect_activation(host, root, version, expected, activation)
    finally:
        if discard_upload:
            release(host, "discard", root, version, owner_token=owner_token)
    if (
        report.get("current") != version
        or report.get("index_version") != version
        or not report.get("sha256_ok")
        or (
            activation is not None
            and not _confirmed_activation(report, version, expected, activation)
        )
    ):
        raise SystemExit(f"published {version}, but the host reports {report}")
    report["transfer_basis"] = {
        "path": basis,
        "reason": prepared.get("basis_reason", "not_provided"),
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish or roll back the document index."
    )
    parser.add_argument("command", choices=["publish", "rollback", "status"])
    parser.add_argument("build_dir", nargs="?", type=Path)
    parser.add_argument(
        "--host", default=None, help="ssh destination; omit for a local root"
    )
    parser.add_argument("--root", default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    if args.command == "publish":
        if args.build_dir is None:
            parser.error("publish needs the build directory")
        report = publish(args.build_dir, args.root, args.host)
    else:
        report = release(args.host, args.command, args.root)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
