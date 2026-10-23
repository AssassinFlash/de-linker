"""One automatic Mac knowledge preparation job, claimed from Woo's durable queue.

Runs under launchd (install_publication_worker.py). Heavy parsing stays on the Mac.
The worker never grants publication: late jobs are rejected by Woo and every
runtime read independently checks current permission. Credentials are env-only.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from index import build, inventory, parse
from index.paths import INDEX_DIR, INVENTORY_PATH, PARSED_DIR, PDF_DIR
from index.publication import inventory as fetch_inventory
from linker_genie.publication import Snapshot
from publish_index import publish


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
        except Exception:  # noqa: BLE001 - persist a safe failure, then propagate
            # No request URL, auth header or exception repr enters Woo/logs.
            self.ack(job, "", "knowledge preparation or loaded verification failed")
            raise
        return True

    def close(self) -> None:
        self.client.close()


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
        help="Local service POST /knowledge/loaded; SSH forwards may be used",
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
            )
            report = publish(directory, args.root, args.host)
            # Retain local current and previous successful build; reusable parse,
            # PDF and vector caches are content-addressed, not backup copies.
            versions = sorted(p for p in (INDEX_DIR / "builds").iterdir() if p.is_dir())
            import shutil

            for old in versions[:-2]:
                shutil.rmtree(old)
            return str(report["index_version"])

        def loaded() -> dict[str, Any]:
            # The serving process reopens the resolved current file under the same
            # search lock, so a changed symlink alone never satisfies this check.
            response = httpx.post(
                args.loaded_url,
                json={},
                timeout=20,
                headers={"X-Linker-Service-Token": token},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

        try:
            worker.one(prepare, loaded)
        except Exception:  # noqa: BLE001 - safe status, no private URLs or credentials
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
