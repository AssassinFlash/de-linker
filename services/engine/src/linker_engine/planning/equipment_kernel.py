"""One durable qualification task over a pinned current Woo candidate pool."""

from __future__ import annotations

from .canonical import Object
from .equipment_assessment import assess_equipment, selection_products
from .equipment_inputs import EquipmentSelection
from .errors import VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .product_sources import ProductSources
from .records import Actor, Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace


class EquipmentKernel:
    kind = "qualify_woo_equipment_v1"
    models = {"task": kind, "facts": "cited_quantity_basis_v1"}

    def __init__(self, workspace: Workspace, products: ProductSources) -> None:
        self.workspace, self.products = workspace, products
        self.runtime = RuntimeSnapshot.capture()
        workspace.blobs.put(self.runtime.content)

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
        selection = EquipmentSelection.read(inputs.get("equipment_selection"))
        basis = self.products.equipment_basis()
        selection_products(selection, basis)
        if inputs.get("pv_string_plan") is not None:
            basis["pv_module_inputs"] = self.products.electrical_module_basis()
            # Validate object identities before queueing, then evaluate again
            # against this exact proof inside the durable worker.
            from .pv_string_assessment import assess_pv_strings

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
        output = self.compute(self.workspace.pinned_inputs(manifest), basis, control)
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
        return {"assessment": assess_equipment(inputs, basis)}
