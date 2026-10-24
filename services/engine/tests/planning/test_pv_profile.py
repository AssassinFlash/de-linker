"""Real weather → owned roof-bound asset → frozen worker and energy ledger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from linker_engine.planning.assets import Asset, Assets
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import InvalidInput, NotFound, VersionUnavailable
from linker_engine.planning.frozen_profiles import frozen_profile
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.profile_preview import ProfilePreview
from linker_engine.planning.profile_selections import check_profile_selections
from linker_engine.planning.pv_profile import (
    PURPOSE,
    PvGenerationLimits,
    PvProfileImport,
)
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.workspace import Workspace

from .test_energy_kernel import TOLERANCE, worker
from .test_pv_generation import geometry, parameter_document
from .test_pvgis_tmy import capture, interpretation, raw, request

LIMITS = PvGenerationLimits(
    max_weather_bytes=2_000_000, max_weather_rows=9000, max_array_steps=9000
)
PROVENANCE: Object = {
    "label": "Actual public JRC weather; synthetic roof and explicit scenario parameters",
    "basis": "official_weather_with_synthetic_geometry_and_parameter_fixture",
    "rights_basis": "JRC reuse with attribution; fixture authored here; private retention",
}
SYNTHETIC: Object = {
    "label": "Constant 10 kW load, zero aux, no battery; no customer or released SKU",
    "basis": "synthetic_fixture",
    "rights_basis": "authored by this test; permanent private retention allowed",
}


def project_with_roof(workspace: Workspace, owner: Actor) -> Project:
    geo, parameters = geometry(), parameter_document()
    geo["arrays"][0]["mount_tilt_deg"] = 30
    parameters["arrays"][0]["transposition"] = "perez"
    parameters["arrays"][0]["thermal"].update(a=-3.47, b=-0.0594, delta_t_c=3)
    return workspace.create(
        owner,
        "Actual JRC typical weather / synthetic roof, not equipment qualification",
        {"geometry": geo, "pv_generation": parameters},
        key="roof",
    )


def import_pv(workspace: Workspace, owner: Actor, project: Project) -> Asset:
    return PvProfileImport(Assets(workspace), LIMITS).reference_profile(
        owner,
        project.id,
        project.revision,
        raw(),
        request(),
        capture(),
        interpretation(),
        PROVENANCE,
        key="pv-reference",
    )


def annual_scenario(
    workspace: Workspace, owner: Actor, project: Project, pv: Asset
) -> Project:
    assets = Assets(workspace)
    profiles = {}
    dates = []
    date = datetime(2023, 1, 1, tzinfo=UTC)
    while date < datetime(2024, 1, 1, tzinfo=UTC):
        dates.append(date)
        date += timedelta(hours=1)
    for role, power in (("gross_load", 10), ("aux_ac", 0)):
        content = (
            "time,power\n" + "".join(f"{date.isoformat()},{power}\n" for date in dates)
        ).encode()
        profiles[role] = (
            ProfileImport(assets)
            .csv(
                owner,
                project.id,
                content,
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
                key=role,
            )
            .id
        )
    battery = assets.add(
        owner,
        project.id,
        encode(
            {
                "schema_version": 1,
                "model": "constant_window_single_ac_bus_v1",
                "parameter_basis": "explicit_scenario",
                "usable_window_kwh": 0,
                "charge_ac_kw": 0,
                "discharge_ac_kw": 0,
                "eta_charge": 1,
                "eta_discharge": 1,
                "internal_aux_kw": 0,
                "standing_loss_rate_per_hour": 0,
            }
        ),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": SYNTHETIC},
        key="battery",
    )
    return workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **project.inputs,
            "profile_selections": {
                "schema_version": 1,
                "selected": {"pv_available_ac": pv.id},
            },
            "energy_replay": {
                "schema_version": 1,
                "gross_load_asset_id": profiles["gross_load"],
                "critical_load_asset_id": None,
                "pv_available_asset_id": pv.id,
                "aux_ac_asset_id": profiles["aux_ac"],
                "battery_parameters_asset_id": battery.id,
                "initial_inventory": {
                    "pv_kwh": 0,
                    "grid_kwh": 0,
                    "initial_unknown_kwh": 0,
                    "basis": "synthetic_fixture",
                    "source_note": "no storage or initial energy",
                },
                "schedule": [
                    {
                        "start_utc": "2023-01-01T00:00:00Z",
                        "end_utc": "2024-01-01T00:00:00Z",
                        "mode": "connected",
                        "reserve_kwh": 0,
                        "import_cap_kw": None,
                        "export_cap_kw": 0,
                        "pv_enabled": True,
                        "allow_grid_charge": False,
                    }
                ],
                "controller": "self_consumption_with_reserve_v1",
                "terminal_min_kwh": 0,
            },
        },
        key="annual-scenario",
    )


def test_actual_roof_weather_to_owned_profile_and_frozen_year_ledger(
    workspace: Workspace,
    owner: Actor,
) -> None:
    roof = project_with_roof(workspace, owner)
    asset = import_pv(workspace, owner, roof)
    profile = frozen_profile(
        workspace.blobs, asset.content_sha256, asset.metadata_sha256, None
    )
    dependencies = cast(Object, asset.metadata["dependencies"])
    assert asset.content_sha256 == digest(raw())
    assert profile.source.raw_sha256 == dependencies["pv_model_inputs"]
    witness = workspace.blobs.object(str(dependencies["pv_model_witness"]))
    assert witness["energy_kwh"] == profile.total_kwh
    preview = ProfilePreview(Assets(workspace)).page(
        owner, roof.id, asset.id, offset=0, page_size=2
    )
    assert cast(Object, preview["summary"])["interval_count"] == 8760
    assert cast(Object, preview["summary"])["reconstructed_means"] is True
    assert preview["measurement"] == "pv_available_ac"
    assert cast(Object, preview["source"])["origin"] == "modelled"

    project = annual_scenario(workspace, owner, roof, asset)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=9000)
    service = EnergyService(workspace, kernel, max_attempts=1)
    run = service.evaluate(owner, project.id, project.revision, key="annual-run")
    # Editing the roof must remain possible with a stale source selected, but
    # only the already frozen run may still use that original source.
    edited = cast(dict[str, Any], project.inputs)
    edited["geometry"]["arrays"][0]["mount_tilt_deg"] = 31
    check_profile_selections(Assets(workspace), owner, project.id, project.inputs)
    newer = workspace.revise(
        owner, project.id, project.revision, project.inputs, key="roof-edit"
    )
    with pytest.raises(InvalidInput, match="stale"):
        service.evaluate(owner, project.id, newer.revision, key="stale-pv-run")
    assert worker(workspace, kernel).run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded" and not completed.is_current
    result = completed.result
    assert result is not None and result["revision"] == project.revision
    assert result["input_sha256"] == project.input_sha256
    assert result["scenario_constraint_status"] == "satisfied"
    assert result["interval_count"] == 8760
    metrics = cast(Object, result["metrics"])
    # 10 kW is above this converter's explicit 9.6 kW cap. With no storage,
    # all available solar must serve load; grid supplies the exact remainder.
    assert metrics["gross_load_kwh"] == 87600
    assert metrics["solar_load_kwh"] == pytest.approx(
        profile.total_kwh, rel=0, abs=1e-7
    )
    assert metrics["grid_import_kwh"] == pytest.approx(
        87600 - profile.total_kwh, rel=0, abs=1e-7
    )
    assert cast(Object, result["equipment_release"])["status"] == "not_assessed"
    assert cast(Object, result["country_assessment"])["status"] == "not_assessed"
    pins = cast(Object, result["pinned_assets"])
    for name, value in dependencies.items():
        assert pins[f"pv_available_ac.{name}"] == value
    assert pins["pv_available_ac.raw"] == digest(raw())
    assert len(workspace.runs(owner, project.id)) == 1


def test_foreign_writer_is_rejected_before_weather_parse_or_blob_publication(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project = project_with_roof(workspace, owner)
    before = set(workspace.blobs.directory.rglob("*"))
    with pytest.raises(NotFound):
        PvProfileImport(Assets(workspace), LIMITS).reference_profile(
            Actor("user", "other"),
            project.id,
            project.revision,
            b"bad-weather",
            request(),
            capture(),
            interpretation(),
            PROVENANCE,
            key="forbidden",
        )
    assert set(workspace.blobs.directory.rglob("*")) == before


def test_import_retry_preserves_first_witness_despite_changed_resource_policy(
    workspace: Workspace,
    owner: Actor,
) -> None:
    project = project_with_roof(workspace, owner)
    asset = import_pv(workspace, owner, project)
    tiny = PvGenerationLimits(
        max_weather_bytes=1, max_weather_rows=1, max_array_steps=1
    )
    retry = PvProfileImport(Assets(workspace), tiny).reference_profile(
        owner,
        project.id,
        project.revision,
        raw(),
        request(),
        capture(),
        interpretation(),
        PROVENANCE,
        key="pv-reference",
    )
    assert retry == asset
    with pytest.raises(InvalidInput):
        PvProfileImport(Assets(workspace), tiny).reference_profile(
            owner,
            project.id,
            project.revision,
            raw(),
            request(),
            capture(),
            interpretation(),
            PROVENANCE,
            key="different-command",
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["geometry"]["arrays"][0].update(mount_tilt_deg=31),
        lambda d: d["pv_generation"]["arrays"][0].update(soiling_factor=0.9),
    ],
)
def test_geometry_and_model_parameters_invalidate_new_run_but_load_edit_does_not(
    workspace: Workspace,
    owner: Actor,
    change: Any,
) -> None:
    roof = project_with_roof(workspace, owner)
    asset = import_pv(workspace, owner, roof)
    project = annual_scenario(workspace, owner, roof, asset)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=9000)
    original = kernel.context(owner, project.id, project.inputs)
    # A load source may change without changing the roof's available AC.
    scenario = cast(dict[str, Any], project.inputs)["energy_replay"]
    assets = Assets(workspace)
    load = ProfileImport(assets).csv(
        owner,
        project.id,
        assets.content(owner, project.id, scenario["gross_load_asset_id"]).replace(
            b",10\n", b",11\n"
        ),
        CsvMapping(
            "time",
            "power",
            "gross_load",
            "interval_average_kw",
            "start",
            "UTC",
            "synthetic",
            3600,
            ",",
            ".",
        ),
        SYNTHETIC,
        key="load-edit",
    )
    scenario["gross_load_asset_id"] = load.id
    changed = kernel.context(owner, project.id, project.inputs)
    assert changed.assets["gross_load.raw"] != original.assets["gross_load.raw"]
    assert {
        key: value
        for key, value in changed.assets.items()
        if key.startswith("pv_available_ac.")
    } == {
        key: value
        for key, value in original.assets.items()
        if key.startswith("pv_available_ac.")
    }
    change(project.inputs)
    check_profile_selections(Assets(workspace), owner, project.id, project.inputs)
    with pytest.raises(InvalidInput, match="stale"):
        kernel.context(owner, project.id, project.inputs)
    assert not workspace.runs(owner, project.id)


def test_model_cannot_claim_a_different_project_geometry_via_metadata_stamps(
    workspace: Workspace,
    owner: Actor,
) -> None:
    roof = project_with_roof(workspace, owner)
    asset = import_pv(workspace, owner, roof)
    dependencies = cast(Object, asset.metadata["dependencies"])
    model_inputs = workspace.blobs.object(str(dependencies["pv_model_inputs"]))
    cast(dict[str, Any], model_inputs)["geometry"]["arrays"][0]["mount_tilt_deg"] = 31
    altered = workspace.blobs.put_object(model_inputs)
    forged = Assets(workspace).add(
        owner,
        roof.id,
        raw(),
        "application/json",
        PURPOSE,
        {
            **asset.metadata,
            "dependencies": {**dependencies, "pv_model_inputs": altered},
        },
        key="forged-stamp",
    )
    project = annual_scenario(workspace, owner, roof, forged)
    with pytest.raises(VersionUnavailable, match="does not match the frozen project"):
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000).context(
            owner, project.id, project.inputs
        )
    with pytest.raises(VersionUnavailable, match="cannot be reproduced"):
        frozen_profile(
            workspace.blobs, forged.content_sha256, forged.metadata_sha256, None
        )


def test_missing_witness_and_wrong_consumption_role_are_rejected(
    workspace: Workspace,
    owner: Actor,
) -> None:
    roof = project_with_roof(workspace, owner)
    asset = import_pv(workspace, owner, roof)
    with pytest.raises(InvalidInput, match="consumption"):
        check_profile_selections(
            Assets(workspace),
            owner,
            roof.id,
            {
                "profile_selections": {
                    "schema_version": 1,
                    "selected": {"gross_load": asset.id},
                }
            },
        )
    witness_hash = str(cast(Object, asset.metadata["dependencies"])["pv_model_witness"])
    (workspace.blobs.directory / witness_hash[:2] / witness_hash).unlink()
    with pytest.raises(VersionUnavailable):
        frozen_profile(
            workspace.blobs, asset.content_sha256, asset.metadata_sha256, None
        )
