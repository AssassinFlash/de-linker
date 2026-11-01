"""One durable qualification task over a pinned current Woo candidate pool."""

from __future__ import annotations

from typing import cast

from .canonical import Object
from .certificate_evidence import certificate_documents
from .certificate_sources import inspect_report_certificates
from .equipment_assessment import assess_equipment, selection_products
from .equipment_condition_inputs import validate_condition_inputs
from .equipment_conditions import review_device_conditions
from .equipment_inputs import EquipmentSelection
from .errors import VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .product_sources import ProductSources
from .records import Actor, Context, Lease
from .worker import Control
from .workspace import Workspace


class EquipmentKernel:
    kind = "qualify_woo_equipment_v1"
    models = {"task": kind, "facts": "cited_quantity_basis_v1"}

    def __init__(self, workspace: Workspace, products: ProductSources) -> None:
        self.workspace, self.products = workspace, products
        self.runtime = workspace.kernel_runtime()

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "product_policy": "current_woo_prepared_equipment_v1",
        }

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        basis = self.products.equipment_basis()
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            from .equipment_plant import EquipmentPlant
            from .plant_assessment import plant_products

            plant_products(EquipmentPlant.from_inputs(inputs), basis)
        else:
            selection = EquipmentSelection.read(inputs.get("equipment_selection"))
            selection_products(selection, basis)
        validate_condition_inputs(inputs, require_prepared=True)
        if (
            inputs.get("pv_string_plan") is not None
            or inputs.get("pv_plant_string_plan") is not None
        ):
            basis["pv_module_inputs"] = self.products.electrical_module_basis()
            # Validate object identities before queueing, then evaluate again
            # against this exact proof inside the durable worker.
            from .pv_string_assessment import assess_pv_strings

            if inputs.get("pv_plant_string_plan") is not None:
                from .plant_assessment import assess_plant

                assess_plant(inputs, basis)
            else:
                assess_pv_strings(inputs, basis)
        # Compilation is frozen here; constraint evaluation stays in worker.
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "woo.equipment_inputs": self.workspace.blobs.put_object(basis),
            },
            self.parameters(),
        )

    def __call__(self, lease: Lease, control: Control) -> Object:
        control.checkpoint()
        sha = lease.request.get("manifest_sha256")
        if not isinstance(sha, str):
            raise VersionUnavailable("equipment qualification has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, sha)
        if request_execution_key(lease.request, manifest, sha) != self.execution_key():
            raise VersionUnavailable("equipment execution settings changed")
        context = manifest.get("context")
        assert isinstance(context, dict)
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or pinned.get("runtime_bundle") != self.runtime.sha256
        ):
            raise VersionUnavailable("equipment runtime bundle is missing")
        proof = pinned.get("woo.equipment_inputs")
        if not isinstance(proof, str):
            raise VersionUnavailable("equipment publication proof is missing")
        basis = self.workspace.blobs.object(proof)
        self.products.confirm_basis(basis, require_reference=False)
        inputs = self.workspace.pinned_inputs(manifest)
        output = self.compute(inputs, basis, control)
        if "equipment_condition_inputs" in inputs:
            evidence = certificate_documents(basis, cast(Object, output["assessment"]))
            source: Object = {"certificates": evidence}
            originals = inspect_report_certificates(
                source, self.workspace.blobs, control.checkpoint
            )
            evidence["condition_review"] = review_device_conditions(inputs, evidence)
            output.update(certificates=evidence, dependencies=originals)
        control.checkpoint()
        self.products.confirm_basis(basis, require_reference=False)
        return {
            "schema": 1,
            "kind": self.kind,
            "project_id": manifest["project_id"],
            "revision": manifest["revision"],
            "input_sha256": manifest["input_sha256"],
            "manifest_sha256": sha,
            "runtime_sha256": self.runtime.sha256,
            "pinned_assets": pinned,
            **output,
        }

    def compute(self, inputs: Object, basis: Object, control: Control) -> Object:
        if "equipment_plant" in inputs:
            from .plant_assessment import assess_plant

            return {"assessment": assess_plant(inputs, basis, control.checkpoint)}
        return {"assessment": assess_equipment(inputs, basis)}
