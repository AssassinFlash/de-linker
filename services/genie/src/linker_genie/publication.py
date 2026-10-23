"""Woo's current publication permission, independent of every derived index.

No TTL or fallback: each read and release validates against Woo. A transport error
stops the affected turn. This client holds no WordPress identity; the manifest,
exact supplied-model identification and dependency validation expose permission only.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

PREFIX = "/wp-json/linker/v1/publication"


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

    @classmethod
    def read(cls, value: Any) -> Snapshot:
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise PublicationUnavailable("unsupported Woo publication manifest")
        if not isinstance(value.get("source_revision"), str):
            raise PublicationUnavailable("missing Woo publication revision")
        try:
            products = {int(p["product_id"]): p for p in value["products"]}
            documents = {str(d["document_id"]): d for d in value["documents"]}
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
        self, base_url: str, transport: httpx.BaseTransport | None = None
    ) -> None:
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
        try:
            response = self._client.request(method, PREFIX + path, json=body)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise PublicationUnavailable(
                "Woo publication permission unavailable"
            ) from error

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

    def identify_text(self, text: str) -> dict[str, str]:
        """Let Woo match known model labels in supplied text, without listing drafts."""
        response = self._request("POST", "/identify", {"text": text})
        if not isinstance(response, dict) or not isinstance(
            response.get("models"), list
        ):
            raise PublicationUnavailable("invalid Woo model identification")
        return {
            str(row["model"]).casefold(): str(row["status"])
            for row in response["models"]
            if isinstance(row, dict)
        }

    def close(self) -> None:
        self._client.close()


_CURRENT: PublicationClient | None = None


def current() -> PublicationClient:
    global _CURRENT
    if _CURRENT is None:
        _CURRENT = PublicationClient(os.environ.get("GENIE_WP_URL", "http://127.0.0.1"))
    return _CURRENT
