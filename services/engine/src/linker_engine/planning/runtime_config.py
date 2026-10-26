"""Explicit deployment settings shared by planning HTTP and its worker.

The file contains no credential. GENIE_SERVICE_TOKEN stays in the service
environment. Limits are operational policy; arithmetic settings are frozen
into each run and are not physical safety/engineering margins.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, model_validator

from .dc_energy_kernel import DcEnergyKernel
from .energy_inputs import Document, Nonnegative, SchemaVersion
from .energy_kernel import EnergyKernel
from .energy_service import EnergyService
from .equipment_kernel import EquipmentKernel
from .equipment_search_kernel import EquipmentSearchKernel
from .equipment_search_limits import EquipmentSearchLimits
from .equipment_service import EquipmentService
from .http_app import HttpLimits
from .numerical_tolerance import Tolerance
from .plant_energy_kernel import PlantEnergyKernel
from .product_sources import ProductSources, worker_product_provider
from .pv_parameters import PvGenerationLimits
from .pv_preparation import PvPreparationService, PvReferenceKernel
from .report_kernel import ReportKernel, ReportService
from .weather_fetch_plan import WeatherFetchLimits
from .weather_kernel import WeatherKernel
from .weather_service import WeatherService
from .workspace import Workspace

type PositiveInteger = Annotated[int, Field(strict=True, gt=0)]


class RuntimeConfig(Document):
    schema_version: SchemaVersion
    directory: str
    max_body_bytes: PositiveInteger
    max_csv_bytes: PositiveInteger
    max_page_size: PositiveInteger
    max_json_depth: PositiveInteger
    max_intervals: PositiveInteger
    max_attempts: PositiveInteger
    absolute_kwh: Nonnegative
    absolute_kw: Nonnegative
    relative: Nonnegative
    # Existing installed policies can run energy alone. Explicit PV limits
    # enable the additional registered executor; no engineering defaults.
    pv_preparation: PvGenerationLimits | None = None
    weather_acquisition: WeatherFetchLimits | None = None
    equipment_search: EquipmentSearchLimits | None = None

    @model_validator(mode="after")
    def absolute_directory(self) -> Self:
        if not Path(self.directory).is_absolute():
            raise ValueError("planning directory must be absolute")
        if self.max_csv_bytes > self.max_body_bytes:
            raise ValueError("CSV limit exceeds the request limit")
        return self

    @classmethod
    def from_environment(cls) -> Self:
        name = os.environ.get("LINKER_PLANNER_CONFIG", "")
        if not name:
            raise ValueError("planning configuration is absent")
        return cls.model_validate_json(Path(name).read_bytes())

    def open(
        self, *, products: ProductSources | None = None
    ) -> tuple[Workspace, EnergyService]:
        workspace = Workspace(Path(self.directory))
        source = products or ProductSources(worker_product_provider)
        kernel = EnergyKernel(
            workspace,
            Tolerance(self.absolute_kwh, self.absolute_kw, self.relative),
            max_intervals=self.max_intervals,
            products=source,
        )
        return workspace, EnergyService(
            workspace,
            kernel,
            max_attempts=self.max_attempts,
            dc_kernel=DcEnergyKernel(
                workspace,
                Tolerance(self.absolute_kwh, self.absolute_kw, self.relative),
                max_intervals=self.max_intervals,
                products=source,
            ),
            plant_kernel=PlantEnergyKernel(
                workspace,
                Tolerance(self.absolute_kwh, self.absolute_kw, self.relative),
                max_intervals=self.max_intervals,
                products=source,
            ),
        )

    def report_service(
        self, workspace: Workspace, *, products: ProductSources | None = None
    ) -> ReportService:
        return ReportService(
            workspace,
            ReportKernel(
                workspace, products or ProductSources(worker_product_provider)
            ),
            max_attempts=self.max_attempts,
        )

    def http_limits(self) -> HttpLimits:
        return HttpLimits(
            self.max_body_bytes,
            self.max_csv_bytes,
            self.max_page_size,
            self.max_json_depth,
        )

    def pv_service(
        self,
        workspace: Workspace,
        *,
        products: ProductSources | None = None,
    ) -> PvPreparationService | None:
        if self.pv_preparation is None:
            return None
        return PvPreparationService(
            workspace,
            PvReferenceKernel(
                workspace,
                self.pv_preparation,
                products=products or ProductSources(worker_product_provider),
            ),
            max_attempts=self.max_attempts,
        )

    def weather_service(self, workspace: Workspace) -> WeatherService | None:
        if self.weather_acquisition is None:
            return None
        return WeatherService(
            workspace,
            WeatherKernel(workspace, self.weather_acquisition),
            max_attempts=self.max_attempts,
        )

    def equipment_service(
        self, workspace: Workspace, *, products: ProductSources | None = None
    ) -> EquipmentService:
        return EquipmentService(
            workspace,
            EquipmentKernel(
                workspace, products or ProductSources(worker_product_provider)
            ),
            max_attempts=self.max_attempts,
        )

    def equipment_search_service(
        self, workspace: Workspace, *, products: ProductSources | None = None
    ) -> EquipmentService | None:
        if self.equipment_search is None:
            return None
        return EquipmentService(
            workspace,
            EquipmentSearchKernel(
                workspace,
                products or ProductSources(worker_product_provider),
                self.equipment_search,
            ),
            max_attempts=self.max_attempts,
        )
