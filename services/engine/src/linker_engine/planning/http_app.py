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
from .energy_service import EnergyService
from .errors import (
    Conflict,
    InvalidInput,
    LeaseLost,
    NotFound,
    NumericalFailure,
    PlanningError,
    VersionUnavailable,
)
from .geometry_review import review_geometry
from .guest_claims import GuestClaims
from .http_asset_intake import HttpAssetIntake
from .http_documents import (
    AssetRead,
    BatteryScenario,
    Command,
    CsvImport,
    CsvInspect,
    EnergyEvaluate,
    GeometryReview,
    ProfilePreviewRead,
    ProjectCreate,
    ProjectList,
    ProjectRead,
    ProjectRevise,
    ProjectRuns,
    RunRead,
    SessionClaim,
)
from .http_index import project_page, run_page
from .http_replay import HttpReplay
from .http_views import asset_view, project_view, run_view
from .profile_preview import ProfilePreview
from .profile_selections import check_profile_selections
from .service_boundary import ServiceBoundary, verified_actor, verified_previous_guest
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
) -> ASGIApp:
    if energy.workspace is not workspace or energy.kernel.workspace is not workspace:
        raise InvalidInput("HTTP and energy service must share the same authority")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    assets = Assets(workspace)
    claims = GuestClaims(workspace)
    intake = HttpAssetIntake(assets, max_csv_bytes=limits.max_csv_bytes)
    previews = ProfilePreview(assets)
    replays = HttpReplay(workspace, energy, intake)

    @app.exception_handler(PlanningError)
    async def domain_error(_request: Request, error: PlanningError) -> JSONResponse:
        status = {
            NotFound: 404,
            Conflict: 409,
            InvalidInput: 422,
            CsvIssue: 422,
            VersionUnavailable: 503,
            LeaseLost: 409,
            NumericalFailure: 422,
        }.get(type(error), 500)
        # Private row/file values and exception traces are not returned.
        detail: Object = {"code": error.code}
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
            "models": dict(energy.kernel.models),
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
        check_profile_selections(assets, actor, None, body.inputs)
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
        # Reject a foreign writer before publishing even an orphan input blob.
        workspace.get(actor, body.project_id)
        check_profile_selections(assets, actor, body.project_id, body.inputs)
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
        return review_geometry(body.geometry)

    @app.post("/runs/read")
    def run_read(body: RunRead, request: Request) -> Object:
        return run_view(workspace.run(verified_actor(request.scope), body.run_id))

    @app.post("/runs/cancel")
    def cancel(body: RunRead, request: Request) -> Object:
        return run_view(
            workspace.cancel(verified_actor(request.scope, write=True), body.run_id)
        )

    @app.post("/runs/energy")
    def evaluate(body: EnergyEvaluate, request: Request) -> Object:
        return run_view(
            energy.evaluate(
                verified_actor(request.scope, write=True),
                body.project_id,
                body.expected_revision,
                key=body.key,
            )
        )

    @app.post("/runs/trace")
    def energy_trace(body: RunRead, request: Request) -> Response:
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
