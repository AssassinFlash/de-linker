"""Real JRC originals plus independent temporal/unit and rejection checks."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Json, Object, digest, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import Conflict, InvalidInput, NotFound
from linker_engine.planning.frozen_profiles import frozen_profile
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.pvgis_import import PvgisImport, PvgisParseLimits
from linker_engine.planning.pvgis_metadata import check_metadata
from linker_engine.planning.pvgis_profile import PvgisInterpretation, pvgis_profile
from linker_engine.planning.pvgis_request import PvgisRequest
from linker_engine.planning.pvgis_response import PvgisCapture, PvgisSeries, read_pvgis
from linker_engine.planning.records import Actor
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

SAMPLES = Path(__file__).resolve().parents[4] / "docs/research/2026-10-23-pv-inputs/raw"
PROVENANCE: Object = {
    "label": "European Commission, Joint Research Centre, PVGIS 5.3",
    "basis": "actual public Berlin 2020 model response; not measured generation",
    "rights_basis": "PVGIS usage conditions section 1 permits unrestricted use; source retained",
    "rights_url": "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/usage-conditions-data-protection_en",
}
LIMITS = PvgisParseLimits(max_bytes=2_000_000, max_rows=9000)


def request(database: str = "PVGIS-ERA5") -> PvgisRequest:
    return PvgisRequest.read(
        {
            "schema_version": 1,
            "api_version": "5.3",
            "radiation_database": database,
            "latitude_deg": 52.52,
            "longitude_deg": 13.405,
            "start_year": 2020,
            "end_year": 2020,
            "peak_power_kwp": 1,
            "system_loss_percent": 14,
            "pv_technology": "crystSi",
            "mounting_place": "free",
            "tilt_deg": 10,
            "azimuth_north_clockwise_deg": 180,
            "use_terrain_horizon": True,
        }
    )


def capture(index: int = 0) -> PvgisCapture:
    record = json.loads((SAMPLES / "sample-provenance.json").read_bytes())[index]
    return PvgisCapture.read(
        {
            "schema_version": 1,
            "requested_url": record["providerURL"],
            "loaded_url": record["loadedURL"],
            "status": record["httpStatus"],
            "content_type": record["contentType"],
            "received_at_utc": record["loadedTime"],
            "capture_basis": record["capture"],
            "source_identifiers": {
                "apify_run": record["apifyRun"],
                "apify_dataset": record["apifyDataset"],
                "apify_record": record["apifyRecord"],
            },
        }
    )


def interpretation(*, sarah: bool = False) -> PvgisInterpretation:
    return PvgisInterpretation(
        schema_version=1,
        temporal_policy="sample_value_over_containing_utc_hour_v1"
        if sarah
        else "era5_centered_hourly_means_v1",
        output_role="pv_available_ac",
        system_power_policy="provider_system_output_no_second_loss_chain",
    )


def raw(*, sarah: bool = False) -> bytes:
    name = "sarah3" if sarah else "era5"
    return (SAMPLES / f"{name}-berlin-2020.seriescalc.json").read_bytes()


def parse(
    content: bytes, req: PvgisRequest | None = None, cap: PvgisCapture | None = None
) -> PvgisSeries:
    return read_pvgis(
        content,
        request() if req is None else req,
        capture() if cap is None else cap,
        max_bytes=LIMITS.max_bytes,
        max_rows=LIMITS.max_rows,
    )


def test_exact_provider_original_era5_leap_year_and_independent_decimal_integral() -> (
    None
):
    content = raw()
    assert (
        digest(content)
        == "9c0b24cf9828cac4c118c4695922fcbbb7aa7213ae80350019f67e00e5eaf6ca"
    )
    native = parse(content)
    profile = pvgis_profile(native, interpretation())
    # Independent original-file Decimal sum is recorded in sample-validation.
    # No 14% or inverter efficiency is applied again to P.
    assert profile.total_kwh == pytest.approx(946.43692, abs=1e-10)
    assert len(native.hours) == len(profile.intervals) == 8784
    assert profile.intervals[0].start == datetime(2020, 1, 1, tzinfo=UTC)
    assert profile.intervals[-1].end == datetime(2021, 1, 1, tzinfo=UTC)
    assert (
        sum(item.start.date().isoformat() == "2020-02-29" for item in profile.intervals)
        == 24
    )
    assert all(item.hours == 1 for item in profile.intervals)
    assert native.value_semantics == "centered_hourly_mean"
    assert profile.reconstructed_means is False
    assert profile.source.origin == "modelled"
    assert profile.source.native_max_interval_seconds == 3600
    assert profile.measurement == "pv_available_ac"


def test_sarah_generic_metadata_does_not_override_instantaneous_semantics() -> None:
    content = raw(sarah=True)
    assert (
        digest(content)
        == "bfaeeebf8257067e90e9571551d8b31063ce8d5e6277f1ab81e6ab953369af39"
    )
    native = parse(content, request("PVGIS-SARAH3"), capture(1))
    assert native.value_semantics == "instantaneous_sample"
    assert native.hours[0].timestamp == datetime(2020, 1, 1, 0, 11, tzinfo=UTC)
    assert b'"timestamp":"hourly averages"' in native.provider_metadata_json
    with pytest.raises(InvalidInput, match="explicit reconstruction"):
        pvgis_profile(native, interpretation())
    profile = pvgis_profile(native, interpretation(sarah=True))
    assert profile.total_kwh == pytest.approx(979.72921, abs=1e-10)
    assert profile.reconstructed_means is True
    transform = profile.transformations[0].document()
    assert transform["energy_preservation_claim"] is False
    assert transform["native_value_semantics"] == "instantaneous_sample"
    assert (
        transform["interval_assignment_basis"]
        == "explicit_model_policy_not_provider_interval_definition"
    )
    assert native.hours[0].timestamp.minute == 11  # never rewritten in the source


def test_request_keeps_full_precision_azimuth_and_every_explicit_parameter() -> None:
    values = request().document()
    values.update(
        latitude_deg=40.416775, longitude_deg=-3.703790, azimuth_north_clockwise_deg=90
    )
    req = PvgisRequest.read(values)
    parameters = req.parameters()
    assert parameters["lat"] == "40.416775" and parameters["lon"] == "-3.70379"
    assert parameters["aspect"] == "-90.0"
    assert parameters["optimalinclination"] == parameters["optimalangles"] == "0"
    assert parameters["startyear"] == parameters["endyear"] == "2020"
    assert parameters["loss"] == "14.0" and parameters["peakpower"] == "1.0"
    assert req.matches_url(req.url)
    assert request().matches_url(capture().requested_url)  # 1/1.0 numeric spellings
    for url in (
        req.url + "&lat=40.416775",
        req.url + "&browser=1",
        req.url.replace("https:", "http:"),
        req.url.replace("v5_3", "v5_2"),
        req.url.replace("re.jrc.ec.europa.eu", "example.com"),
        req.url.replace("peakpower=1.0", "peakpower=2"),
        req.url + "#ignored",
        req.url.replace("loss=14.0", "loss=NaN"),
    ):
        assert not req.matches_url(url)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("start_year", True),
        ("end_year", 2019),
        ("api_version", "5.4"),
        ("latitude_deg", 90.1),
        ("longitude_deg", -180.1),
        ("tilt_deg", -1),
        ("azimuth_north_clockwise_deg", 360),
        ("system_loss_percent", -1),
        ("peak_power_kwp", 0),
        ("use_terrain_horizon", 1),
        ("peak_power_kwp", float("nan")),
    ],
)
def test_invalid_request_does_not_fall_back_to_provider_defaults(
    field: str, value: Json
) -> None:
    values = request().document()
    values[field] = value
    with pytest.raises(InvalidInput):
        PvgisRequest.read(values)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("inputs", "location", "longitude"), 13.4),
        (("inputs", "meteo_data", "radiation_db"), "PVGIS-SARAH3"),
        (("inputs", "meteo_data", "year_min"), 2019),
        (("inputs", "meteo_data", "use_horizon"), False),
        (("inputs", "pv_module", "technology"), "c-Si2025"),
        (("inputs", "pv_module", "peak_power"), 2),
        (("inputs", "pv_module", "system_loss"), 0),
        (("inputs", "mounting_system", "fixed", "azimuth", "value"), 180),
        (("inputs", "mounting_system", "fixed", "slope", "optimal"), True),
        (("inputs", "mounting_system", "fixed", "type"), "building-integrated"),
        (("meta", "outputs", "hourly", "variables", "P", "units"), "kW"),
    ],
)
def test_wrong_response_identity_or_unit_is_rejected(
    path: tuple[str, ...], value: Json
) -> None:
    values = json.loads(raw())
    parent = values
    for name in path[:-1]:
        parent = parent[name]
    parent[path[-1]] = value
    with pytest.raises(InvalidInput):
        parse(encode(cast(Object, values)))


@pytest.mark.parametrize(
    "bad", ["gap", "duplicate", "nan", "negative", "bool", "bad_flag", "wrong_minute"]
)
def test_bad_rows_are_not_sorted_zero_filled_or_accepted_as_complete(bad: str) -> None:
    values = json.loads(raw())
    rows = values["outputs"]["hourly"]
    if bad == "gap":
        rows.pop(100)
    elif bad == "duplicate":
        rows[100]["time"] = rows[99]["time"]
    elif bad == "nan":
        rows[100]["P"] = float("nan")
    elif bad == "negative":
        rows[100]["P"] = -1
    elif bad == "bool":
        rows[100]["P"] = True
    elif bad == "bad_flag":
        rows[100]["Int"] = 2
    else:
        rows[100]["time"] = "20200105:0400"
    with pytest.raises(InvalidInput):
        parse(json.dumps(values).encode())


def test_capture_rejection_duplicate_json_and_resource_limits() -> None:
    for changes in (
        {"content_type": "text/html"},
        {"status": 429},
        {"loaded_url": "https://example.com/"},
    ):
        with pytest.raises(InvalidInput):
            parse(raw(), cap=PvgisCapture.read({**capture().document(), **changes}))
    with pytest.raises(InvalidInput, match="duplicate"):
        parse(b'{"inputs":{},"inputs":{}}')
    for limits in (
        {"max_bytes": 1, "max_rows": 9000},
        {"max_bytes": 2_000_000, "max_rows": 8760},
    ):
        with pytest.raises(InvalidInput):
            read_pvgis(raw(), request(), capture(), **limits)


def test_reconstructed_radiation_quality_and_mutable_capture_are_not_lost() -> None:
    values = json.loads(raw())
    values["outputs"]["hourly"][100]["Int"] = 1
    cap = capture()
    native = parse(encode(cast(Object, values)), cap=cap)
    before = native.source_document()
    cap.source_identifiers["apify_run"] = "changed-after-parse"
    assert native.source_document() == before
    assert before["radiation_reconstructed_rows"] == 1


def test_owned_import_receipt_freezes_raw_metadata_and_can_replay_without_tzif(
    workspace: Workspace, owner: Actor
) -> None:
    project = workspace.create(owner, "public provider reference", {}, key="create")
    importer = PvgisImport(Assets(workspace), LIMITS)
    asset = importer.system_profile(
        owner,
        project.id,
        raw(),
        request(),
        capture(),
        interpretation(),
        PROVENANCE,
        key="provider",
    )
    assert asset.content_sha256 == digest(raw())
    assert "timezone_rules_sha256" not in asset.metadata
    # A stricter deployment ceiling does not change the first accepted receipt.
    retry = PvgisImport(Assets(workspace), PvgisParseLimits(max_bytes=1, max_rows=1))
    assert (
        retry.system_profile(
            owner,
            project.id,
            raw(),
            request(),
            capture(),
            interpretation(),
            PROVENANCE,
            key="provider",
        )
        == asset
    )
    replayed = frozen_profile(
        workspace.blobs, asset.content_sha256, asset.metadata_sha256, None
    )
    assert replayed.total_kwh == pytest.approx(946.43692, abs=1e-10)
    assert replayed.source.raw_sha256 == asset.content_sha256
    with pytest.raises(Conflict):
        importer.system_profile(
            owner,
            project.id,
            raw(),
            request(),
            capture(),
            interpretation(),
            {**PROVENANCE, "basis": "different command"},
            key="provider",
        )
    for actor in (Actor("guest", "other"), Actor("team", "read-only")):
        with pytest.raises(NotFound):
            importer.system_profile(
                actor,
                project.id,
                b"invalid before parsing",
                request(),
                capture(),
                interpretation(),
                PROVENANCE,
                key="foreign",
            )


def test_actual_provider_metadata_mappings_for_all_other_technologies() -> None:
    probes = json.loads((SAMPLES / "technology-mapping-probes.json").read_bytes())
    for probe in probes:
        parameters = probe["requestParameters"]
        req = PvgisRequest.read(
            {
                **request().document(),
                "pv_technology": parameters["pvtechchoice"][0],
                "mounting_place": parameters["mountingplace"][0],
            }
        )
        assert req.matches_url(probe["requestURL"])
        metadata = {"inputs": probe["inputs"], "meta": probe["meta"]}
        if req.pv_technology == "Unknown":
            # This actual response echoes "Unknown type" but supplies no P
            # unit. A label mapping is not evidence that PV output exists.
            with pytest.raises(InvalidInput, match="P.units"):
                check_metadata(metadata, req)
        else:
            check_metadata(metadata, req)


def test_actual_north_boundary_response_changes_one_degree_and_is_rejected() -> None:
    probe = json.loads((SAMPLES / "north-nohorizon-probe.json").read_bytes())[0]
    req = PvgisRequest.read(
        {
            **request().document(),
            "azimuth_north_clockwise_deg": 0,
            "use_terrain_horizon": False,
        }
    )
    assert req.matches_url(probe["requestURL"])
    assert req.parameters()["aspect"] == "-180.0"
    assert probe["inputs"]["mounting_system"]["fixed"]["azimuth"]["value"] == -179
    assert probe["inputs"]["meteo_data"]["use_horizon"] is False
    assert "horizon_data" not in probe["inputs"]["meteo_data"]
    with pytest.raises(InvalidInput, match="azimuth.value"):
        check_metadata({"inputs": probe["inputs"], "meta": probe["meta"]}, req)


def test_actual_full_year_provider_asset_through_durable_worker_and_energy_ledger(
    workspace: Workspace, owner: Actor
) -> None:
    """Real PV input with explicitly synthetic load/battery, not SKU validation."""
    project = workspace.create(
        owner,
        "Berlin public PVGIS reference / synthetic constant load",
        {},
        key="create",
    )
    assets = Assets(workspace)
    pv = PvgisImport(assets, LIMITS).system_profile(
        owner,
        project.id,
        raw(),
        request(),
        capture(),
        interpretation(),
        PROVENANCE,
        key="pv",
    )
    synthetic: Object = {
        "label": "Analytic constant 1 kW load, zero aux, no battery; not a customer/SKU",
        "basis": "synthetic_fixture",
        "rights_basis": "created by this test; permanent private retention allowed",
    }
    # Independent calendar traversal, not the provider adapter's constructed axis.
    dates = []
    instant = datetime(2020, 1, 1, tzinfo=UTC)
    while instant < datetime(2021, 1, 1, tzinfo=UTC):
        dates.append(instant)
        instant += timedelta(hours=1)
    profiles = {}
    for role, power in (("gross_load", 1), ("aux_ac", 0)):
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
                synthetic,
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
        {"retention": "permanent", "provenance": synthetic},
        key="battery",
    )
    project = workspace.revise(
        owner,
        project.id,
        1,
        {
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
                    "source_note": "no battery / no initial energy",
                },
                "schedule": [
                    {
                        "start_utc": "2020-01-01T00:00:00Z",
                        "end_utc": "2021-01-01T00:00:00Z",
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
            }
        },
        key="scenario",
    )
    kernel = EnergyKernel(workspace, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=9000)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 2, key="run"
    )
    workspace.revise(
        owner, project.id, 2, {"note": "new revision after queue"}, key="newer"
    )
    worker = Worker(
        Jobs(workspace),
        "actual-pvgis-test",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert worker.run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded" and not completed.is_current
    result = completed.result
    assert result is not None and result["revision"] == 2
    assert result["input_sha256"] == project.input_sha256
    assert result["scenario_constraint_status"] == "satisfied"
    energy = cast(Object, result["metrics"])
    assert energy["gross_load_kwh"] == 8784
    # Original file max P is 727.73 W < constant load of 1 kW: all PV goes
    # directly to load. These expected totals need no dispatch implementation.
    assert energy["solar_load_kwh"] == pytest.approx(946.43692, abs=1e-9)
    assert energy["grid_import_kwh"] == pytest.approx(7837.56308, abs=1e-9)
    assert cast(Object, energy["solar_autarky"])["value"] == pytest.approx(
        946.43692 / 8784
    )
    assert result["interval_count"] == 8784
    assert cast(Object, result["pinned_assets"])["pv_available_ac.raw"] == digest(raw())
    assert "pv_available_ac.timezone" not in cast(Object, result["pinned_assets"])
    periods = cast(
        list[Object],
        cast(Object, result["profile_interpretation"])["operating_periods"],
    )
    pv_notes = cast(Object, cast(Object, periods[0]["profiles"])["pv_available_ac"])
    assert cast(Object, pv_notes["source"])["origin"] == "modelled"
    assert (
        cast(Object, cast(Object, pv_notes["source"])["details"])[
            "native_value_semantics"
        ]
        == "centered_hourly_mean"
    )
