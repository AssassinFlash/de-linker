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


class ReferenceEvidenceUnavailable(PublicationUnavailable):
    """The approved reference input has no current, prepared Woo evidence."""


# Version 2 proves that non-saleable engineering references were considered.
# Old receipts only proved saleable products and cannot authorize a new action.
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
            response = requests.get(
                url, timeout=10, headers={"Cache-Control": "no-cache"}
            )
            response.raise_for_status()
            data = response.json()
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

    def _reference_scope(
        self, engine: Engine, current: dict[str, Any]
    ) -> dict[str, Any]:
        """Bind the loaded facts to their Woo source, never to a fresh URL hash.

        The producer removes figures whose content binding is no longer valid.
        This consumer requires that prepared immutable generation, its source
        role and every document's current identity, bytes and association.
        """
        unavailable = ReferenceEvidenceUnavailable(
            "Reference component evidence is not currently available"
        )
        module = engine.products.reference_module
        if module is None:
            raise unavailable
        matching = [item for item in self.feed["overlay"] if item["id"] == module.id]
        if len(matching) != 1:
            raise unavailable
        raw = matching[0]
        canonical = raw.get("canonical_product_id")
        revision = raw.get("product_revision")
        source: dict[str, Any] = next(
            (p for p in current["products"] if p["product_id"] == canonical), {}
        )
        if (
            not isinstance(canonical, int)
            or isinstance(canonical, bool)
            or canonical < 1
            or not isinstance(revision, str)
            or not re.fullmatch("[a-f0-9]{64}", revision)
            or raw.get("reference_revision") != revision
            or source.get("product_revision") != revision
            or source.get("engineering_role") != "reference_pv_module"
            or source.get("engineering_id") != module.id
            or not raw["documents"]
        ):
            raise unavailable
        documents = {d["document_id"]: d for d in current["documents"]}
        refs = []
        urls: set[str] = set()
        for document in raw["documents"]:
            doc_id = document.get("document_id")
            doc = documents.get(doc_id, {})
            sha = document.get("blob_sha256")
            current_urls = {
                self._feed_url(url)
                for url in [doc.get("url"), *doc.get("aliases", [])]
                if isinstance(url, str)
            }
            if (
                not doc_id
                or doc_id not in source.get("documents", [])
                or not document.get("document_revision")
                or doc.get("document_revision") != document["document_revision"]
                or canonical not in document.get("product_ids", [])
                or canonical not in doc.get("product_ids", [])
                or not isinstance(sha, str)
                or not re.fullmatch("[a-f0-9]{64}", sha)
                or doc.get("blob_sha256") != sha
                or document["url"] not in current_urls
            ):
                raise unavailable
            urls.update(current_urls)
            refs.append(
                {
                    "document_id": doc_id,
                    "document_revision": document["document_revision"],
                    "blob_sha256": sha,
                    "product_id": canonical,
                }
            )
        if any(f["citation"]["url"] not in urls for f in raw["figures"].values()):
            raise unavailable
        return {
            "reference_inputs": [
                {
                    "reference_input_id": module.id,
                    "reference_revision": revision,
                    "product_id": canonical,
                    "product_revision": revision,
                }
            ],
            "products": [{"product_id": canonical, "product_revision": revision}],
            "documents": refs,
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

    def reference_view(self, engine: Engine) -> View:
        """Roof operations use only the reference and its evidence."""
        current = self.read()
        return View(
            engine, {**self._scope(current), **self._reference_scope(engine, current)}
        )

    def prepared_products(self, engine: Engine) -> list[dict[str, Any]]:
        """A reference can remain unready without blocking unrelated products."""
        current = self.read()
        products: list[dict[str, Any]] = self._view(engine, current).dependencies[
            "products"
        ]
        try:
            products.extend(self._reference_scope(engine, current)["products"])
        except ReferenceEvidenceUnavailable:
            pass
        return products

    def view(self, engine: Engine, *, require_reference: bool = False) -> View:
        return self._view(engine, self.read(), require_reference=require_reference)

    def prepared_view(self, engine: Engine, *, include_reference: bool = False) -> View:
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
        reference = engine.products.reference_module
        raw_reference = next(
            (
                row
                for row in self.feed["overlay"]
                if reference and row["id"] == reference.id
            ),
            None,
        )
        if (
            raw_reference is None
            or raw_reference.get("canonical_product_id") not in ready
        ):
            reference = None
        prepared = replace(
            engine,
            products=replace(
                engine.products,
                products=tuple(p for p in engine.products.products if p.id in ready),
                reference_module=reference,
            ),
        )
        view = self._view(prepared, current)
        if include_reference and reference is not None:
            try:
                scope = self._reference_scope(prepared, current)
            except ReferenceEvidenceUnavailable:
                # A reference cannot close unrelated prepared sales products.
                return view
            for kind in ("products", "documents", "reference_inputs"):
                view.dependencies[kind] = list(
                    {
                        digest(row): row
                        for row in [*view.dependencies[kind], *scope[kind]]
                    }.values()
                )
        return view

    def _view(
        self,
        engine: Engine,
        current: dict[str, Any],
        *,
        require_reference: bool = False,
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
                or item.get("engineering_role") == "reference_pv_module"
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
        # Residential evaluates every inverter, including excluded candidates;
        # a retrofit and a genuinely empty inverter pool never use this module.
        if require_reference and any(p.device_class == "inverters" for p in allowed):
            reference = self._reference_scope(engine, current)
            for kind in ("reference_inputs", "products", "documents"):
                dependencies[kind].extend(reference[kind])
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
        require_reference: bool = False,
        require_prepared: bool = False,
    ) -> None:
        current = self.read()
        scope = view.dependencies
        if (
            scope.get("engineering_contract") != ENGINEERING_CONTRACT
            or not all(
                isinstance(scope.get(kind), list)
                for kind in ("products", "documents", "reference_inputs")
            )
            or (require_reference and not scope["reference_inputs"])
        ):
            raise PublicationChanged("Engineering evidence proof is missing")
        if current.get("compatibility_revision") != scope.get("compatibility_revision"):
            raise PublicationChanged("Engineering dependencies changed")
        if scope["reference_inputs"]:
            try:
                reference = self._reference_scope(view.engine, current)
            except ReferenceEvidenceUnavailable as error:
                raise PublicationChanged(
                    "Reference component evidence changed"
                ) from error
            if scope["reference_inputs"] != reference["reference_inputs"] or any(
                dependency not in scope[kind]
                for kind in ("products", "documents")
                for dependency in reference[kind]
            ):
                raise PublicationChanged("Reference component proof is incomplete")
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
