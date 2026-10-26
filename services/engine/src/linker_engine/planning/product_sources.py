"""The planner reads the site's existing Woo-loaded engineering generation.

No product editor, fallback list, source acquisition or independent cache lives
here. The shared publication module owns current permission and preparation;
the shared site service owns the loaded immutable feed. Project binding and
operation-level validation compose with this same authority.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from ..engine import Engine
from ..products import FeedError
from ..publication import (
    Publication,
    PublicationChanged,
    PublicationUnavailable,
    ReferenceEvidenceUnavailable,
    View,
)
from .canonical import Json, Object, decode_object, encode
from .equipment_fact_resolution import declared_battery_ports
from .equipment_facts import compile_product
from .errors import Conflict, InvalidInput, ProductEvidenceChanged, VersionUnavailable
from .geometry_documents import GeometryDocument, ModuleSource, ModuleSpec
from .pv_parameters import PvGenerationParameters, PvModuleParameters
from .pv_profile_preparation import PROFILE_PURPOSE
from .woo_module import module_template


class ProductProvider(Protocol):
    engine: Engine
    publication: Publication
    version: str


def worker_product_provider() -> ProductProvider:
    # Reuse the site's loader for the currently selected immutable generation.
    # Run proofs stay frozen; current permission is checked independently.
    from ..app import SOURCE, Services, Settings

    return Services(Settings.from_environment(), SOURCE)


class ProductSources:
    def __init__(self, load: Callable[[], ProductProvider]) -> None:
        self.load = load

    def module_basis(self) -> Object:
        return self._module_basis(electrical=False)

    def electrical_module_basis(self) -> Object:
        return self._module_basis(electrical=True)

    def _module_basis(self, *, electrical: bool) -> Object:
        """Freeze only the used reference, not unrelated sales candidates."""
        try:
            loaded = self.load()
            view = loaded.publication.reference_view(loaded.engine)
            identity = view.dependencies["reference_inputs"][0]["reference_input_id"]
            raw = next(
                row
                for row in loaded.publication.feed["overlay"]
                if row["id"] == identity
            )
            result = decode_object(
                encode(
                    {
                        "schema_version": 1,
                        "publication": view.dependencies,
                        "module": module_template(raw),
                        **({"electrical_product": raw} if electrical else {}),
                    }
                )
            )
            loaded.publication.confirm(
                view, require_reference=True, require_prepared=True
            )
            return result
        except (PublicationChanged, ReferenceEvidenceUnavailable) as error:
            raise ProductEvidenceChanged("current Woo module data changed") from error
        except (
            PublicationUnavailable,
            FeedError,
            OSError,
            KeyError,
            ValueError,
            RuntimeError,
        ) as error:
            raise VersionUnavailable(
                "current Woo module data is unavailable"
            ) from error

    def equipment_basis(self) -> Object:
        """Freeze the whole current candidate pool and its scoped pair claims."""
        try:
            loaded = self.load()
            if loaded.publication.feed.get("figure_projection_version") != 2:
                raise VersionUnavailable(
                    "Woo condition-preserving figure projection must be prepared"
                )
            if loaded.publication.feed.get("compatibility_origin") != "woocommerce":
                raise VersionUnavailable(
                    "Woo-maintained compatibility claims must be prepared"
                )
            view = loaded.publication.prepared_view(loaded.engine)
            ids = {p.id for p in view.engine.products.products}
            result = decode_object(
                encode(
                    {
                        "schema_version": 1,
                        "figure_projection_version": 2,
                        "compatibility_origin": "woocommerce",
                        "publication": view.dependencies,
                        "products": [
                            row
                            for row in loaded.publication.feed["products"]
                            if row["id"] in ids
                        ],
                        "compatibility": view.engine.compatibility.snapshot(),
                    }
                )
            )
            loaded.publication.confirm(view, require_prepared=True)
            return result
        except PublicationChanged as error:
            raise ProductEvidenceChanged(
                "current Woo equipment data changed"
            ) from error
        except (
            PublicationUnavailable,
            FeedError,
            OSError,
            KeyError,
            ValueError,
            RuntimeError,
        ) as error:
            raise VersionUnavailable(
                "current Woo equipment data is unavailable"
            ) from error

    def confirm_basis(self, basis: Object, *, require_reference: bool = True) -> None:
        scope = basis.get("publication")
        if basis.get("schema_version") != 1 or not isinstance(scope, dict):
            raise VersionUnavailable("pinned Woo product proof is missing")
        nested = basis.get("pv_module_inputs")
        if isinstance(nested, dict):
            self.confirm_basis(nested)
        if require_reference and set(basis) == {
            "schema_version",
            "publication",
            "module",
        } | ({"electrical_product"} if "electrical_product" in basis else set()):
            # PV preparation uses only this reference component. A sales
            # compatibility update must not invalidate unchanged module output.
            # Obtain a fresh native permission/preparation proof, then require
            # exact component, document and reference identities. Retained
            # profile bytes and their original publication proof stay intact.
            current = (
                self.electrical_module_basis()
                if "electrical_product" in basis
                else self.module_basis()
            )
            current_scope = cast(Object, current["publication"])
            if (
                set(scope) != set(current_scope)
                or basis["module"] != current["module"]
                or basis.get("electrical_product") != current.get("electrical_product")
                or any(
                    scope.get(key) != current_scope.get(key)
                    for key in (
                        "engineering_contract",
                        "products",
                        "documents",
                        "reference_inputs",
                    )
                )
            ):
                raise ProductEvidenceChanged("current Woo module data changed")
            return
        try:
            loaded = self.load()
            if (
                basis.get("compatibility_origin") == "woocommerce"
                and loaded.publication.feed.get("compatibility_origin") != "woocommerce"
            ):
                raise VersionUnavailable(
                    "current Woo compatibility projection is unavailable"
                )
            loaded.publication.confirm(
                View(loaded.engine, scope),
                require_reference=require_reference,
                require_prepared=True,
            )
        except PublicationChanged as error:
            raise ProductEvidenceChanged("current Woo product data changed") from error
        except (
            PublicationUnavailable,
            FeedError,
            OSError,
            KeyError,
            ValueError,
            RuntimeError,
        ) as error:
            raise VersionUnavailable(
                "current Woo product data is unavailable"
            ) from error

    @staticmethod
    def _check_binding(source: ModuleSource, expected: ModuleSource) -> None:
        old, current = source.woo, expected.woo
        if (
            old is not None
            and current is not None
            and (
                old.product_id == current.product_id
                and old.reference_input_id == current.reference_input_id
                and old.product_revision != current.product_revision
            )
        ):
            raise ProductEvidenceChanged("the saved Woo module revision changed")

    @staticmethod
    def _check_module(module: ModuleSpec, basis: Object) -> None:
        template = cast(Object, basis["module"])
        expected = ModuleSpec.read(template["specification"])
        ProductSources._check_binding(module.source, expected.source)
        if module != expected.model_copy(update={"id": module.id}):
            raise InvalidInput("choose the current Woo-maintained module specification")

    def check_project(self, inputs: Object, previous: Object | None = None) -> None:
        """Retain unchanged history; new/edited product facts must come from Woo."""
        before = previous or {}
        if "equipment_plant" in inputs and inputs.get("equipment_plant") != before.get(
            "equipment_plant"
        ):
            from .equipment_plant import EquipmentPlant
            from .plant_assessment import plant_products

            plant_products(EquipmentPlant.from_inputs(inputs), self.equipment_basis())
        self.check_installation(inputs, before)
        changed = inputs.get("geometry") != before.get("geometry")
        pv_changed = inputs.get("pv_generation") != before.get("pv_generation")
        if (not changed and not pv_changed) or "geometry" not in inputs:
            return
        geometry = GeometryDocument.read(inputs["geometry"])
        old = (
            GeometryDocument.read(before["geometry"])
            if isinstance(before.get("geometry"), dict)
            else None
        )
        edited = [
            module
            for module in geometry.module_specs
            if old is None or module not in old.module_specs
        ]
        if not edited and not (pv_changed and "pv_generation" in inputs):
            return
        if any(module.source.woo is None for module in edited):
            raise InvalidInput(
                "choose a Woo-maintained module before adding product facts"
            )
        basis = self.module_basis()
        for module in edited:
            self._check_module(module, basis)
        if pv_changed and "pv_generation" in inputs:
            self.check_pv_inputs(inputs, basis)

    def check_installation(self, inputs: Object, previous: Object) -> None:
        from .installation_inputs import InstallationInputs
        from .installation_takeoff import product_basis

        if "installation" not in inputs or inputs.get("installation") == previous.get(
            "installation"
        ):
            return
        plan = InstallationInputs.read(inputs["installation"])
        old = (
            InstallationInputs.read(previous["installation"])
            if "installation" in previous
            else None
        )
        bindings = (
            {(d.id, d.product_id, d.product_revision) for d in old.instances}
            if old
            else set()
        )
        if any(
            d.product_id is not None
            and (d.id, d.product_id, d.product_revision) not in bindings
            for d in plan.instances
        ):
            basis = product_basis(plan, self.equipment_basis())
            self.confirm_basis(basis, require_reference=False)

    def pv_basis(self, inputs: Object) -> Object:
        basis = self.module_basis()
        self.check_pv_inputs(inputs, basis)
        return basis

    def check_pv_inputs(self, inputs: Object, basis: Object) -> None:
        geometry = GeometryDocument.read(inputs.get("geometry"))
        parameters = PvGenerationParameters.read(inputs.get("pv_generation"))
        template = cast(Object, basis["module"])
        expected = PvModuleParameters.read(template["parameters"])
        modules = {module.id: module for module in geometry.module_specs}
        for item in parameters.modules:
            module = modules.get(item.module_spec_id)
            if module is None:
                raise InvalidInput("PV module is outside the saved roof layout")
            self._check_module(module, basis)
            self._check_binding(item.source, expected.source)
            if item != expected.model_copy(update={"module_spec_id": module.id}):
                raise InvalidInput(
                    "PV coefficient must match its current Woo-maintained figure"
                )

    def check_profile(self, metadata: Object) -> None:
        if metadata.get("profile_type") != PROFILE_PURPOSE:
            return
        basis = metadata.get("woo_module_inputs")
        if not isinstance(basis, dict):
            raise InvalidInput(
                "prepare a PV profile from the current Woo-maintained module"
            )
        self.confirm_basis(basis)

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
            references = [row for row in feed["overlay"] if row["id"] in reference_ids]
            templates: list[Json] = []
            diagnostics: list[Json] = []
            for row in references:
                try:
                    templates.append(module_template(row))
                except (VersionUnavailable, ValueError, KeyError) as error:
                    diagnostics.append(
                        {
                            "product_id": row["canonical_product_id"],
                            "reference_input_id": row["id"],
                            "code": "module_projection_unavailable",
                            "reason": str(error),
                        }
                    )
            result = decode_object(
                encode(
                    {
                        "schema_version": 1,
                        "provider": "woocommerce",
                        "compatibility_origin": feed.get("compatibility_origin"),
                        "figure_projection_version": feed.get(
                            "figure_projection_version"
                        ),
                        "loaded_engine_version": loaded.version,
                        "loaded_source_revision": feed["source_revision"],
                        "publication": view.dependencies,
                        "products": [
                            row for row in feed["products"] if row["id"] in ids
                        ],
                        "dc_battery_ports": {
                            str(row["canonical_product_id"]): cast(Json, ports)
                            for row in feed["products"]
                            if row["id"] in ids
                            and (ports := declared_battery_ports(compile_product(row)))
                            is not None
                        },
                        "references": references,
                        "pv_modules": templates,
                        "module_diagnostics": diagnostics,
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
            KeyError,
            ValueError,
            RuntimeError,
        ) as error:
            raise VersionUnavailable(
                "current Woo product data is unavailable"
            ) from error
