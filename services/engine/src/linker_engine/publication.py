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

import requests

from .compatibility import Compatibility
from .engine import Engine


class PublicationUnavailable(RuntimeError):
    """Current source cannot be established; no result may escape."""


class PublicationChanged(PublicationUnavailable):
    """A dependency was withdrawn or replaced during the action."""


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
        url = os.environ.get(
            "LINKER_PUBLICATION_URL",
            "https://de-linker.com/wp-json/linker/v1/publication/manifest",
        )
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

    def view(self, engine: Engine) -> View:
        current = self.read()
        compatibility = self.feed.get("compatibility_revision")
        if not compatibility or current.get("compatibility_revision") != compatibility:
            raise PublicationUnavailable("Engineering compatibility is not ready")
        products = {p["product_id"]: p for p in current["products"]}
        documents = {d["document_id"]: d for d in current["documents"]}
        loaded = {p["id"]: p for p in self.feed["products"]}
        allowed = []
        dependencies: dict[str, Any] = {
            "source_revision": current["source_revision"],
            "compatibility_revision": compatibility,
            "products": [],
            "documents": [],
        }
        for product in engine.products.products:
            raw = loaded[product.id]
            canonical = raw.get("canonical_product_id")
            item = products.get(canonical)
            revision = raw.get("product_revision")
            if not item or not revision or item.get("product_revision") != revision:
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
                refs.append(
                    {
                        "document_id": doc_id,
                        "document_revision": document["document_revision"],
                        "product_id": canonical,
                    }
                )
            urls = {d["url"] for d in raw["documents"]}
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
                permitted_urls.setdefault(doc["url"], set()).add(
                    raw["canonical_product_id"]
                )
        contract = self.feed.get("compatibility")
        if not isinstance(contract, dict):
            raise PublicationUnavailable(
                "Loaded compatibility generation is incomplete"
            )

        def permitted_row(row: dict[str, Any]) -> bool:
            patterns = [row[key] for key in ("inverter", "battery") if key in row]
            relevant = {
                loaded[p.id]["canonical_product_id"]
                for p in allowed
                if any(re.search(pattern, p.model) for pattern in patterns)
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

    def confirm(self, view: View) -> None:
        current = self.read()
        if (
            current.get("compatibility_revision")
            != view.dependencies["compatibility_revision"]
        ):
            raise PublicationChanged("Engineering dependencies changed")
        products = {p["product_id"]: p for p in current["products"]}
        docs = {d["document_id"]: d for d in current["documents"]}
        for product in view.dependencies["products"]:
            if (
                products.get(product["product_id"], {}).get("product_revision")
                != product["product_revision"]
            ):
                raise PublicationChanged("Product publication changed")
        for doc in view.dependencies["documents"]:
            item = docs.get(doc["document_id"], {})
            if item.get("document_revision") != doc["document_revision"] or doc[
                "product_id"
            ] not in item.get("product_ids", []):
                raise PublicationChanged("Document publication changed")


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
