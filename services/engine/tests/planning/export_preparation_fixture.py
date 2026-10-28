"""Export actual worker/publication views for native consumer regression fixtures.

Uses the retained real TMY and explicit synthetic model/roof with a simulated
provider adapter. Never connects to a live service, account, or project store.

The export is reproducible: identifiers and clock values come from a fixed
sequence, so two runs produce identical bytes and a fixture diff means the
saved objects changed rather than that a random ID did.

Every key of the browser fixture is produced here, one saved workflow at a
time: weather acquisition, PV preparation, the managed roof AC reference, the
direct-beam witness, and the geometric PV profile with its report. A key that
is hand-maintained somewhere else could stop describing the engine the browser
actually consumes without any test noticing.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from conftest import publication_feed, publication_manifest

from linker_engine.app import SOURCE, Services, Settings
from linker_engine.planning import asset_publication, assets
from linker_engine.planning import workspace as workspace_module
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_calculation_sources import calculation_sources
from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.direct_beam_inputs import DirectBeamLimits
from linker_engine.planning.direct_beam_job import DirectBeamKernel
from linker_engine.planning.direct_beam_service import DirectBeamService
from linker_engine.planning.direct_beam_weather import weather_assets, weather_preview
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.geometric_pv_inputs import GeometricPvLimits
from linker_engine.planning.geometric_pv_job import GeometricPvKernel
from linker_engine.planning.geometric_pv_service import GeometricPvService
from linker_engine.planning.http_views import asset_view, project_view, run_view
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.profile_preview import ProfilePreview
from linker_engine.planning.project_input_contracts import (
    DIRECT_BEAM_INPUT_CONTRACT,
    GEOMETRIC_PV_INPUT_CONTRACT,
)
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
)
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.pvgis_reference_kernel import PvgisRoofReferenceKernel
from linker_engine.planning.pvgis_reference_service import PvgisRoofReferenceService
from linker_engine.planning.records import Actor, Run
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.weather_status import weather_status
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_energy_kernel import BATTERY, TOLERANCE
from .test_energy_kernel import PROVENANCE as SYNTHETIC
from .test_geometric_pv import scenario as geometric_scenario
from .test_pv_generation import geometry, parameter_document
from .test_pv_profile import LIMITS, PROVENANCE, project_with_roof
from .test_pvgis_roof_reference import Captures
from .test_pvgis_roof_reference import fixture_inputs as reference_inputs
from .test_pvgis_roof_reference import limits as reference_limits
from .test_pvgis_tmy import capture as weather_capture
from .test_pvgis_tmy import interpretation, raw, request
from .test_weather_kernel import services, source_inputs, valid_adapter
from .test_weather_kernel import worker as weather_worker

ROOT = Path(__file__).resolve().parents[4]
APP = ROOT / "apps" / "planner"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@contextmanager
def fixed_identity() -> Iterator[None]:
    """Pinned clock and identifier sequence for a byte-reproducible export."""
    counter = iter(range(1, 10_000))

    def numbered(_value: str | None = None) -> uuid.UUID:
        return uuid.UUID(int=next(counter))

    originals = [
        (workspace_module, "uuid4"),
        (assets, "uuid4"),
        (asset_publication, "uuid4"),
    ]
    saved = [(module, name, getattr(module, name)) for module, name in originals]
    try:
        for module, name in originals:
            setattr(module, name, numbered)
        yield
    finally:
        for module, name, value in saved:
            setattr(module, name, value)


@contextmanager
def frozen_publication() -> Iterator[None]:
    """Read the loaded generation's manifest instead of a live Woo request.

    The fixture feed marks engineering readiness false because it is a copy of
    the live product publication; the export declares the reference module
    prepared exactly as the consumer tests do before reading it.
    """
    from linker_engine.publication import Publication

    def manifest(self: Publication) -> Any:
        value = publication_manifest(self.feed)
        for row in value["products"]:
            row["ready"]["engineering"] = True
        return value

    original = Publication.read
    Publication.read = manifest  # type: ignore[method-assign]
    try:
        yield
    finally:
        Publication.read = original  # type: ignore[method-assign]


def product_sources(directory: Path) -> ProductSources:
    """The site's own loader over the real fixture feed, without any request."""
    feed_path = directory / "published-feed.json"
    feed_path.write_text(
        json.dumps(
            publication_feed(
                json.loads((FIXTURES / "feed.json").read_text()),
                json.loads((FIXTURES / "compatibility.json").read_text()),
            )
        )
    )
    loaded = Services(
        Settings(
            feed=feed_path,
            compatibility=FIXTURES / "compatibility.json",
            cache=directory / "cache",
        ),
        SOURCE,
    )
    return ProductSources(lambda: loaded)


def capture() -> Object:
    with TemporaryDirectory(prefix="p548-preparation-fixture-") as directory:
        with fixed_identity():
            return _capture(Path(directory))


def _capture(directory: Path) -> Object:
    workspace = Workspace(directory / "private", clock=Clock(1_700_000_000.0))
    owner = Actor("user", "native-preparation-synthetic-fixture")
    bundle = _weather_and_pv(workspace, owner)
    products = product_sources(directory)
    with frozen_publication():
        bundle.update(_pvgis_reference(workspace, owner, products))
        bundle["direct_beam"] = _direct_beam(workspace, owner, products)
        bundle["geometric_pv"] = _geometric_pv(workspace, owner, products)
    return bundle


def _drained(
    workspace: Workspace, registry: Any, run: Run, owner: Actor, name: str
) -> Run:
    worker = weather_worker(workspace, registry)
    worker.name = name
    # One queued evaluation for this scenario: a second claim would be another
    # task, and this export does not create one.
    assert worker.run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded", completed.error
    return completed


def _weather_and_pv(workspace: Workspace, owner: Actor) -> Object:
    project = project_with_roof(workspace, owner)
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, **source_inputs()},
        key="weather-inputs",
    )
    adapter = valid_adapter()
    weather, energy = services(workspace, adapter)
    pv = PvPreparationService(
        workspace, PvReferenceKernel(workspace, LIMITS), max_attempts=2
    )
    registry = service_registry(energy, pv, weather)
    weather_run = weather.evaluate(owner, project.id, project.revision, key="acquire")
    assert weather_worker(workspace, registry).run_once()
    completed = workspace.run(owner, weather_run.id)
    assert completed.result is not None
    asset = completed.result["prepared_asset"]
    assert isinstance(asset, dict) and isinstance(asset["id"], str)
    selected = workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **project.inputs,
            "pv_preparation": {
                "schema_version": 1,
                "weather_asset_id": asset["id"],
            },
        },
        key="select-weather",
    )
    pv_run = pv.evaluate(owner, project.id, selected.revision, key="prepare-pv")
    assert weather_worker(workspace, registry).run_once()
    finished = workspace.run(owner, pv_run.id)
    assert completed.state == finished.state == "succeeded"
    # One official weather request per acquisition; the PV task reuses the
    # retained owned asset instead of fetching anything again.
    assert len(adapter.calls) == 1
    return {
        "schema_version": 1,
        "provider_responses": (
            "Simulated single official HTTPS response with retained original JRC TMY "
            "bytes; no live network or research credentials"
        ),
        "weather_run": run_view(completed),
        "pv_run": run_view(finished),
        "weather_project": project_view(project),
        "pv_project": project_view(selected),
        "weather_status": weather_status(workspace, owner, weather_run.id),
    }


def _pvgis_reference(
    workspace: Workspace, owner: Actor, products: ProductSources
) -> Object:
    basis = products.module_basis()
    assert isinstance(basis, dict)
    values = reference_inputs(basis)
    project = workspace.create(
        owner, "Synthetic multi-array reference", values, key="reference"
    )
    kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        reference_limits(),
        max_array_steps=20_000,
        transport_factory=Captures,
    )
    service = PvgisRoofReferenceService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    registry = service_registry(energy, None, pvgis_reference=service)
    run = service.evaluate(owner, project.id, project.revision, key="reference-run")
    completed = _drained(workspace, registry, run, owner, "reference-worker")
    return {
        "pvgis_reference_run": run_view(completed),
        "pvgis_reference_project": project_view(project),
    }


def _direct_beam(
    workspace: Workspace, owner: Actor, products: ProductSources
) -> Object:
    template = cast(Object, products.module_basis()["module"])
    roof = geometry()
    identifier = roof["module_specs"][0]["id"]
    roof["module_specs"] = [
        {**cast(Object, template["specification"]), "id": identifier}
    ]
    project = workspace.create(
        owner,
        "Synthetic owned direct-beam fixture",
        {"geometry": roof},
        key="beam-roof",
    )
    owned = Assets(workspace)
    source = WeatherImport(owned, LIMITS).tmy(
        owner,
        project.id,
        PvSource(
            raw(), request(), weather_capture(), interpretation(), encode(PROVENANCE)
        ),
        key="beam-weather",
    )
    inputs: Object = {
        **project.inputs,
        "direct_beam_visibility": {
            "schema_version": 1,
            "weather_asset_id": source.id,
            "row_indices": [0, 12],
            "sampling": {"coarse_cells_per_edge": 1, "fine_cells_per_edge": 2},
        },
    }
    project = workspace.revise(
        owner,
        project.id,
        1,
        inputs,
        key="beam-selection",
        input_contract=DIRECT_BEAM_INPUT_CONTRACT,
    )
    # Explicit tiny diagnostic resource policy, not an engineering recommendation.
    kernel = DirectBeamKernel(
        workspace,
        LIMITS,
        DirectBeamLimits(
            max_selected_rows=2,
            max_samples=10000,
            max_ray_face_checks=100000,
            max_bounds_checks=100000,
            index_leaf_size=4,
        ),
        products=products,
    )
    service = DirectBeamService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    reports = ReportService(
        workspace, ReportKernel(workspace, products), max_attempts=1
    )
    registry = service_registry(energy, None, reports=reports, direct_beam=service)
    run = service.evaluate(owner, project.id, 2, key="beam-visibility")
    completed = _drained(workspace, registry, run, owner, "beam-worker")
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
        direct_beam_run_id=run.id,
    )
    report = reports.evaluate(owner, project.id, 2, options, key="beam-report")
    report_run = _drained(workspace, registry, report, owner, "beam-report-worker")
    # The saved views are captured for the revision the calculation used. A
    # later unrelated edit then makes those runs historical, which is the state
    # the browser shows its "earlier saved roof" notice for.
    saved = project_view(project)
    inputs = {
        **cast(Object, saved["inputs"]),
        "project_note": "A later unrelated edit",
    }
    workspace.revise(
        owner,
        project.id,
        2,
        inputs,
        key="beam-later-edit",
        input_contract=DIRECT_BEAM_INPUT_CONTRACT,
    )
    # Re-read both runs: `is_current` is decided against the project revision
    # at read time, not when the run was fetched.
    saved_run = workspace.run(owner, completed.id)
    saved_report = workspace.run(owner, report_run.id)
    return {
        "provenance": {
            "method": (
                "read-only native Workspace run/project/run views; the preview is the "
                "same retained weather document the daylight witness reads"
            ),
            "new_job_or_model_call": False,
        },
        "project": saved,
        "run": run_view(saved_run),
        "report_run": run_view(saved_report),
        "weather_assets": weather_assets(
            owned, owner, project.id, offset=0, page_size=100
        ),
        "weather_preview": weather_preview(
            owned, owner, project.id, source.id, LIMITS, offset=0, page_size=2
        ),
        "report_options": options.model_dump(mode="json"),
        "visibility_limits": kernel.limits.model_dump(mode="json"),
        "module_template": template,
        "weather_asset": asset_view(source),
    }


def _geometric_pv(
    workspace: Workspace, owner: Actor, products: ProductSources
) -> Object:
    template = cast(Object, products.module_basis()["module"])
    roof, parameters = geometry(), parameter_document()
    roof["module_specs"] = [{**cast(Object, template["specification"]), "id": "module"}]
    roof["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    parameters["modules"] = [
        {**cast(Object, template["parameters"]), "module_spec_id": "module"}
    ]
    project = workspace.create(
        owner,
        "Actual weather / synthetic one-module geometric scenario",
        {"geometry": roof},
        key="geometric-create",
    )
    weather_asset = WeatherImport(Assets(workspace), LIMITS).tmy(
        owner,
        project.id,
        PvSource(
            raw(), request(), weather_capture(), interpretation(), encode(PROVENANCE)
        ),
        key="geometric-weather",
    )
    options = geometric_scenario(parameters).model_copy(
        update={"weather_asset_id": weather_asset.id}
    )
    project = workspace.revise(
        owner,
        project.id,
        1,
        {
            **project.inputs,
            "geometric_pv_preparation": options.model_dump(mode="json"),
        },
        key="geometric-parameters",
        input_contract=GEOMETRIC_PV_INPUT_CONTRACT,
    )
    before_project = project_view(project)
    # Full 8760 source / one synthetic module / explicit 1+2 grids: 43800
    # worst-case samples. These limits are this diagnostic's work policy.
    kernel = GeometricPvKernel(
        workspace,
        LIMITS,
        GeometricPvLimits(
            max_module_steps=9000,
            max_samples=45000,
            max_ray_face_checks=1_000_000,
            max_bounds_checks=1_000_000,
            index_leaf_size=2,
        ),
        products=products,
    )
    service = GeometricPvService(workspace, kernel, max_attempts=1)
    reports = ReportService(
        workspace, ReportKernel(workspace, products), max_attempts=1
    )
    registry = service_registry(
        EnergyService(
            workspace,
            EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
            max_attempts=1,
        ),
        None,
        reports=reports,
        geometric_pv=service,
    )
    run = service.evaluate(owner, project.id, 2, key="full-geometric")
    completed = _drained(workspace, registry, run, owner, "geometric-worker")
    assert completed.result is not None
    prepared = Assets(workspace).get(
        owner, project.id, str(cast(Object, completed.result["prepared_asset"])["id"])
    )
    previews = ProfilePreview(Assets(workspace))
    adopted = _adopt_geometric_energy(workspace, owner, products, project, prepared)
    report = reports.evaluate(
        owner,
        project.id,
        adopted.revision,
        ReportOptions(
            locale="de",
            pv_run_id=completed.id,
            energy_run_id=adopted.id,
            equipment_run_id=None,
            logo=None,
        ),
        key="geometric-report",
    )
    report_run = _drained(workspace, registry, report, owner, "geometric-report-worker")
    return {
        "project": before_project,
        "run": run_view(completed),
        "weather_asset": asset_view(weather_asset),
        "profile_asset": asset_view(prepared),
        "profile_preview": previews.page(
            owner, project.id, prepared.id, offset=3995, page_size=2
        ),
        "profile_preview_initial": previews.page(
            owner, project.id, prepared.id, offset=0, page_size=2
        ),
        "report_run": run_view(report_run),
        "run_assistant": assistant_context(
            workspace, owner, project.id, completed.revision, [completed.id], "en"
        ),
        "report_run_assistant": assistant_context(
            workspace, owner, project.id, report_run.revision, [report_run.id], "en"
        ),
        "calculation_sources": calculation_sources(workspace, report_run),
        "source_note": (
            "Actual retained complete weather; synthetic one-module layout and declared "
            "scenario; native task/asset/report, not site/equipment approval"
        ),
    }


def _adopt_geometric_energy(
    workspace: Workspace,
    owner: Actor,
    products: ProductSources,
    project: Any,
    prepared: Any,
) -> Run:
    """A two-hour replay over the retained complete-year profile."""
    owned = Assets(workspace)
    imported: dict[str, str] = {}
    for role, power in (("gross_load", 2), ("aux_ac", 0)):
        data = (
            f"time,power\n2023-06-16T11:00:00Z,{power}\n2023-06-16T12:00:00Z,{power}\n"
        ).encode()
        imported[role] = (
            ProfileImport(owned)
            .csv(
                owner,
                project.id,
                data,
                CsvMapping(
                    "time",
                    "power",
                    cast(Measurement, role),
                    "interval_average_kw",
                    "start",
                    "UTC",
                    "synthetic",
                    3600,
                    ",",
                    ".",
                ),
                SYNTHETIC,
                key="geometric-" + role,
            )
            .id
        )
    battery = owned.add(
        owner,
        project.id,
        encode(
            {**BATTERY, "usable_window_kwh": 0, "charge_ac_kw": 0, "discharge_ac_kw": 0}
        ),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": SYNTHETIC},
        key="geometric-battery",
    )
    project = workspace.revise(
        owner,
        project.id,
        2,
        {
            **project.inputs,
            "profile_selections": {
                "schema_version": 1,
                "selected": {"pv_available_ac": prepared.id},
            },
            "energy_replay": {
                "schema_version": 1,
                "gross_load_asset_id": imported["gross_load"],
                "aux_ac_asset_id": imported["aux_ac"],
                "critical_load_asset_id": None,
                "pv_available_asset_id": prepared.id,
                "battery_parameters_asset_id": battery.id,
                "initial_inventory": {
                    "pv_kwh": 0,
                    "grid_kwh": 0,
                    "initial_unknown_kwh": 0,
                    "basis": "synthetic_fixture",
                    "source_note": "No battery",
                },
                "schedule": [
                    {
                        "start_utc": "2023-06-16T11:00:00Z",
                        "end_utc": "2023-06-16T13:00:00Z",
                        "mode": "connected",
                        "reserve_kwh": 0,
                        "import_cap_kw": None,
                        "export_cap_kw": None,
                        "pv_enabled": True,
                        "allow_grid_charge": False,
                    }
                ],
                "controller": "self_consumption_with_reserve_v1",
                "terminal_min_kwh": 0,
            },
        },
        key="geometric-adopt",
        input_contract=GEOMETRIC_PV_INPUT_CONTRACT,
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    run = energy.evaluate(owner, project.id, project.revision, key="geometric-energy")
    return _drained(
        workspace, service_registry(energy, None), run, owner, "energy-worker"
    )


def rendered() -> str:
    """The exporter's own serialization of the fixture document.

    The planner package owns this file's whitespace and formats it with
    Prettier, so a regeneration is followed by that formatter. This function
    exists so the two agree on the data and the regenerating command is one
    line.
    """
    return json.dumps(capture(), ensure_ascii=False, indent="\t") + "\n"


if __name__ == "__main__":
    target = APP / "tests" / "fixtures" / "preparation-flow.json"
    target.write_text(rendered())
    print(target)
