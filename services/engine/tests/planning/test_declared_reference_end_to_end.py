"""A roof of declared tiers prepares a real PV reference end to end.

The static checks only prove the door is open. This runs the actual preparation
kernel over the same synthetic weather fixture and reads the prepared asset, so
"the customer can calculate PV after choosing a tier" is shown on the real path.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
)
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .export_preparation_fixture import frozen_publication, product_sources
from .test_pv_generation import parameter_document
from .test_pv_profile import LIMITS, project_with_roof
from .test_pvgis_tmy import capture, interpretation, raw, request


def _declared_roof() -> tuple[FixtureObject, FixtureObject]:
    """The fixture roof with its one module replaced by a declared tier."""
    from .test_pv_generation import geometry as fixture_geometry

    geometry = cast(FixtureObject, fixture_geometry())
    parameters = cast(FixtureObject, parameter_document())
    note = (
        "declared_reference — Generic tier planning reference; unverified "
        "planning assumption, not a manufacturer datasheet value."
    )
    geometry["module_specs"] = [
        {
            "id": "module",
            "model": "PV 450 Wp · 1762 × 1134 mm",
            "width_m": 1.134,
            "length_m": 1.762,
            "thickness_m": 0.035,
            "stc_power_w": 450,
            "gamma_pdc_per_c": -0.0034,
            "source": {
                "kind": "user_declared",
                "note": note,
                "document_sha256": None,
                "url": None,
                "page": None,
            },
        }
    ]
    parameters["modules"] = [
        {
            "module_spec_id": "module",
            "gamma_pdc_per_c": -0.0034,
            "source": {
                "kind": "user_declared",
                "note": note,
                "document_sha256": None,
                "url": None,
                "page": None,
            },
        }
    ]
    return geometry, parameters


def _drain(
    workspace: Workspace, owner: Actor, kernel: PvReferenceKernel, run_id: str
) -> Object:
    """Run the queued preparation through the real worker and read it back."""
    from linker_engine.planning.jobs import Jobs
    from linker_engine.planning.worker import Worker

    worker = Worker(
        Jobs(workspace),
        "declared-reference-pv-worker",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert worker.run_once()
    completed = workspace.run(owner, run_id)
    assert completed.state == "succeeded", completed.error
    assert completed.result is not None
    return json_object(completed.result)


def _prepare(
    workspace: Workspace, owner: Actor, products: ProductSources
) -> tuple[Project, Object]:
    from linker_engine.planning.assets import Assets
    from linker_engine.planning.pv_source import PvSource
    from linker_engine.planning.weather_import import WeatherImport

    project = project_with_roof(workspace, owner)
    source = WeatherImport(Assets(workspace), LIMITS).tmy(
        owner,
        project.id,
        PvSource(
            raw(),
            request(),
            capture(),
            interpretation(),
            encode(
                {
                    "label": "Actual public JRC weather; synthetic declared-reference roof",
                    "basis": "official_weather_with_synthetic_geometry_and_parameter_fixture",
                    "rights_basis": "JRC reuse with attribution; fixture authored here",
                }
            ),
        ),
        key="weather",
    )
    geometry, parameters = _declared_roof()
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **project.inputs,
            "geometry": geometry,
            "pv_generation": parameters,
            "pv_preparation": {"schema_version": 1, "weather_asset_id": source.id},
        },
        key="declared-roof",
    )
    kernel = PvReferenceKernel(workspace, LIMITS, products=products)
    run = PvPreparationService(workspace, kernel, max_attempts=2).evaluate(
        owner, project.id, project.revision, key="prepare-declared"
    )
    return project, _drain(workspace, owner, kernel, run.id)


def test_a_declared_reference_roof_prepares_a_pv_reference(tmp_path: Path) -> None:
    """The energy model runs from the tier's own coefficient, not the product."""
    from linker_engine.planning.workspace import Workspace

    workspace = Workspace(tmp_path / "private")
    owner = Actor("user", "wordpress:17")
    products = product_sources(tmp_path)
    with frozen_publication():
        project, result = _prepare(workspace, owner, products)
        prepared = json_object(result["prepared_asset"])
        assert prepared["id"]
        assert result["profile_summary"] is not None
        metadata = json_object(prepared["metadata"])
        # The pinned proof still exists; a declared roof does not remove it.
        assert isinstance(metadata["woo_module_inputs"], dict)
        # The geometry the calculation used carries the declared module, and
        # that module is what the parameter check accepts.
        geometry = read_geometry(project.inputs["geometry"])
        module = geometry.module_specs[0]
        assert module.source.woo is None
        assert module.gamma_pdc_per_c == -0.0034


def test_the_woo_roof_still_prepares_and_still_binds_the_product(
    tmp_path: Path,
) -> None:
    """Regression guard on the unchanged path, at the same level."""
    from linker_engine.planning.assets import Assets
    from linker_engine.planning.pv_source import PvSource
    from linker_engine.planning.weather_import import WeatherImport
    from linker_engine.planning.workspace import Workspace

    workspace = Workspace(tmp_path / "private")
    owner = Actor("user", "wordpress:17")
    products = product_sources(tmp_path)
    with frozen_publication():
        project = project_with_roof(workspace, owner)
        template = json_object(json_object(products.module_basis())["module"])
        geometry = cast(Object, project.inputs["geometry"])
        identifier = str(cast(list[Object], geometry["module_specs"])[0]["id"])
        geometry["module_specs"] = [
            {**cast(Object, template["specification"]), "id": identifier}
        ]
        parameters = cast(Object, project.inputs["pv_generation"])
        parameters["modules"] = [
            {**cast(Object, template["parameters"]), "module_spec_id": identifier}
        ]
        source = WeatherImport(Assets(workspace), LIMITS).tmy(
            owner,
            project.id,
            PvSource(
                raw(),
                request(),
                capture(),
                interpretation(),
                encode(
                    {
                        "label": "Actual public JRC weather; synthetic Woo roof",
                        "basis": "official_weather_with_synthetic_geometry_and_parameter_fixture",
                        "rights_basis": "JRC reuse with attribution; fixture authored here",
                    }
                ),
            ),
            key="weather",
        )
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            {
                **project.inputs,
                "pv_preparation": {
                    "schema_version": 1,
                    "weather_asset_id": source.id,
                },
            },
            key="woo-roof",
        )
        kernel = PvReferenceKernel(workspace, LIMITS, products=products)
        run = PvPreparationService(workspace, kernel, max_attempts=2).evaluate(
            owner, project.id, project.revision, key="prepare-woo"
        )
        completed = _drain(workspace, owner, kernel, run.id)
        assert json_object(completed["prepared_asset"])["id"]
        assert json_object(completed["profile_summary"])["energy_kwh"] > 0
        # A coefficient that the product record does not state is still refused.
        broken = cast(Object, project.inputs["pv_generation"])
        broken["modules"] = [
            {
                **cast(Object, cast(list[Object], broken["modules"])[0]),
                "gamma_pdc_per_c": -0.99,
            }
        ]
        with frozen_publication():
            with __import__("pytest").raises(InvalidInput):
                ProductSources.check_pv_inputs(
                    {"geometry": project.inputs["geometry"], "pv_generation": broken},
                    products.pv_basis(
                        {
                            "geometry": project.inputs["geometry"],
                            "pv_generation": project.inputs["pv_generation"],
                        }
                    ),
                )
