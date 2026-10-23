"""One automatic Mac knowledge preparation job, claimed from Woo's durable queue.

Runs under launchd (install_publication_worker.py). Heavy parsing stays on the Mac.
The worker never grants publication: late jobs are rejected by Woo and every
runtime read independently checks current permission. Credentials are env-only.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
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
from index.publication import inventory as fetch_inventory  # noqa: E402
from linker_genie.publication import Snapshot  # noqa: E402
from publish_index import publish  # noqa: E402

_LOADED_PROGRAM = """import json, sys, urllib.request
try:
    data = json.load(sys.stdin)
    request = urllib.request.Request(data['url'], data=b'{}', method='POST', headers={
        'Content-Type': 'application/json', 'X-Linker-Service-Token': data['token']})
    with urllib.request.urlopen(request, timeout=20) as response:
        loaded = json.load(response)
    print(json.dumps({key: loaded[key] for key in ('index_version', 'source_revision', 'products')}))
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
    ) -> None:
        self.jobs = jobs_url.rstrip("/")
        self.worker_id, self.lease = worker_id, lease_seconds
        self.client = httpx.Client(
            auth=(user, password),
            timeout=120,
            transport=transport,
            headers={"Cache-Control": "no-cache"},
        )

    def claim(self) -> dict[str, Any] | None:
        response = self.client.post(
            self.jobs + "/claim",
            json={
                "consumer": "knowledge",
                "worker_id": self.worker_id,
                "lease_seconds": self.lease,
            },
        )
        response.raise_for_status()
        job: dict[str, Any] | None = response.json()["job"]
        return job

    def ack(
        self,
        job: dict[str, Any],
        loaded: str,
        error: str = "",
        products: list[dict[str, Any]] | None = None,
    ) -> None:
        response = self.client.post(
            self.jobs + "/ack",
            json={
                "job_id": job["job_id"],
                "lease_token": job["lease_token"],
                "source_revision": job["source_revision"],
                "loaded_revision": loaded,
                "status": "ready" if loaded else "failed",
                "error": error,
                "prepared_products": products or [],
            },
        )
        response.raise_for_status()
        if response.json().get("accepted") is not True:
            raise RuntimeError("Woo did not acknowledge the prepared generation")

    def one(self, prepare: Any, loaded: Any) -> bool:
        job = self.claim()
        if job is None:
            return False
        revision = Snapshot.read(job["manifest"]).source_revision
        if revision != job["source_revision"]:
            raise RuntimeError("job manifest revision differs from its claimed source")
        try:
            version = prepare(job["manifest"])
            actual = loaded()
            if (
                actual.get("source_revision") != revision
                or actual.get("index_version") != version
            ):
                raise RuntimeError(
                    "running Genie has not loaded the prepared generation"
                )
            products = actual.get("products", [])
            partial = len(products) < len(job["manifest"]["products"])
            self.ack(
                job,
                str(actual["source_revision"]),
                "Some published products still lack proven document passages."
                if partial
                else "",
                products=products,
            )
        except (
            Exception,
            SystemExit,
        ):  # safe failure, including the native publish CLI
            # No request URL, auth header or exception repr enters Woo/logs.
            self.ack(job, "", "knowledge preparation or loaded verification failed")
            raise
        return True

    def close(self) -> None:
        self.client.close()


def run_job(
    worker: Worker,
    prepare: Callable[[dict[str, Any]], str],
    loaded: Callable[[], dict[str, Any]],
    index_dir: Path,
) -> bool:
    """Own one build through loaded/ack and roll back its rebuildable output."""
    discard_pending(index_dir)
    try:
        completed = worker.one(prepare, loaded)
        if completed:
            prepared = pending_build(index_dir)
            if prepared is not None:
                retain_builds(index_dir, prepared)
                (index_dir / "publication-worker-pending.json").unlink(missing_ok=True)
        return completed
    finally:
        # Includes build/publish failure, not just failures after a Path returns.
        # A killed process is recovered by the next locked invocation.
        discard_pending(index_dir)


def main() -> int:
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
    args = parser.parse_args()
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
            return 0
        worker = Worker(jobs, user, password, args.worker_id, args.lease_seconds)

        def prepare(manifest: dict[str, Any]) -> str:
            source = inventory.RestClient(args.rest_config)
            # Prevent an operator accidentally building one site and acking another.
            if urlsplit(source.base).netloc != urlsplit(jobs).netloc:
                raise RuntimeError(
                    "inventory and publication queue belong to different sites"
                )
            fetch_inventory(source, INVENTORY_PATH, PDF_DIR, manifest)
            parse.run(INVENTORY_PATH, PDF_DIR, PARSED_DIR, parse.WORKERS)
            import py3langid

            from index.tokenizer import HFTokenizer

            directory = build.build(
                INVENTORY_PATH,
                PDF_DIR,
                PARSED_DIR,
                INDEX_DIR,
                build.document_embedder(build.DEFAULT_MODEL),
                HFTokenizer.from_pretrained(build.CHUNK_TOKENIZER),
                lambda text: str(py3langid.classify(text)[0]),
                on_created=lambda directory: record_build(INDEX_DIR, directory),
            )
            report = publish(directory, args.root, args.host)
            return str(report["index_version"])

        def loaded() -> dict[str, Any]:
            # The serving process reopens the resolved current file under the same
            # search lock, so a changed symlink alone never satisfies this check.
            return read_loaded(args.loaded_url, token, args.host)

        try:
            run_job(worker, prepare, loaded, INDEX_DIR)
        except (Exception, SystemExit):  # noqa: BLE001 - safe status, no private URLs or credentials
            print(
                "Knowledge preparation failed; Woo retains the pending job.",
                file=sys.stderr,
            )
            return 1
        finally:
            worker.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
