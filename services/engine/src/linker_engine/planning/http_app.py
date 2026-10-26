"""Private, bounded project RPC over the real durable workspace.

This app is constructed behind ServiceBoundary, with no public off switch or
browser CORS. A separate WP route must verify native identity, nonce/origin
and resource policy before making this authenticated hop. The composed service
mounts this app outside legacy public middleware. Numerical work runs only in
the Worker.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp

from .access import active_actor, positive_integer
from .assets import Assets
from .canonical import Json, Object
from .csv_inspection import inspect_csv
from .csv_issue import CsvIssue
from .energy_comparison import compare_energy_runs
from .energy_service import EnergyService
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_service import EquipmentService
from .errors import (
    Conflict,
    EvaluationRevisionChanged,
    EvidenceMissing,
    InvalidInput,
    LeaseLost,
    MethodDomainExceeded,
    NotFound,
    NumericalFailure,
    PlanningError,
    ServiceDraining,
    VersionUnavailable,
)
from .execution_identity import storage_binding
from .execution_registry import service_registry
from .geometry_import import GeometryImport
from .geometry_import_selections import check_geometry_imports
from .geometry_review import review_geometry
from .guest_claims import GuestClaims
from .handoffs import Handoffs
from .http_asset_intake import HttpAssetIntake
from .http_documents import (
    AssetRead,
    BatteryScenario,
    Command,
    CsvImport,
    CsvInspect,
    EnergyEvaluate,
    EquipmentCandidateRead,
    GeometryImportCommand,
    GeometryReview,
    HandoffPrepare,
    HandoffRead,
    InstallationReview,
    ProfilePreviewRead,
    ProjectCreate,
    ProjectList,
    ProjectRead,
    ProjectRevise,
    ProjectRuns,
    ReportEvaluate,
    RunCompare,
    RunRead,
    SessionClaim,
    TraceRead,
)
from .http_index import project_page, run_page
from .http_replay import HttpReplay
from .http_views import asset_view, project_view, run_view
from .product_sources import ProductProvider, ProductSources
from .profile_preview import ProfilePreview
from .profile_selections import check_profile_selections
from .pv_preparation import PvPreparationService, check_pv_preparation
from .records import Actor
from .report_kernel import ReportService
from .service_boundary import ServiceBoundary, verified_actor, verified_previous_guest
from .trace_window import TraceWindow
from .weather_service import WeatherService
from .weather_status import weather_status
from .workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HttpLimits:
    max_body_bytes: int
    max_csv_bytes: int
    max_page_size: int
    max_json_depth: int

    def __post_init__(self) -> None:
        for name in (
            "max_body_bytes",
            "max_csv_bytes",
            "max_page_size",
            "max_json_depth",
        ):
            positive_integer(getattr(self, name), name)


def create_private_app(
    workspace: Workspace,
    energy: EnergyService,
    *,
    credential: Callable[[], str],
    limits: HttpLimits,
    pv: PvPreparationService | None = None,
    weather: WeatherService | None = None,
    product_provider: Callable[[], ProductProvider] | None = None,
    equipment: EquipmentService | None = None,
    equipment_search: EquipmentService | None = None,
    reports: ReportService | None = None,
) -> ASGIApp:
    if energy.workspace is not workspace or energy.kernel.workspace is not workspace:
        raise InvalidInput("HTTP and energy service must share the same authority")
    if pv is not None and (
        pv.workspace is not workspace or pv.kernel.workspace is not workspace
    ):
        raise InvalidInput("HTTP and PV preparation must share the same authority")
    if weather is not None and (
        weather.workspace is not workspace or weather.kernel.workspace is not workspace
    ):
        raise InvalidInput("HTTP and weather acquisition must share project authority")
    if equipment is not None and (
        equipment.workspace is not workspace
        or equipment.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput(
            "equipment qualification requires shared project and Woo authority"
        )
    if equipment_search is not None and (
        equipment_search.workspace is not workspace
        or equipment_search.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput("equipment search requires shared project and Woo authority")
    if reports is not None and (
        reports.workspace is not workspace
        or reports.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput("reports require shared project and Woo authority")
    registry = service_registry(
        energy, pv, weather, equipment, equipment_search, reports
    )
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    assets = Assets(workspace)
    claims = GuestClaims(workspace)
    intake = HttpAssetIntake(
        assets, max_csv_bytes=limits.max_csv_bytes, products=energy.kernel.products
    )
    geometry_intake = GeometryImport(assets)
    previews = ProfilePreview(assets)
    replays = HttpReplay(workspace, energy, intake, geometry_intake)
    products = (
        ProductSources(product_provider) if product_provider is not None else None
    )

    def previous_result(actor: Actor, path: str, body: Command) -> Object | None:
        # Reuse the existing durable receipt reader. Historical private replay
        # never becomes a new operation or asks for current product permission.
        if products is None:
            return None
        result = replays.read(actor, path, cast(Object, body.model_dump(mode="json")))
        return (
            cast(Object, result["result"]) if result["status"] == "replayed" else None
        )

    @app.exception_handler(PlanningError)
    async def domain_error(_request: Request, error: PlanningError) -> JSONResponse:
        statuses = {
            NotFound: 404,
            Conflict: 409,
            EvaluationRevisionChanged: 409,
            InvalidInput: 422,
            EvidenceMissing: 422,
            MethodDomainExceeded: 422,
            CsvIssue: 422,
            VersionUnavailable: 503,
            ServiceDraining: 503,
            LeaseLost: 409,
            NumericalFailure: 422,
        }
        status = next(
            (status for kind, status in statuses.items() if isinstance(error, kind)),
            500,
        )
        # Private row/file values and exception traces are not returned.
        detail: Object = {"code": error.code}
        if isinstance(error, EvidenceMissing) and error.public_details:
            detail["details"] = dict(error.public_details)
        if isinstance(error, CsvIssue):
            detail["profile_issue"] = error.document()
        return JSONResponse({"error": detail}, status_code=status)

    @app.exception_handler(RequestValidationError)
    async def bad_command(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # Bounded transport diagnostics, not engineering tolerances. The
        # explicit request depth gate precedes recursive union validation.
        errors = error.errors()
        fields: list[Json] = [
            {
                "path": [str(part)[:64] for part in item["loc"][:16]],
                "kind": item["type"],
            }
            for item in errors[:16]
        ]
        detail: Object = {"code": "invalid_input", "fields": fields}
        if len(errors) > 16 or any(
            len(item["loc"]) > 16 or any(len(str(part)) > 64 for part in item["loc"])
            for item in errors[:16]
        ):
            detail["truncated"] = True
        return JSONResponse({"error": detail}, status_code=422)

    @app.exception_handler(HTTPException)
    async def framework_error(_request: Request, error: HTTPException) -> JSONResponse:
        code = {
            400: "invalid_input",
            404: "not_found",
            405: "method_not_allowed",
            413: "request_too_large",
        }.get(error.status_code, "http_error")
        allowed = (error.headers or {}).get("Allow")
        return JSONResponse(
            {"error": {"code": code}},
            status_code=error.status_code,
            headers={"Allow": allowed} if allowed else None,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, error: Exception) -> JSONResponse:
        logger.error("private planner request failed", exc_info=error)
        return JSONResponse({"error": {"code": "execution_failed"}}, status_code=500)

    @app.post("/version")
    def runtime(_body: Command) -> Object:
        return {
            "schema_version": 1,
            "runtime_sha256": energy.kernel.runtime.sha256,
            "models": {
                **energy.kernel.models,
                "comparison": "frozen_energy_comparison_v1",
                **(
                    {"dc_replay": energy.dc_kernel.kind}
                    if energy.dc_kernel is not None
                    else {}
                ),
                **(
                    {"plant_replay": energy.plant_kernel.kind}
                    if energy.plant_kernel is not None
                    else {}
                ),
                **({"report": reports.kernel.kind} if reports is not None else {}),
                **(
                    {
                        "equipment_search": equipment_search.kernel.kind,
                        "equipment_plant_search": "declared_plant_v1",
                    }
                    if equipment_search is not None
                    else {}
                ),
            },
            "execution_key": registry.execution_key(),
            "storage_binding": storage_binding(workspace.database.path),
            "limits": {
                "max_body_bytes": limits.max_body_bytes,
                "max_csv_bytes": limits.max_csv_bytes,
                "max_page_size": limits.max_page_size,
                "max_json_depth": limits.max_json_depth,
            },
        }

    @app.post("/identity/status")
    def identity_status(_body: Command, request: Request) -> Object:
        actor = verified_actor(request.scope)
        with workspace.database.read() as connection:
            try:
                active_actor(connection, actor)
            except NotFound:
                return {"schema_version": 1, "status": "retired"}
        return {"schema_version": 1, "status": "active"}

    @app.post("/products/current")
    def current_products(_body: Command, request: Request) -> Object:
        actor = verified_actor(request.scope)
        with workspace.database.read() as connection:
            active_actor(connection, actor)
        if products is None:
            raise VersionUnavailable("current Woo product data is unavailable")
        return products.current()

    @app.post("/handoffs/prepare")
    def prepare_handoff(body: HandoffPrepare, request: Request) -> Object:
        return Handoffs(workspace).prepare(
            verified_actor(request.scope, write=True),
            body.project_id,
            body.report_run_id,
            body.expected_revision,
            key=body.key,
        )

    @app.post("/handoffs/read")
    def read_handoff(body: HandoffRead, request: Request) -> Object:
        return Handoffs(workspace).read(verified_actor(request.scope), body.handoff_id)

    @app.post("/identity/claim-session")
    def claim_session(body: SessionClaim, request: Request) -> Object:
        user = verified_actor(request.scope, write=True)
        if user.kind != "user":
            raise NotFound("verified account required")
        return claims.claim(verified_previous_guest(request.scope), user, key=body.key)

    @app.post("/operations/replay/{path:path}")
    def replay(path: str, body: Object, request: Request) -> Object:
        try:
            return replays.read(verified_actor(request.scope, write=True), path, body)
        except ValidationError as error:
            raise RequestValidationError(error.errors()) from error

    @app.post("/projects/create")
    def create(body: ProjectCreate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "projects/create", body)
        if previous is not None:
            return previous
        check_profile_selections(assets, actor, None, body.inputs)
        check_geometry_imports(assets, actor, None, body.inputs)
        check_pv_preparation(assets, actor, None, body.inputs)
        check_equipment_candidate(
            workspace, actor, None, body.inputs, products=products
        )
        if products is not None:
            products.check_project(body.inputs)
        return project_view(
            workspace.create(actor, body.title, body.inputs, key=body.key)
        )

    @app.post("/projects/list")
    def listing(body: ProjectList, request: Request) -> Object:
        if body.page_size > limits.max_page_size:
            raise InvalidInput("project page exceeds deployment limit")
        return project_page(
            workspace, verified_actor(request.scope), body.page_size, body.after
        )

    @app.post("/projects/read")
    def read(body: ProjectRead, request: Request) -> Object:
        return project_view(
            workspace.get(
                verified_actor(request.scope), body.project_id, revision=body.revision
            )
        )

    @app.post("/projects/revise")
    def revise(body: ProjectRevise, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        receipt = previous_result(actor, "projects/revise", body)
        if receipt is not None:
            return receipt
        # Reject a foreign writer before publishing even an orphan input blob.
        previous = workspace.get(actor, body.project_id)
        check_profile_selections(assets, actor, body.project_id, body.inputs)
        check_geometry_imports(assets, actor, body.project_id, body.inputs)
        check_pv_preparation(assets, actor, body.project_id, body.inputs)
        check_equipment_candidate(
            workspace,
            actor,
            body.project_id,
            body.inputs,
            products=products,
            previous=previous.inputs,
        )
        if products is not None:
            products.check_project(body.inputs, previous.inputs)
        return project_view(
            workspace.revise(
                actor,
                body.project_id,
                body.expected_revision,
                body.inputs,
                key=body.key,
            )
        )

    @app.post("/projects/runs")
    def runs(body: ProjectRuns, request: Request) -> Object:
        if body.page_size > limits.max_page_size:
            raise InvalidInput("run page exceeds deployment limit")
        return run_page(
            workspace,
            verified_actor(request.scope),
            body.project_id,
            body.page_size,
            body.before_created_at,
            body.before_id,
        )

    @app.post("/geometry/review")
    def geometry_review(body: GeometryReview, request: Request) -> Object:
        # Ownership is checked before geometry work; this read-only review
        # never publishes a source blob or mutates the saved revision.
        workspace.get(verified_actor(request.scope), body.project_id)
        reply = review_geometry(body.geometry)
        reply["runtime_sha256"] = energy.kernel.runtime.sha256
        return reply

    @app.post("/geometry/import")
    def geometry_import(body: GeometryImportCommand, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        assets.check_write(actor, body.project_id)
        return asset_view(
            geometry_intake.prepare(
                actor,
                body.project_id,
                geometry_intake.decode(body.content_base64),
                body.options,
                key=body.key,
            )
        )

    @app.post("/installation/review")
    def installation_review(body: InstallationReview, request: Request) -> Object:
        from .installation_inputs import InstallationInputs
        from .installation_takeoff import product_basis, route_takeoff

        workspace.get(verified_actor(request.scope), body.project_id)
        if products is None:
            raise VersionUnavailable("current Woo installation evidence is unavailable")
        inputs: Object = {"geometry": body.geometry, "installation": body.installation}
        basis = product_basis(
            InstallationInputs.read(body.installation), products.equipment_basis()
        )
        reply = route_takeoff(inputs, basis, bind_geometry=body.bind_geometry)
        products.confirm_basis(basis, require_reference=False)
        reply["project_id"] = body.project_id
        reply["runtime_sha256"] = energy.kernel.runtime.sha256
        return reply

    @app.post("/runs/read")
    def run_read(body: RunRead, request: Request) -> Object:
        return run_view(workspace.run(verified_actor(request.scope), body.run_id))

    @app.post("/runs/compare")
    def run_compare(body: RunCompare, request: Request) -> Object:
        return compare_energy_runs(
            workspace,
            verified_actor(request.scope),
            body.project_id,
            body.baseline_run_id,
            body.candidate_run_id,
        )

    @app.post("/runs/cancel")
    def cancel(body: RunRead, request: Request) -> Object:
        return run_view(
            workspace.cancel(verified_actor(request.scope, write=True), body.run_id)
        )

    @app.post("/runs/energy")
    def evaluate(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/energy", body)
        if previous is not None:
            return previous
        return run_view(
            energy.evaluate(
                actor,
                body.project_id,
                body.expected_revision,
                key=body.key,
            )
        )

    @app.post("/runs/pv")
    def prepare_pv(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/pv", body)
        if previous is not None:
            return previous
        if pv is None:
            raise VersionUnavailable("PV preparation is not configured")
        return run_view(
            pv.evaluate(actor, body.project_id, body.expected_revision, key=body.key)
        )

    @app.post("/runs/equipment")
    def qualify_equipment(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/equipment", body)
        if previous is not None:
            return previous
        if equipment is None:
            raise VersionUnavailable("equipment qualification is not configured")
        return run_view(
            equipment.evaluate(
                actor,
                body.project_id,
                body.expected_revision,
                key=body.key,
            )
        )

    @app.post("/runs/equipment-search")
    def equipment_find(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/equipment-search", body)
        if previous is not None:
            return previous
        if equipment_search is None:
            raise VersionUnavailable("equipment search is not configured")
        return run_view(
            equipment_search.evaluate(
                actor, body.project_id, body.expected_revision, key=body.key
            )
        )

    @app.post("/runs/report")
    def planning_report(body: ReportEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/report", body)
        if previous is not None:
            return previous
        if reports is None:
            raise VersionUnavailable("planning reports are unavailable")
        return run_view(
            reports.evaluate(
                actor,
                body.project_id,
                body.expected_revision,
                body.options,
                key=body.key,
            )
        )

    @app.post("/equipment/candidates/read")
    def equipment_candidate(body: EquipmentCandidateRead, request: Request) -> Object:
        return EquipmentCandidateStore(workspace).read(
            verified_actor(request.scope), body.run_id, body.candidate_id
        )

    @app.post("/runs/trace")
    def energy_trace(body: TraceRead, request: Request) -> Response:
        if body.offset is not None and body.page_size is not None:
            if body.page_size > limits.max_page_size:
                raise InvalidInput("trace window exceeds deployment page limit")
            return JSONResponse(
                TraceWindow(workspace).page(
                    verified_actor(request.scope),
                    body.run_id,
                    offset=body.offset,
                    page_size=body.page_size,
                    unit_id=body.unit_id,
                )
            )
        run = workspace.run(verified_actor(request.scope), body.run_id)
        trace_hash = run.result.get("trace_sha256") if run.result else None
        if not isinstance(trace_hash, str):
            raise NotFound("trace not found")
        return Response(
            workspace.blobs.read(trace_hash),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{body.run_id}-energy-trace.json"'
            },
        )

    @app.post("/runs/weather")
    def acquire_weather(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        if weather is None:
            raise VersionUnavailable("weather acquisition is not configured")
        return run_view(
            weather.evaluate(
                actor, body.project_id, body.expected_revision, key=body.key
            )
        )

    @app.post("/runs/weather/status")
    def read_weather(body: RunRead, request: Request) -> Object:
        return weather_status(workspace, verified_actor(request.scope), body.run_id)

    @app.post("/assets/read")
    def asset_read(body: AssetRead, request: Request) -> Object:
        return asset_view(
            assets.get(verified_actor(request.scope), body.project_id, body.asset_id)
        )

    @app.post("/assets/content")
    def asset_content(body: AssetRead, request: Request) -> Response:
        content = assets.content(
            verified_actor(request.scope), body.project_id, body.asset_id
        )
        return Response(
            content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{body.asset_id}"'},
        )

    @app.post("/profiles/csv")
    def csv_profile(body: CsvImport, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        return asset_view(intake.csv(actor, body))

    @app.post("/profiles/inspect")
    def csv_inspect(body: CsvInspect, request: Request) -> Object:
        workspace.get(verified_actor(request.scope), body.project_id)
        if body.page_size > limits.max_page_size:
            raise InvalidInput("CSV preview page exceeds deployment limit")
        return inspect_csv(
            intake.decode_csv(body.content_base64),
            body.delimiter,
            page_size=body.page_size,
            max_reply_bytes=limits.max_body_bytes,
        )

    @app.post("/battery/scenario")
    def battery_scenario(body: BatteryScenario, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        return asset_view(intake.battery(actor, body))

    @app.post("/profiles/preview")
    def profile_preview(body: ProfilePreviewRead, request: Request) -> Object:
        if body.page_size > limits.max_page_size:
            raise InvalidInput("profile page exceeds deployment limit")
        return previews.page(
            verified_actor(request.scope),
            body.project_id,
            body.asset_id,
            offset=body.offset,
            page_size=body.page_size,
        )

    return ServiceBoundary(
        app,
        credential=credential,
        max_body_bytes=limits.max_body_bytes,
        max_json_depth=limits.max_json_depth,
    )
