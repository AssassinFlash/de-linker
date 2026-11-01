"""Woo's current publication permission, independent of every derived index.

No TTL or fallback: each read and release validates against Woo. A transport error
stops the affected turn. This client holds no WordPress identity; the manifest,
exact supplied-model identification and dependency validation expose permission only.
"""

from __future__ import annotations

import json
import os
import syslog
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

PREFIX = "/wp-json/linker/v1/publication"
_IDENTIFY_ATTEMPTS = 3
_RETRY_AFTER_CAP = 2.0


def _retry_after(response: httpx.Response) -> float:
    """Honor a bounded Retry-After without trusting a response body."""
    raw = response.headers.get("retry-after", "").strip()
    delay = 0.0
    if raw.isascii() and raw.isdecimal() and len(raw) <= 8:
        delay = float(int(raw))
    elif 0 < len(raw) <= 128:
        try:
            when = parsedate_to_datetime(raw)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            delay = max(0.0, when.timestamp() - time.time())
        except (TypeError, ValueError, OverflowError, IndexError):
            pass
    return min(_RETRY_AFTER_CAP, delay)


def knowledge_progress(phase: str, event: str, **counts: int | float) -> None:
    """Use the worker's existing syslog sink, plus flushed foreground output.

    Callers provide fixed phase/event names and numeric counters only. Supplied
    text, native lease credentials and document/customer content never enter it.
    """
    message = json.dumps({"phase": phase, "event": event, **counts})
    syslog.syslog(syslog.LOG_INFO, "linker-knowledge-publication " + message)
    print(message, flush=True)


class PublicationUnavailable(RuntimeError):
    """Current permission cannot be established; never serve a stale permit."""

    failure_kind = "retrieval"


class PublicationChanged(PublicationUnavailable):
    """Woo answered authoritatively that a captured dependency was revoked."""


@dataclass(frozen=True)
class Snapshot:
    source_revision: str
    products: dict[int, dict[str, Any]]
    documents: dict[str, dict[str, Any]]
    compatibility_revision: str
    model_identity_revision: str = ""

    @classmethod
    def read(cls, value: Any) -> Snapshot:
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise PublicationUnavailable("unsupported Woo publication manifest")
        if not isinstance(value.get("source_revision"), str):
            raise PublicationUnavailable("missing Woo publication revision")
        if "model_identity_revision" in value and (
            not isinstance(value["model_identity_revision"], str)
            or not value["model_identity_revision"]
        ):
            raise PublicationUnavailable("invalid Woo model identity revision")
        try:
            if (
                not isinstance(value["products"], list)
                or not isinstance(value["documents"], list)
                or not all(isinstance(p, dict) for p in value["products"])
            ):
                raise ValueError("invalid product/document entries")
            products = {
                int(p["product_id"]): p
                for p in value["products"]
                if p.get("engineering_role")
                not in ("reference_pv_module", "reference_cable")
            }
            documents = {
                str(d["document_id"]): {
                    **d,
                    "product_ids": [pid for pid in d["product_ids"] if pid in products],
                }
                for d in value["documents"]
                if any(pid in products for pid in d["product_ids"])
            }
            for product in products.values():
                if not product["product_revision"]:
                    raise ValueError("empty product revision")
            for document in documents.values():
                if not document["document_revision"] or not document["blob_sha256"]:
                    raise ValueError("empty document revision")
        except (KeyError, TypeError, ValueError) as error:
            raise PublicationUnavailable("invalid Woo publication manifest") from error
        return cls(
            value["source_revision"],
            products,
            documents,
            str(value.get("compatibility_revision", "")),
            str(value.get("model_identity_revision", "")),
        )

    def canonical(self, product_id: int) -> int | None:
        for canonical, product in self.products.items():
            if product_id == canonical or product_id in product.get(
                "published_locale_ids", []
            ):
                return canonical
        return None

    def dependencies(self) -> dict[str, Any]:
        """Validate the entire input set, not just the eventual selected cards."""
        return {
            "products": [
                {"product_id": pid, "product_revision": p["product_revision"]}
                for pid, p in self.products.items()
            ],
            "documents": [
                {
                    "document_id": did,
                    "document_revision": d["document_revision"],
                    "product_id": pid,
                }
                for did, d in self.documents.items()
                for pid in d["product_ids"]
            ],
            "compatibility_revision": self.compatibility_revision,
            "model_identity_revision": self.model_identity_revision,
        }

    def require_products(self, product_ids: Sequence[int]) -> None:
        if any(self.canonical(pid) is None for pid in product_ids):
            raise PublicationChanged("product is no longer published")

    def require_urls(self, urls: Sequence[str]) -> None:
        allowed = {
            str(url).split("#")[0]
            for d in self.documents.values()
            for url in [d["url"], *d.get("aliases", [])]
        }
        if any(url.split("#")[0] not in allowed for url in urls):
            raise PublicationChanged("document is no longer published")


def product_ids(value: Any) -> Iterator[int]:
    """IDs in commerce payloads, including candidates and compatibility partners."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"product_id", "inverter_id", "battery_id"} and isinstance(
                child, int
            ):
                if child > 0:
                    yield child
            elif key in {"product_ids", "draft_ids"} and isinstance(child, list):
                yield from (pid for pid in child if isinstance(pid, int) and pid > 0)
            else:
                yield from product_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from product_ids(child)


def document_urls(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        if value.get("type") == "document" and isinstance(value.get("url"), str):
            yield value["url"]
        for key, child in value.items():
            if key in {"url", "doc_url", "href"} and isinstance(child, str):
                if child.split("#")[0].split("?")[0].lower().endswith(".pdf"):
                    yield child
            else:
                yield from document_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from document_urls(child)


class PublicationClient:
    def __init__(
        self,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        *,
        identify_deadline: int | None = None,
        identify_lease: Mapping[str, Any] | None = None,
    ) -> None:
        if identify_deadline is not None and type(identify_deadline) is not int:
            raise ValueError("identify deadline must be a native lease expiry")
        self._identify_deadline = identify_deadline
        self._identify_lease = (
            dict(identify_lease) if identify_lease is not None else None
        )
        self.identification: dict[str, int | float] = {
            "windows": 0,
            "input_bytes": 0,
            "batches": 0,
            "attempts": 0,
            "backoff_seconds": 0.0,
            "seconds": 0.0,
            "identity_reads": 0,
            "identity_seconds": 0.0,
            "match_seconds": 0.0,
        }
        # Same loopback budget as AbilityClient; no cached success on outage.
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=20,
            headers={"Cache-Control": "no-cache"},
            transport=transport,
        )

    def _request(
        self, method: str, path: str, body: Mapping[str, Any] | None = None
    ) -> Any:
        # The leased compiler opts in; interactive reads and every other endpoint
        # retain their original one-attempt behavior. /identify is read-only even
        # though it uses POST to keep supplied text out of URLs.
        deadline = (
            self._identify_deadline
            if method == "POST" and path == "/identify"
            else None
        )
        attempts = _IDENTIFY_ATTEMPTS if deadline is not None else 1
        auth = None
        if path == "/identify" and body is not None and "texts" in body:
            if self._identify_lease is None or deadline is None:
                raise PublicationUnavailable(
                    "batched identification requires a native lease"
                )
            try:
                verify = urlsplit(str(self._identify_lease.get("verify_url", "")))
                target = urlsplit(str(self._client.base_url))
                same_origin = (
                    verify.scheme,
                    verify.hostname,
                    verify.port
                    if verify.port is not None
                    else {"http": 80, "https": 443}.get(verify.scheme),
                ) == (
                    target.scheme,
                    target.hostname,
                    target.port
                    if target.port is not None
                    else {"http": 80, "https": 443}.get(target.scheme),
                )
            except ValueError:
                raise PublicationUnavailable("invalid native lease origin") from None
            if (
                not same_origin
                or verify.scheme not in {"http", "https"}
                or not verify.hostname
                or verify.username is not None
                or verify.password is not None
                or target.username is not None
                or target.password is not None
                or verify.path != PREFIX + "/jobs/claim"
                or verify.query
                or verify.fragment
            ):
                raise PublicationUnavailable("invalid native lease origin")
            auth = (
                str(self._identify_lease["username"]),
                str(self._identify_lease["password"]),
            )
        for attempt in range(attempts):
            if deadline is not None:
                remaining = deadline - time.time() - 1
                if remaining <= 0:
                    raise PublicationUnavailable("native knowledge lease expired")
            try:
                if path == "/identify":
                    self.identification["attempts"] += 1
                    if auth is not None:
                        knowledge_progress(
                            "identify",
                            "attempt",
                            attempt=attempt + 1,
                            batch=self.identification["batches"],
                            windows=self.identification["windows"],
                        )
                if deadline is None:
                    response = self._client.request(method, PREFIX + path, json=body)
                else:
                    response = self._client.request(
                        method,
                        PREFIX + path,
                        json=body,
                        timeout=min(20.0, remaining),
                        auth=auth,
                    )
                response.raise_for_status()
                result = response.json()
                if deadline is not None and deadline <= time.time() + 1:
                    raise PublicationUnavailable("native knowledge lease expired")
                return result
            except (httpx.HTTPError, ValueError) as error:
                retryable = isinstance(error, httpx.TransportError) or (
                    isinstance(error, httpx.HTTPStatusError)
                    and error.response.status_code == 503
                )
                if not retryable or attempt + 1 == attempts or deadline is None:
                    raise PublicationUnavailable(
                        "Woo publication permission unavailable"
                    ) from error
                suggested = (
                    _retry_after(error.response)
                    if isinstance(error, httpx.HTTPStatusError)
                    else 0.0
                )
                delay = max(float(2**attempt), suggested)
                if time.time() + delay + 1 >= deadline:
                    raise PublicationUnavailable(
                        "native knowledge lease expired before retry"
                    ) from error
                self.identification["backoff_seconds"] += delay
                if auth is not None:
                    knowledge_progress(
                        "identify",
                        "backoff",
                        attempt=attempt + 1,
                        seconds=delay,
                        batch=self.identification["batches"],
                    )
                time.sleep(delay)
        raise PublicationUnavailable("Woo publication permission unavailable")

    def snapshot(self) -> Snapshot:
        return Snapshot.read(self._request("GET", "/manifest"))

    def validate(self, snapshot: Snapshot) -> None:
        response = self._request("POST", "/validate", snapshot.dependencies())
        if isinstance(response, dict) and response.get("valid") is False:
            raise PublicationChanged("Woo publication changed during the operation")
        if not isinstance(response, dict) or response.get("valid") is not True:
            raise PublicationUnavailable("invalid Woo publication validation")

    def identify(self, models: Sequence[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        # Woo's exact-input schema caps batches at twenty; it never lists drafts.
        unique = list(dict.fromkeys(model.strip() for model in models if model.strip()))
        for offset in range(0, len(unique), 20):
            response = self._request(
                "POST", "/identify", {"models": unique[offset : offset + 20]}
            )
            if not isinstance(response, dict) or not isinstance(
                response.get("models"), list
            ):
                raise PublicationUnavailable("invalid Woo model identification")
            for row in response["models"]:
                if isinstance(row, dict):
                    result[str(row.get("model", "")).casefold()] = str(
                        row.get("status", "unknown")
                    )
        return result

    def identify_text(
        self, text: str, *, expected_revision: str = ""
    ) -> dict[str, str]:
        """Let Woo match known model labels in supplied text, without listing drafts."""
        response = self._request("POST", "/identify", {"text": text})
        if expected_revision and (
            not isinstance(response, dict)
            or response.get("model_identity_revision") != expected_revision
        ):
            raise PublicationChanged("model identity changed during compilation")
        if not isinstance(response, dict) or not isinstance(
            response.get("models"), list
        ):
            raise PublicationUnavailable("invalid Woo model identification")
        return {
            str(row["model"]).casefold(): str(row["status"])
            for row in response["models"]
            if isinstance(row, dict)
        }

    def identify_texts(self, texts: Sequence[str], revision: str) -> dict[str, str]:
        """Keep original windows distinct; only the leased compiler batches them."""
        windows = list(texts)
        if any(
            not isinstance(text, str) or not text or len(text.encode()) > 16000
            for text in windows
        ):
            raise ValueError(
                "identification windows must be nonempty and at most 16000 UTF-8 bytes"
            )
        if self._identify_lease is None:
            result: dict[str, str] = {}
            for text in windows:
                result.update(self.identify_text(text, expected_revision=revision))
            return result
        lease = self._identify_lease
        body = lease.get("verify_body")
        if (
            not revision
            or not isinstance(body, dict)
            or body.get("model_identity_revision") != revision
        ):
            raise PublicationUnavailable(
                "identification model identity differs from native lease"
            )
        result = {}
        for offset in range(0, len(windows), 20):
            batch = windows[offset : offset + 20]
            started = time.monotonic()
            self.identification["windows"] += len(batch)
            self.identification["input_bytes"] += sum(
                len(text.encode()) for text in batch
            )
            self.identification["batches"] += 1
            succeeded = False
            try:
                payload = {
                    name: body[name]
                    for name in (
                        "consumer",
                        "job_id",
                        "source_revision",
                        "recipe_revision",
                        "lease_token",
                        "activation_epoch",
                        "model_identity_revision",
                    )
                }
                response = self._request(
                    "POST", "/identify", {**payload, "texts": batch}
                )
                if (
                    not isinstance(response, dict)
                    or response.get("model_identity_revision") != revision
                    or not isinstance(response.get("models"), list)
                ):
                    raise PublicationUnavailable("invalid leased model identification")
                metrics = response.get("metrics", {})
                if isinstance(metrics, dict):
                    for name in ("identity_reads", "identity_seconds", "match_seconds"):
                        value = metrics.get(name, 0)
                        if type(value) in (int, float) and value >= 0:
                            self.identification[name] += value
                for row in response["models"]:
                    if (
                        not isinstance(row, dict)
                        or not isinstance(row.get("model"), str)
                        or row.get("status")
                        not in {"published", "unavailable", "unknown"}
                    ):
                        raise PublicationUnavailable(
                            "invalid leased model identification row"
                        )
                    label, status = row["model"].casefold(), row["status"]
                    if label in result and result[label] != status:
                        raise PublicationChanged(
                            "model identification changed between windows"
                        )
                    result[label] = status
                succeeded = True
            finally:
                self.identification["seconds"] += time.monotonic() - started
                knowledge_progress(
                    "identify",
                    "batch_done" if succeeded else "batch_failed",
                    **self.identification,
                )
        return result

    def close(self) -> None:
        self._client.close()


_CURRENT: PublicationClient | None = None


def current() -> PublicationClient:
    global _CURRENT
    if _CURRENT is None:
        _CURRENT = PublicationClient(os.environ.get("GENIE_WP_URL", "http://127.0.0.1"))
    return _CURRENT
