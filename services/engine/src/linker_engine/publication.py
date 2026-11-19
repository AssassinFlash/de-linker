"""Current Woo permission applied to an immutable, loaded engineering generation.

Derived feed data never grants publication permission. Read Woo before work and
again before releasing it; an unavailable authority closes the action in every
anti-abuse mode. An unrelated unprepared product does not close valid products.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from .compatibility import Compatibility
from .engine import Engine


class PublicationUnavailable(RuntimeError):
    """Current source cannot be established; no result may escape."""


class PublicationChanged(PublicationUnavailable):
    """A dependency was withdrawn or replaced during the action."""


# Stored receipts bind the equipment and documents used for the selection.
ENGINEERING_CONTRACT = 2
MANIFEST_URL = "https://de-linker.com/wp-json/linker/v1/publication/manifest"


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


@dataclass(frozen=True)
class View:
    engine: Engine
    dependencies: dict[str, Any]


class Publication:
    def __init__(self, feed: dict[str, Any]) -> None:
        self.feed = feed

    def read(self) -> dict[str, Any]:
        url = os.environ.get("LINKER_PUBLICATION_URL", MANIFEST_URL)
        try:
            data = self._manifest(url)
            if (
                not isinstance(data, dict)
                or data.get("schema_version") != 1
                or not isinstance(data.get("products"), list)
                or not isinstance(data.get("documents"), list)
            ):
                raise ValueError("invalid publication manifest")
            if (
                not all(
                    isinstance(row, dict)
                    and isinstance(row.get("product_id"), int)
                    and isinstance(row.get("product_revision"), str)
                    for row in data["products"]
                )
                or not all(
                    isinstance(row, dict)
                    and isinstance(row.get("document_id"), str)
                    and isinstance(row.get("document_revision"), str)
                    and isinstance(row.get("product_ids"), list)
                    for row in data["documents"]
                )
                or not isinstance(data.get("source_revision"), str)
                or not isinstance(data.get("compatibility_revision"), str)
            ):
                raise ValueError("invalid publication dependencies")
            return data
        except (requests.RequestException, ValueError) as error:
            raise PublicationUnavailable(
                "Current product publication is unavailable"
            ) from error

    @staticmethod
    def _manifest(url: str) -> Any:
        """Read the current manifest, retrying transient transport failures.

        The site's edge intermittently answers a fresh TLS handshake with
        ``TLSV1_ALERT_INTERNAL_ERROR``; that is a transport blip, not a
        withdrawn publication. Retrying only connection/SSL faults keeps a
        genuine permission or dependency change failing closed on the first
        response instead of being masked by the retry window.
        """
        attempts = 3
        for attempt in range(attempts):
            try:
                response = requests.get(
                    url, timeout=10, headers={"Cache-Control": "no-cache"}
                )
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout):
                if attempt + 1 == attempts:
                    raise
                time.sleep(0.15 * (attempt + 1))
        raise AssertionError("unreachable")

    def _scope(self, current: dict[str, Any]) -> dict[str, Any]:
        compatibility = self.feed.get("compatibility_revision")
        if not compatibility or current.get("compatibility_revision") != compatibility:
            raise PublicationUnavailable("Engineering compatibility is not ready")
        return {
            "engineering_contract": ENGINEERING_CONTRACT,
            "reference_inputs": [],
            "source_revision": current["source_revision"],
            "compatibility_revision": compatibility,
            "products": [],
            "documents": [],
        }

    @staticmethod
    def _feed_url(url: str) -> str:
        """Mirror the producer's explicit current-site to canonical mapping.

        Local snapshots keep their upload origin in the authority manifest,
        while EngineeringFeed.feed_url emits the production origin. Only the
        configured authority's exact origin is interchangeable, never an
        arbitrary host with a matching path or matching content hash.
        """
        source = urlsplit(os.environ.get("LINKER_PUBLICATION_URL", MANIFEST_URL))
        parsed = urlsplit(url)
        if (parsed.scheme.lower(), parsed.netloc.lower()) == (
            source.scheme.lower(),
            source.netloc.lower(),
        ):
            return urlunsplit(
                ("https", "de-linker.com", parsed.path, parsed.query, parsed.fragment)
            )
        return url

    def prepared_products(self, engine: Engine) -> list[dict[str, Any]]:
        """A reference can remain unready without blocking unrelated products."""
        current = self.read()
        products: list[dict[str, Any]] = self._view(engine, current).dependencies[
            "products"
        ]
        products.extend(self.cable_scope(current)["products"])
        return products

    def cable_scope(
        self, current: dict[str, Any], *, prepared: bool = False
    ) -> dict[str, Any]:
        """Current non-sale cable records use normal product/document revocation."""
        products = {p["product_id"]: p for p in current["products"]}
        documents = {d["document_id"]: d for d in current["documents"]}
        scope: dict[str, Any] = {"products": [], "documents": []}
        for raw in self.feed["overlay"]:
            if raw["kind"] != "cable":
                continue
            canonical, revision = (
                raw.get("canonical_product_id"),
                raw.get("product_revision"),
            )
            source = products.get(canonical, {})
            if (
                source.get("engineering_role") != "reference_cable"
                or source.get("engineering_id") != raw["id"]
                or source.get("product_revision") != revision
                or raw.get("reference_revision") != revision
                or not raw["documents"]
                or prepared
                and source.get("ready", {}).get("engineering") is not True
            ):
                continue
            refs = []
            for doc in raw["documents"]:
                current_doc = documents.get(doc.get("document_id"), {})
                if (
                    doc.get("document_revision") != current_doc.get("document_revision")
                    or doc.get("blob_sha256") != current_doc.get("blob_sha256")
                    or canonical not in current_doc.get("product_ids", [])
                    or doc.get("document_id") not in source.get("documents", [])
                    or doc["url"]
                    not in {
                        self._feed_url(url)
                        for url in [
                            current_doc.get("url"),
                            *current_doc.get("aliases", []),
                        ]
                        if isinstance(url, str)
                    }
                ):
                    break
                refs.append(
                    {
                        "document_id": doc["document_id"],
                        "document_revision": doc["document_revision"],
                        "blob_sha256": doc["blob_sha256"],
                        "product_id": canonical,
                    }
                )
            else:
                bound_documents = {doc["document_id"]: doc for doc in raw["documents"]}
                facts = raw["cable_facts"]
                if any(
                    evidence["product_id"] != canonical
                    or evidence["document_id"] not in bound_documents
                    or any(
                        evidence[key]
                        != bound_documents[evidence["document_id"]].get(key)
                        for key in ("document_revision", "blob_sha256", "url")
                    )
                    for evidence in [
                        facts["source"],
                        *(row["source"] for row in facts["parameter_sets"]),
                        *(
                            row["source"]
                            for row in facts.get("reference_current_ratings", [])
                        ),
                    ]
                ):
                    continue
                scope["products"].append(
                    {"product_id": canonical, "product_revision": revision}
                )
                scope["documents"].extend(refs)
        return scope

    def view(self, engine: Engine) -> View:
        return self._view(engine, self.read())

    def prepared_view(
        self,
        engine: Engine,
        *,
        include_cables: bool = False,
    ) -> View:
        """Planner consumption of the current Woo-prepared intersection.

        Preparation workers still use view()/prepared_products() to prove a
        newly loaded generation before acknowledging it. Customer reads must
        additionally respect Woo's current engineering readiness.
        """
        current = self.read()
        ready = {
            item["product_id"]
            for item in current["products"]
            if item.get("ready", {}).get("engineering") is True
        }
        prepared = replace(
            engine,
            products=replace(
                engine.products,
                products=tuple(p for p in engine.products.products if p.id in ready),
            ),
        )
        view = self._view(prepared, current)
        if include_cables:
            cable_scope = self.cable_scope(current, prepared=True)
            for kind in ("products", "documents"):
                view.dependencies[kind].extend(cable_scope[kind])

        return view

    def _view(
        self,
        engine: Engine,
        current: dict[str, Any],
    ) -> View:
        dependencies = self._scope(current)
        products = {p["product_id"]: p for p in current["products"]}
        documents = {d["document_id"]: d for d in current["documents"]}
        loaded = {p["id"]: p for p in self.feed["products"]}
        allowed = []
        reference_ids = {
            item.get("canonical_product_id") for item in self.feed["overlay"]
        }
        for product in engine.products.products:
            raw = loaded[product.id]
            canonical = raw.get("canonical_product_id")
            item = products.get(canonical)
            revision = raw.get("product_revision")
            if (
                not item
                or not revision
                or item.get("product_revision") != revision
                or item.get("engineering_role")
                or canonical in reference_ids
            ):
                continue
            refs = []
            permitted = True
            # Validate every document and figure that any candidate can use.
            for document in raw["documents"]:
                doc_id = document.get("document_id")
                doc = documents.get(doc_id)
                if (
                    not doc
                    or not document.get("document_revision")
                    or doc.get("document_revision") != document["document_revision"]
                    or canonical not in doc.get("product_ids", [])
                ):
                    permitted = False
                    break
                current_urls = {
                    self._feed_url(url)
                    for url in [doc.get("url"), *doc.get("aliases", [])]
                    if isinstance(url, str)
                }
                if not {document["url"], *document.get("aliases", [])} <= current_urls:
                    permitted = False
                    break
                refs.append(
                    {
                        "document_id": doc_id,
                        "document_revision": document["document_revision"],
                        "product_id": canonical,
                    }
                )
            urls = {
                url
                for document in raw["documents"]
                for url in [document["url"], *document.get("aliases", [])]
            }
            if any(f["citation"]["url"] not in urls for f in raw["figures"].values()):
                permitted = False
            if not permitted:
                continue
            allowed.append(product)
            dependencies["products"].append(
                {"product_id": canonical, "product_revision": revision}
            )
            dependencies["documents"].extend(refs)
        permitted_urls: dict[str, set[int]] = {}
        for product in allowed:
            raw = loaded[product.id]
            for doc in raw["documents"]:
                for url in [doc["url"], *doc.get("aliases", [])]:
                    permitted_urls.setdefault(url, set()).add(
                        raw["canonical_product_id"]
                    )
        contract = self.feed.get("compatibility")
        if not isinstance(contract, dict):
            raise PublicationUnavailable(
                "Loaded compatibility generation is incomplete"
            )

        def permitted_row(row: dict[str, Any]) -> bool:
            bound = {
                row[key]
                for key in ("inverter_product_id", "battery_product_id")
                if key in row
            }
            allowed_ids = {loaded[p.id]["canonical_product_id"] for p in allowed}
            if bound and not bound.issubset(allowed_ids):
                return False
            patterns = [row[key] for key in ("inverter", "battery") if key in row]
            relevant = {
                loaded[p.id]["canonical_product_id"]
                for p in allowed
                if (
                    loaded[p.id]["canonical_product_id"] in bound
                    if bound
                    else any(re.search(pattern, p.model) for pattern in patterns)
                )
            }
            return bool(relevant) and all(
                bool(permitted_urls.get(doc["url"], set()) & relevant)
                for doc in row["documents"]
            )

        contract = {
            **contract,
            "pairs": [row for row in contract["pairs"] if permitted_row(row)],
            "requirements": [
                row for row in contract["requirements"] if permitted_row(row)
            ],
        }
        return View(
            replace(
                engine,
                products=replace(engine.products, products=tuple(allowed)),
                compatibility=Compatibility(contract),
            ),
            dependencies,
        )

    def confirm(
        self,
        view: View,
        *,
        require_prepared: bool = False,
        current: dict[str, Any] | None = None,
    ) -> None:
        # One operation may confirm several frozen proofs against the same read.
        current = self.read() if current is None else current
        scope = view.dependencies
        if (
            scope.get("engineering_contract") != ENGINEERING_CONTRACT
            or not all(
                isinstance(scope.get(kind), list)
                for kind in ("products", "documents", "reference_inputs")
            )
            or bool(scope["reference_inputs"])
        ):
            raise PublicationChanged("Engineering evidence proof is missing")
        if current.get("compatibility_revision") != scope.get("compatibility_revision"):
            raise PublicationChanged("Engineering dependencies changed")
        products = {p["product_id"]: p for p in current["products"]}
        docs = {d["document_id"]: d for d in current["documents"]}
        for product in scope["products"]:
            if (
                products.get(product["product_id"], {}).get("product_revision")
                != product["product_revision"]
            ):
                raise PublicationChanged("Product publication changed")
            if (
                require_prepared
                and products[product["product_id"]].get("ready", {}).get("engineering")
                is not True
            ):
                raise PublicationChanged("Product engineering preparation changed")
        for doc in scope["documents"]:
            item = docs.get(doc["document_id"], {})
            if item.get("document_revision") != doc["document_revision"] or doc[
                "product_id"
            ] not in item.get("product_ids", []):
                raise PublicationChanged("Document publication changed")
            if "blob_sha256" in doc and doc["blob_sha256"] != item.get("blob_sha256"):
                raise PublicationChanged("Document content changed")


def fingerprint(
    input_: dict[str, Any], result: dict[str, Any], dependencies: dict[str, Any]
) -> str:
    # The clock and unrelated source changes cannot silently change a confirmed
    # system. All candidates, selected quantities and engineering results can.
    stable = dict(dependencies)
    stable.pop("source_revision", None)
    content = {
        k: v
        for k, v in result.items()
        if k not in {"report", "publication", "selection_fingerprint"}
    }
    return digest({"input": input_, "result": content, "dependencies": stable})
