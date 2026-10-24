"""The planner reads the site's existing Woo-loaded engineering generation.

No product editor, fallback list, source acquisition or independent cache lives
here. The shared publication module owns current permission and preparation;
the shared site service owns the loaded immutable feed. Project binding and
operation-level validation compose with this same authority.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ..engine import Engine
from ..products import FeedError
from ..publication import Publication, PublicationChanged, PublicationUnavailable
from .canonical import Object, decode_object, encode
from .errors import Conflict, VersionUnavailable


class ProductProvider(Protocol):
    engine: Engine
    publication: Publication
    version: str


class ProductSources:
    def __init__(self, load: Callable[[], ProductProvider]) -> None:
        self.load = load

    def current(self) -> Object:
        try:
            loaded = self.load()
            view = loaded.publication.prepared_view(
                loaded.engine, include_reference=True
            )
            ids = {product.id for product in view.engine.products.products}
            reference_ids = {
                row["reference_input_id"]
                for row in view.dependencies["reference_inputs"]
            }
            feed = loaded.publication.feed
            result = decode_object(
                encode(
                    {
                        "schema_version": 1,
                        "provider": "woocommerce",
                        "loaded_engine_version": loaded.version,
                        "loaded_source_revision": feed["source_revision"],
                        "publication": view.dependencies,
                        "products": [
                            row for row in feed["products"] if row["id"] in ids
                        ],
                        "references": [
                            row for row in feed["overlay"] if row["id"] in reference_ids
                        ],
                    }
                )
            )
            loaded.publication.confirm(view, require_prepared=True)
            return result
        except PublicationChanged as error:
            raise Conflict("current Woo product data changed") from error
        except (
            PublicationUnavailable,
            FeedError,
            OSError,
            ValueError,
            RuntimeError,
        ) as error:
            raise VersionUnavailable(
                "current Woo product data is unavailable"
            ) from error
