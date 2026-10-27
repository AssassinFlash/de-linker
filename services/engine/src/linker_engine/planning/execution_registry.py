"""One owned worker dispatches only its registered, immutable execution keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .asset_publication import AssetResult
from .canonical import Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import EvaluationRouting, request_execution_key
from .frozen_run import frozen_manifest
from .records import Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace

if TYPE_CHECKING:
    from .energy_service import EnergyService
    from .equipment_service import EquipmentService
    from .pv_preparation import PvPreparationService
    from .pvgis_reference_service import PvgisRoofReferenceService
    from .report_kernel import ReportService
    from .weather_service import WeatherService


def service_registry(
    energy: EnergyService,
    pv: PvPreparationService | None,
    weather: WeatherService | None = None,
    equipment: EquipmentService | None = None,
    equipment_search: EquipmentService | None = None,
    reports: ReportService | None = None,
    pvgis_reference: PvgisRoofReferenceService | None = None,
) -> ExecutionRegistry:
    """One executor-set authority for HTTP, worker startup and operator identity."""
    return ExecutionRegistry(
        *energy.kernels,
        *(() if pv is None else (pv.kernel,)),
        *(() if weather is None else (weather.kernel,)),
        *(() if equipment is None else (equipment.kernel,)),
        *(() if equipment_search is None else (equipment_search.kernel,)),
        *(() if reports is None else (reports.kernel,)),
        *(() if pvgis_reference is None else (pvgis_reference.kernel,)),
    )


class RegisteredKernel(Protocol):
    kind: str
    workspace: Workspace
    runtime: RuntimeSnapshot

    def execution_key(self) -> str: ...

    def __call__(self, lease: Lease, control: Control) -> Object | AssetResult: ...


class ExecutionRegistry:
    def __init__(self, *kernels: RegisteredKernel) -> None:
        if not kernels:
            raise InvalidInput("registered execution kernels required")
        self.workspace = kernels[0].workspace
        self.runtime = kernels[0].runtime
        if any(
            k.workspace is not self.workspace or k.runtime.sha256 != self.runtime.sha256
            for k in kernels
        ):
            raise InvalidInput("registered kernels must share runtime and workspace")
        self._by_key = {k.execution_key(): k for k in kernels}
        if len(self._by_key) != len(kernels) or len({k.kind for k in kernels}) != len(
            kernels
        ):
            raise InvalidInput(
                "unique registered task kinds and execution keys required"
            )
        self._keys = tuple(sorted(self._by_key))

    def execution_key(self) -> str:
        if len(self._keys) == 1:
            return self._keys[0]
        return digest(
            encode(
                {
                    "schema_version": 1,
                    "registered_executors": {
                        kernel.kind: key for key, kernel in self._by_key.items()
                    },
                }
            )
        )

    def routing(self, batch_size: int) -> EvaluationRouting:
        return EvaluationRouting(self.execution_key(), batch_size, self._keys)

    def __call__(self, lease: Lease, control: Control) -> Object | AssetResult:
        control.checkpoint()
        manifest_hash = lease.request.get("manifest_sha256")
        if not isinstance(manifest_hash, str):
            raise VersionUnavailable("evaluation has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        key = request_execution_key(lease.request, manifest, manifest_hash)
        kernel = self._by_key.get(key)
        if kernel is None or kernel.execution_key() != key:
            raise VersionUnavailable("this worker cannot execute the pinned task")
        return kernel(lease, control)
