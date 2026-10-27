"""One managed multi-array reference and its source/permission boundaries."""

from __future__ import annotations

import copy
import io
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from typing import Any

import pytest
import requests
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests.adapters import BaseAdapter
from urllib3.response import HTTPResponse

from linker_engine.planning.assets import Asset, Assets
from linker_engine.planning.canonical import decode_object, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import (
    InvalidInput,
    LeaseLost,
    ProductEvidenceChanged,
)
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.pvgis_reference_artifacts import prepare_reference_asset
from linker_engine.planning.pvgis_reference_download import ReferenceCapture
from linker_engine.planning.pvgis_reference_geometry import reference_plan
from linker_engine.planning.pvgis_reference_http import PvgisReferenceHttp
from linker_engine.planning.pvgis_reference_inputs import PvgisReferenceInputs
from linker_engine.planning.pvgis_reference_journal import PvgisReferenceJournal
from linker_engine.planning.pvgis_reference_kernel import PvgisRoofReferenceKernel
from linker_engine.planning.pvgis_reference_profile import (
    prepared_reference_profile,
    reference_bundle,
    reference_dependencies,
)
from linker_engine.planning.pvgis_reference_service import PvgisRoofReferenceService
from linker_engine.planning.pvgis_reference_transport import PvgisReferenceTransport
from linker_engine.planning.pvgis_request import PvgisRequest
from linker_engine.planning.pvgis_response import PvgisCapture
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
)
from linker_engine.planning.weather_fetch_plan import WeatherFetchLimits
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.publication import Publication

from .conftest import Clock, FixtureObject, json_object
from .test_energy_kernel import TOLERANCE
from .test_official_weather import Reply
from .test_private_http import TOKEN, headers
from .test_pv_generation import geometry
from .test_pvgis import raw
from .test_pvgis import request as sample_request
from .test_weather_deadline import SLOW_BODY


def limits() -> WeatherFetchLimits:
    # Isolated operational test budgets, not provider or engineering limits.
    return WeatherFetchLimits(
        max_response_bytes=8_000_000,
        max_metadata_bytes=100_000,
        max_weather_rows=9000,
        connect_timeout_seconds=5,
        read_timeout_seconds=20,
        max_elapsed_seconds=60,
    )


def settings() -> FixtureObject:
    return {
        "schema_version": 1,
        "model": "pvgis_5_3_roof_ac_reference_v1",
        "radiation_database": "PVGIS-ERA5",
        "year": 2020,
        "pv_technology": "crystSi",
        "mounting_place": "free",
        "system_loss_percent": 14,
        "use_terrain_horizon": True,
    }


class Captures:
    def __init__(self, *, transient_second: bool = False) -> None:
        self.requests: list[PvgisRequest] = []
        self.deadlines: list[float] = []
        self.byte_limits: list[int] = []
        self.transient_second, self.closed = transient_second, False

    def close(self) -> None:
        self.closed = True

    def download(
        self,
        request: PvgisRequest,
        limits: WeatherFetchLimits,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> ReferenceCapture:
        guard()
        self.requests.append(request)
        self.deadlines.append(deadline)
        self.byte_limits.append(limits.max_response_bytes)
        if self.transient_second and len(self.requests) == 2:
            raise WeatherProviderUnavailable("synthetic transient second-array failure")
        # Reuse the retained JRC response structure. The changed input echoes
        # and linear P scaling are explicitly synthetic transport fixtures.
        document = json_object(decode_object(raw()))
        inputs = document["inputs"]
        inputs["location"].update(
            latitude=request.latitude_deg, longitude=request.longitude_deg
        )
        inputs["meteo_data"].update(
            radiation_db=request.radiation_database,
            year_min=request.start_year,
            year_max=request.end_year,
            use_horizon=request.use_terrain_horizon,
        )
        inputs["pv_module"].update(
            technology="c-Si",
            peak_power=request.peak_power_kwp,
            system_loss=request.system_loss_percent,
        )
        fixed = inputs["mounting_system"]["fixed"]
        fixed["slope"]["value"] = request.tilt_deg
        fixed["azimuth"]["value"] = request.azimuth_north_clockwise_deg - 180
        for row in document["outputs"]["hourly"]:
            row["P"] *= request.peak_power_kwp
        return ReferenceCapture(
            encode(document),
            PvgisCapture(
                schema_version=1,
                requested_url=request.url,
                loaded_url=request.url,
                status=200,
                content_type="application/json",
                received_at_utc="2026-10-28T00:00:00Z",
                capture_basis="official_jrc_https_get_original_v1",
                source_identifiers={"provider": "EC_JRC_PVGIS", "api_version": "5.3"},
            ),
        )


def fixture_inputs(basis: FixtureObject) -> FixtureObject:
    layout = geometry()
    layout["module_specs"] = [{**basis["module"]["specification"], "id": "module"}]
    first = layout["arrays"][0]
    first.update(rows=2, columns=5, excluded_slots=[], mount_tilt_deg=10)
    second = copy.deepcopy(first)
    second.update(
        id="other", name="Second synthetic array", origin_uv=[10, 2], mount_tilt_deg=20
    )
    layout["arrays"].append(second)
    return {"geometry": layout, "pvgis_reference": settings()}


def prepared_reference_fixture(
    workspace: Workspace, owner: Actor, products: ProductSources
) -> tuple[Project, Asset]:
    """Reuse the exact producer artifact for consumer tests, without a PV replay."""
    basis = json_object(products.module_basis())
    values = fixture_inputs(basis)
    project = workspace.create(
        owner, "Synthetic reference consumer", values, key="reference-consumer"
    )
    plan = reference_plan(values, workspace.blobs.put_object(basis), limits(), 20_000)
    source = Captures()
    captures = [
        source.download(
            a.request, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
        for a in plan.arrays
    ]
    publication, _ = prepare_reference_asset(
        workspace.blobs, project.id, 1, values, basis, plan, captures
    )
    asset = Assets(workspace).add(
        owner,
        project.id,
        workspace.blobs.read(publication.content_sha256),
        publication.media_type,
        publication.purpose,
        workspace.blobs.object(publication.metadata_sha256),
        key="reference-source",
    )
    return project, asset


def test_managed_reference_freezes_both_arrays_and_refuses_stale_or_partial_use(
    client: TestClient,
    workspace: Workspace,
    owner: Actor,
    clock: Clock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    withdrawn = False

    def current(publication: Publication) -> FixtureObject:
        value = publication_manifest(publication.feed)
        for product in value["products"]:
            product["ready"]["engineering"] = True
        if withdrawn:
            value["products"] = [
                p
                for p in value["products"]
                if p.get("engineering_role") != "reference_pv_module"
            ]
        return value

    monkeypatch.setattr(Publication, "read", current)
    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    basis = json_object(products.module_basis())
    values = fixture_inputs(basis)
    assert "source_note" not in values["pvgis_reference"]
    assert PvgisReferenceInputs.read(values["pvgis_reference"]).source_note is None
    for optional_note in (None, "", " \t\n"):
        variant = {**values["pvgis_reference"], "source_note": optional_note}
        assert PvgisReferenceInputs.read(variant).source_note is None
    assert (
        PvgisReferenceInputs.read(
            {**values["pvgis_reference"], "source_note": " note \t"}
        ).source_note
        == " note \t"
    )
    layout = values["geometry"]
    source = Captures()
    kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: source,
    )
    project = workspace.create(
        owner, "Synthetic multi-array reference", values, key="roof"
    )
    plan = reference_plan(values, workspace.blobs.put_object(basis), limits(), 20_000)
    assert sum(a.module_count for a in plan.arrays) == 20
    expected_kwp = 20 * layout["module_specs"][0]["stc_power_w"] / 1000
    assert sum(a.request.peak_power_kwp for a in plan.arrays) == expected_kwp
    assert [a.request.tilt_deg for a in plan.arrays] == pytest.approx([10, 20])
    tampered = copy.deepcopy(values)
    tampered["geometry"]["module_specs"][0]["stc_power_w"] += 1
    with pytest.raises(InvalidInput):
        kernel.context(tampered)
    service = PvgisRoofReferenceService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 100_000, 10, 32),
        product_provider=client.app.state.planning_product_provider,
        pvgis_reference=service,
    )
    body = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": project.revision,
        "key": "reference",
    }
    with TestClient(app) as admission:
        version = admission.post(
            "/version", json={"schema_version": 1}, headers=headers(owner)
        )
        assert version.status_code == 200
        assert version.json()["models"]["pvgis_roof_reference"] == kernel.kind
        admitted = admission.post(
            "/runs/pvgis-reference", json=body, headers=headers(owner)
        )
        assert admitted.status_code == 200, admitted.text
        assert (
            admission.post(
                "/runs/pvgis-reference", json=body, headers=headers(owner)
            ).json()
            == admitted.json()
        )
        replay = admission.post(
            "/operations/replay/runs/pvgis-reference", json=body, headers=headers(owner)
        )
        assert replay.status_code == 200
        assert replay.json()["schema_version"] == 1
        assert replay.json()["status"] == "replayed"
        assert replay.json()["result"] == admitted.json()
        foreign = admission.post(
            "/runs/pvgis-reference",
            json=body,
            headers=headers(Actor("user", "wordpress:18")),
        )
        assert foreign.status_code == 404
    run = workspace.run(owner, admitted.json()["id"])
    assert source.requests == []  # HTTP admission has not called a provider.
    registry = ExecutionRegistry(kernel)
    worker = Worker(
        Jobs(workspace),
        "reference",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once()
    finished = workspace.run(owner, run.id)
    assert finished.state == "succeeded", finished.error
    result = json_object(finished.result)
    asset = Assets(workspace).get(owner, project.id, result["prepared_asset"]["id"])
    profile = prepared_reference_profile(
        workspace.blobs, asset.content_sha256, asset.metadata
    )
    assert profile.total_kwh == pytest.approx(946.43692 * expected_kwp, abs=1e-8)
    assert len(profile.intervals) == 8784 and profile.measurement == "pv_available_ac"
    assert profile.reconstructed_means is False and source.closed
    bundle = json_object(
        reference_bundle(workspace.blobs, asset.content_sha256, asset.metadata)
    )
    assert len(bundle["manifest"]["arrays"]) == 2
    assert bundle["parameters"] == values["pvgis_reference"]
    assert len(reference_dependencies(asset, values, workspace.blobs)) == 9
    for changed in ["geometry", "pvgis_reference"]:
        altered = copy.deepcopy(values)
        if changed == "geometry":
            altered[changed]["arrays"][0]["excluded_slots"] = ["0:0"]
        else:
            altered[changed]["year"] = 2021
        with pytest.raises(InvalidInput):
            reference_dependencies(asset, altered, workspace.blobs)
    bad = Captures(transient_second=True)
    bad_kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: bad,
    )
    bad_run = PvgisRoofReferenceService(workspace, bad_kernel, max_attempts=2).evaluate(
        owner, project.id, 1, key="bad"
    )
    bad_registry = ExecutionRegistry(bad_kernel)
    bad_worker = Worker(
        Jobs(workspace),
        "bad",
        {"evaluate": bad_registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=bad_registry.routing(8),
    )
    assert bad_worker.run_once()
    assert workspace.run(owner, bad_run.id).state == "retry_wait"
    assert workspace.run(owner, bad_run.id).result is None
    with workspace.database.read() as db:
        journal_sha = db.execute(
            "SELECT output_sha256 FROM jobs WHERE run_id=?", (bad_run.id,)
        ).fetchone()[0]
        assert (
            db.execute(
                "SELECT COUNT(*) FROM project_assets WHERE project_id=?", (project.id,)
            ).fetchone()[0]
            == 1
        )
    retained = json_object(workspace.blobs.object(journal_sha))
    assert list(retained["arrays"]) == ["0"]
    assert retained["arrays"]["0"]["validated"] is True
    first_raw = retained["arrays"]["0"]["raw_sha256"]
    first_capture = retained["arrays"]["0"]["capture_sha256"]
    used = len(workspace.blobs.read(first_raw))
    assert retained["consumed_bytes"] == used
    assert bad.byte_limits == [
        limits().max_response_bytes,
        limits().max_response_bytes - used,
    ]
    clock.advance(1)
    assert bad_worker.run_once()
    resumed = workspace.run(owner, bad_run.id)
    assert resumed.state == "succeeded", resumed.error
    resumed_asset = json_object(json_object(resumed.result)["prepared_asset"])
    resumed_metadata = resumed_asset["metadata"]
    acquisition = resumed_metadata["acquisition"]
    assert [r.tilt_deg for r in bad.requests] == pytest.approx([10, 20, 20])
    assert bad.deadlines == [retained["deadline_at"]] * 3
    assert bad.byte_limits[2] == limits().max_response_bytes - used
    assert acquisition["started_at"] == retained["started_at"]
    assert acquisition["deadline_at"] == retained["deadline_at"]
    assert acquisition["arrays"]["0"]["raw_sha256"] == first_raw
    assert acquisition["arrays"]["0"]["capture_sha256"] == first_capture
    assert acquisition["consumed_bytes"] == sum(
        len(workspace.blobs.read(row["raw_sha256"]))
        for row in acquisition["arrays"].values()
    )
    assert (
        resumed_metadata["interpretation"]["energy_kwh"]
        == json_object(asset.metadata["interpretation"])["energy_kwh"]
    )
    # One two-byte rejected response proves quarantine/fencing, without a
    # further annual replay or provider request.
    rejected = service.evaluate(owner, project.id, 1, key="invalid-original")
    lease = Jobs(workspace).claim(
        "quarantine", kinds=("evaluate",), lease_seconds=30, routing=registry.routing(8)
    )
    assert lease is not None and lease.run_id == rejected.id
    journal = PvgisReferenceJournal(workspace, lease, plan)
    journal.begin()
    invalid_original = ReferenceCapture(
        b"{}", PvgisCapture.read(workspace.blobs.object(first_capture))
    )
    journal.retain(0, invalid_original)
    with pytest.raises(WeatherResponseInvalid):
        journal.validate(0, invalid_original)
    quarantined = json_object(journal.current())
    assert quarantined["arrays"]["0"]["validated"] is False
    assert quarantined["arrays"]["0"]["failure"] == "response_validation_failed"
    assert workspace.blobs.read(quarantined["arrays"]["0"]["raw_sha256"]) == b"{}"
    with pytest.raises(WeatherResponseInvalid):
        journal.captured(0)
    assert workspace.run(owner, rejected.id).result is None
    Jobs(workspace).fail(
        lease,
        {"code": "weather_response_invalid", "retryable": False},
        retry_after=None,
    )
    with pytest.raises(LeaseLost):
        journal.retain(0, invalid_original)
    withdrawn = True
    with pytest.raises(ProductEvidenceChanged):
        products.check_profile(asset.metadata)
    assert (
        prepared_reference_profile(
            workspace.blobs, asset.content_sha256, asset.metadata
        ).total_kwh
        == profile.total_kwh
    )


class ReferenceAdapter(BaseAdapter):
    def __init__(self, reply: Reply) -> None:
        self.reply = reply

    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        assert request.url and "/api/v5_3/seriescalc?" in request.url
        assert request.method == "GET" and stream is True and verify is not False
        assert (
            "Authorization" not in request.headers and "Cookie" not in request.headers
        )
        response = requests.Response()
        response.status_code = self.reply.status
        response.url = self.reply.loaded_url or request.url
        response.headers.update(self.reply.headers)
        response.raw = HTTPResponse(
            body=io.BytesIO(self.reply.body), preload_content=False
        )
        return response

    def close(self) -> None:
        pass


def test_official_reference_transfer_retains_bytes_and_refuses_redirects() -> None:
    req = sample_request()
    transfer = PvgisReferenceHttp(ReferenceAdapter(Reply(200, raw())))
    captured = transfer.download(
        req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
    )
    assert captured.content == raw()
    wire = (
        encode({"schema_version": 1, "capture": captured.capture.document()})
        + b"\n"
        + captured.content
    )
    assert PvgisReferenceTransport._result(req, limits(), wire).content == raw()
    with pytest.raises(WeatherProviderRejected):
        PvgisReferenceHttp(ReferenceAdapter(Reply(302, b"redirect"))).download(
            req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
    with pytest.raises(WeatherResponseInvalid):
        PvgisReferenceHttp(
            ReferenceAdapter(
                Reply(200, raw(), loaded_url="https://foreign.invalid/seriescalc")
            )
        ).download(req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None)
    transfer.close()


def test_reference_supervision_cancels_and_reaps_only_its_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def observe(command: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        assert not any(
            k in kwargs["env"] for k in ["APIFY_TOKEN", "GENIE_SERVICE_TOKEN"]
        )
        child: subprocess.Popen[bytes] = original(
            [sys.executable, "-c", SLOW_BODY], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe)
    start = time.monotonic()

    def guard() -> None:
        if time.monotonic() - start > 0.10:
            raise LeaseLost("synthetic revoked owner")

    with pytest.raises(LeaseLost):
        PvgisReferenceTransport().download(
            sample_request(),
            limits(),
            deadline=time.time() + 5,
            clock=time.time,
            guard=guard,
        )
    assert len(children) == 1 and children[0].returncode is not None
