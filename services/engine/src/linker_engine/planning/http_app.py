"""Private, bounded project RPC over the real durable workspace.

This app is constructed behind ServiceBoundary, with no public off switch or
browser CORS. A separate WP route must verify native identity, nonce/origin
and resource policy before making this authenticated hop. The composed service
mounts this app outside legacy public middleware. Numerical work runs only in
the Worker.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp

from .. import geo, imagery
from ..models import Imagery
from ..roof import europe, footprints, lod2
from ..roof.citygml import Building
from .access import active_actor, positive_integer
from .assets import Assets
from .assistant_context import assistant_context
from .canonical import Json, Object
from .capacity_window import REFERENCE_CAPACITY
from .certificate_evidence import CertificateEvidence
from .csv_inspection import inspect_csv
from .csv_issue import CsvIssue
from .direct_beam_service import DirectBeamService
from .direct_beam_weather import check_direct_beam, weather_assets, weather_preview
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
    StorageUnavailable,
    VersionUnavailable,
)
from .execution_identity import storage_binding
from .execution_registry import service_registry
from .geometric_pv_job import check_geometric_pv
from .geometric_pv_service import GeometricPvService
from .geometry_import import GeometryImport
from .geometry_import_selections import check_geometry_imports
from .geometry_review import review_geometry
from .guest_claims import GuestClaims
from .handoffs import Handoffs
from .http_asset_intake import HttpAssetIntake
from .http_documents import (
    AssetRead,
    BatteryScenario,
    CertificateRead,
    CheckedProjectDelete,
    Command,
    CsvImport,
    CsvInspect,
    EnergyCalculate,
    EnergyEvaluate,
    EquipmentCandidateRead,
    EquipmentFind,
    GeometryImportCommand,
    GeometryReview,
    HandoffPrepare,
    HandoffRead,
    InquiryAdmission,
    InstallationReview,
    PlaceLookup,
    PlaceOutline,
    PreparedHandoffs,
    ProfilePreviewRead,
    ProjectAssistant,
    ProjectCreate,
    ProjectDelete,
    ProjectInquiry,
    ProjectList,
    ProjectRead,
    ProjectRevise,
    ProjectRuns,
    ReportEvaluate,
    RunCompare,
    RunInputsRead,
    RunRead,
    SessionClaim,
    StandardProfile,
    TraceRead,
    WeatherAssetsRead,
)
from .http_index import project_page, run_page
from .http_replay import HttpReplay
from .http_views import asset_view, owned_run_view, project_view, run_view
from .product_sources import ProductProvider, ProductSources
from .profile_preview import ProfilePreview
from .profile_selections import check_profile_selections
from .project_input_contracts import SUPPORTED_INPUT_CONTRACTS
from .pv_preparation import PvPreparationService, check_pv_preparation
from .pvgis_reference_service import PvgisRoofReferenceService
from .records import Actor
from .report_kernel import ReportService
from .retained_panels import display_document, project_panels
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


def _imagery_reply(service: Imagery | None) -> Object | None:
    """Serialize the aerial layer independently of the address lookup."""
    if service is None:
        return None
    return {
        "tiles": list(service.tiles),
        "credit": service.credit,
        "licence": service.licence,
        "licence_url": service.licence_url,
    }


@cache
def _local_model_transformer(country: str) -> Transformer:
    return Transformer.from_crs("EPSG:4326", europe.model_crs(country), always_xy=True)


def _outer_ring(
    footprint_rings: list[list[tuple[float, float]]],
    plane_rings: list[list[tuple[float, float]]],
) -> list[tuple[float, float]] | None:
    for ring in footprint_rings:
        if len(ring) >= 3:
            return ring
    polygons = [Polygon(ring) for ring in plane_rings if len(ring) >= 3]
    valid = [p if p.is_valid else p.buffer(0) for p in polygons if not p.is_empty]
    if not valid:
        return None
    merged = unary_union(valid)
    target = merged if isinstance(merged, Polygon) else merged.convex_hull
    if isinstance(target, Polygon) and len(target.exterior.coords) >= 4:
        return [(float(x), float(y)) for x, y in target.exterior.coords[:-1]]
    return None


def _lod2_shape(building: dict[str, Any]) -> BaseGeometry | None:
    rings = building.get("footprint") or [
        plane["ring"] for plane in building.get("planes", [])
    ]
    polygons = [Polygon(ring) for ring in rings if len(ring) >= 3]
    valid = [p if p.is_valid else p.buffer(0) for p in polygons if not p.is_empty]
    if not valid:
        return None
    return unary_union(valid)


def _transform_wgs84_ring(
    transformer: Transformer, ring: list[tuple[float, float]]
) -> Json:
    return [
        [round(float(lon), 7), round(float(lat), 7)]
        for lon, lat in (transformer.transform(x, y) for x, y in ring)
    ]


def _lod2_wgs84_ring(zone: int, ring: list[tuple[float, float]]) -> Json:
    return [
        [round(lon, 7), round(lat, 7)]
        for lon, lat in (lod2.to_wgs84(zone, x, y) for x, y in ring)
    ]


OUTLINE_SEARCH_RADIUS_M = 60.0


def _official_3d_outline(
    place: geo.Place, latitude: float, longitude: float
) -> Object | None:
    if place.country in ("NL", "CH", "LI"):
        try:
            model = europe.read(place.country, latitude, longitude)
        except europe.ModelUnavailable:
            model = None
        if model is None:
            return None
        to_wgs84 = model.transformer
        to_local = _local_model_transformer(model.country)
        x, y = to_local.transform(longitude, latitude)
        best: tuple[float, Building] | None = None
        for building in model.buildings:
            footprint = (
                building.footprint[0]
                if building.footprint
                else (building.planes[0].ring if building.planes else None)
            )
            if footprint is None:
                continue
            dist = europe.distance_m(footprint, x, y)
            if dist <= OUTLINE_SEARCH_RADIUS_M and (best is None or dist < best[0]):
                best = (dist, building)
        if best is None:
            return None
        _, chosen = best
        valid_planes = [
            plane
            for plane in chosen.planes
            if 0.0 <= plane.tilt_deg < 90.0
            and 1.0 <= plane.area_m2 <= 3000.0
            and len(plane.ring) >= 3
        ]
        if not valid_planes:
            return None
        outer = _outer_ring(chosen.footprint, [plane.ring for plane in valid_planes])
        if outer is None:
            return None
        return {
            "schema_version": 1,
            "found": True,
            "country_code": place.country,
            "outline": _transform_wgs84_ring(to_wgs84, outer),
            "source": f"{model.country} 3D model",
            "licence": model.licence,
            "planes": [
                {
                    "id": index,
                    "polygon": _transform_wgs84_ring(to_wgs84, plane.ring),
                    "tilt_deg": round(plane.tilt_deg, 1),
                    "azimuth_deg": round(plane.azimuth_deg, 1),
                    "area_m2": round(plane.area_m2, 2),
                }
                for index, plane in enumerate(valid_planes, start=1)
            ],
        }
    if place.country == "DE":
        cache_dir = (
            Path(os.environ.get("LINKER_ENGINE_CACHE") or "/tmp/linker-engine-cache")
            / "lod2"
        )
        try:
            tile = lod2.tile_for(place.iso_region, latitude, longitude)
            index = lod2.TileIndex(cache_dir).load(tile)
        except lod2.Lod2Unavailable:
            return None
        x, y = lod2.to_utm(tile.zone, latitude, longitude)
        point = Point(x, y)
        best_de: tuple[float, dict[str, Any]] | None = None
        for item in index["buildings"]:
            shape = _lod2_shape(item)
            if shape is None:
                continue
            dist = shape.distance(point)
            if dist <= OUTLINE_SEARCH_RADIUS_M and (
                best_de is None or dist < best_de[0]
            ):
                best_de = (dist, item)
        if best_de is None:
            return None
        _, building_dict = best_de
        raw_planes = [
            raw
            for raw in building_dict.get("planes", [])
            if 0.0 <= float(raw.get("tilt", -1)) < 90.0
            and 1.0 <= float(raw.get("area", 0)) <= 3000.0
            and len(raw.get("ring", [])) >= 3
        ]
        if not raw_planes:
            return None
        footprint_rings = [
            [(float(px), float(py)) for px, py in ring]
            for ring in (building_dict.get("footprint") or [])
        ]
        plane_rings = [
            [(float(px), float(py)) for px, py in raw["ring"]] for raw in raw_planes
        ]
        outer = _outer_ring(footprint_rings, plane_rings)
        if outer is None:
            return None
        return {
            "schema_version": 1,
            "found": True,
            "country_code": place.country,
            "outline": _lod2_wgs84_ring(tile.zone, outer),
            "source": f"LoD2 {place.iso_region}",
            "licence": tile.licence,
            "planes": [
                {
                    "id": idx,
                    "polygon": _lod2_wgs84_ring(
                        tile.zone,
                        [(float(px), float(py)) for px, py in raw["ring"]],
                    ),
                    "tilt_deg": round(float(raw["tilt"]), 1),
                    "azimuth_deg": round(float(raw["azimuth"]), 1),
                    "area_m2": round(float(raw["area"]), 2),
                }
                for idx, raw in enumerate(raw_planes, start=1)
            ],
        }
    return None


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
    pvgis_reference: PvgisRoofReferenceService | None = None,
    direct_beam: DirectBeamService | None = None,
    geometric_pv: GeometricPvService | None = None,
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
    if pvgis_reference is not None and (
        pvgis_reference.workspace is not workspace
        or pvgis_reference.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput(
            "PVGIS roof reference requires shared project and Woo authority"
        )
    if direct_beam is not None and (
        direct_beam.workspace is not workspace
        or direct_beam.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput(
            "direct-beam visibility requires shared project and Woo authority"
        )
    if geometric_pv is not None and (
        geometric_pv.workspace is not workspace
        or geometric_pv.kernel.workspace is not workspace
        or product_provider is None
    ):
        raise InvalidInput("geometric PV requires shared project and Woo authority")
    geo.countries()
    registry = service_registry(
        energy,
        pv,
        weather,
        equipment,
        equipment_search,
        reports,
        pvgis_reference,
        direct_beam,
        geometric_pv,
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
        command = cast(Object, body.model_dump(mode="json"))
        if (
            isinstance(body, (ProjectCreate, ProjectRevise))
            and "input_contract" not in body.model_fields_set
        ):
            command.pop("input_contract", None)
        result = replays.read(actor, path, command)
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
            StorageUnavailable: 503,
            LeaseLost: 409,
            NumericalFailure: 422,
        }
        status = next(
            (status for kind, status in statuses.items() if isinstance(error, kind)),
            500,
        )
        # Private row/file values and exception traces are not returned.
        detail: Object = {"code": error.code}
        if isinstance(error, InvalidInput) and error.public_fields:
            detail["fields"] = list(error.public_fields)
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
                    {"capacity_reference": REFERENCE_CAPACITY}
                    if energy.dc_kernel is not None or energy.plant_kernel is not None
                    else {}
                ),
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
                **(
                    {"plant_dc_replay": energy.plant_dc_kernel.kind}
                    if energy.plant_dc_kernel is not None
                    else {}
                ),
                **({"report": reports.kernel.kind} if reports is not None else {}),
                **(
                    {"direct_beam_visibility": direct_beam.kernel.kind}
                    if direct_beam is not None
                    else {}
                ),
                **(
                    {"geometric_pv_generation": geometric_pv.kernel.kind}
                    if geometric_pv is not None
                    else {}
                ),
                **(
                    {
                        "pvgis_roof_reference": pvgis_reference.kernel.kind,
                        "pvgis_known_reference": "pvgis_5_3_known_ac_reference_v1",
                    }
                    if pvgis_reference is not None
                    else {}
                ),
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
                **(
                    {
                        "direct_beam_visibility": direct_beam.kernel.limits.model_dump(
                            mode="json"
                        )
                    }
                    if direct_beam is not None
                    else {}
                ),
                **(
                    {
                        "geometric_pv_generation": geometric_pv.kernel.limits.model_dump(
                            mode="json"
                        )
                    }
                    if geometric_pv is not None
                    else {}
                ),
                **(
                    {
                        "geometric_pv_clear_flat_roof": geometric_pv.kernel.expanded_limits.model_dump(
                            mode="json"
                        )
                    }
                    if geometric_pv is not None
                    and geometric_pv.kernel.expanded_limits is not None
                    else {}
                ),
                **(
                    {
                        "geometric_pv_clear_pitched_roof": geometric_pv.kernel.pitched_limits.model_dump(
                            mode="json"
                        )
                    }
                    if geometric_pv is not None
                    and geometric_pv.kernel.pitched_limits is not None
                    else {}
                ),
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

    @app.post("/inputs/contracts")
    def input_contract_status(_body: Command, request: Request) -> Object:
        if verified_actor(request.scope).kind != "team":
            raise NotFound("operator state not found")
        from .project_input_floor import read_project_input_floor

        try:
            floor = read_project_input_floor(workspace.database.path.parent)
        except ValueError as error:
            raise VersionUnavailable("project input floor is unavailable") from error
        return {
            **floor,
            "supported_input_contracts": list(SUPPORTED_INPUT_CONTRACTS),
        }

    @app.post("/products/current")
    def current_products(_body: Command, request: Request) -> Object:
        actor = verified_actor(request.scope)
        with workspace.database.read() as connection:
            active_actor(connection, actor)
        if products is None:
            raise VersionUnavailable("current Woo product data is unavailable")
        return products.current()

    @app.post("/places/lookup")
    def lookup_place(body: PlaceLookup, request: Request) -> Object:
        """Resolve a declared postcode to the site facts a project records.

        The one-screen start asks for a postcode, and until now the saved
        project carried only that free text: the printed report had no country
        and no time zone, and the weather step had no coordinate anchor. The
        bundled European table answers all four, so the screen asks the server
        instead of the visitor.

        The table used to be German and the answer keyed on five digits, so a
        Dutch or British postcode was refused (measured 2026-11-15). Shapes now
        come from the table in each country's own form: `10115`, `75001`,
        `M1 1AE`, `3750-000`, `59-700`.
        """
        actor = verified_actor(request.scope)
        with workspace.database.read() as connection:
            active_actor(connection, actor)
        query = body.query.strip()
        if not query:
            raise NotFound("place not found")
        found = geo.lookup(query, body.country)
        country = (
            found.country if found else body.country.upper() if body.country else None
        )
        editing = (
            imagery.for_editing(country, found.iso_region if found else None)
            if country
            else None
        )
        # Keep viewing pixels separate from the editing source consumed by the design tools.
        viewing = imagery.for_viewing(country) if country and editing is None else None
        layers = {
            "imagery": _imagery_reply(editing),
            "viewing_imagery": _imagery_reply(viewing),
        }
        if found is None:
            # A postcode several countries write the same way is not a failure
            # of the visitor's input; the screen asks for the country instead of
            # claiming the place does not exist.
            shared = body.country is None and len(geo.countries_of(query)) > 1
            return {
                "schema_version": 1,
                "found": False,
                "query": query,
                "needs_country": shared,
                "attribution": geo.ATTRIBUTION,
                # A street address resolved by the browser's Google geocoder
                # need not exist in the postal table. Its saved coordinates
                # still need the selected country's aerial layer.
                **layers,
            }
        return {
            "schema_version": 1,
            "found": True,
            "query": query,
            "country_code": found.country,
            "location_label": f"{found.postcode} {found.name}",
            "latitude": found.latitude,
            "longitude": found.longitude,
            "region": found.region,
            "timezone": found.timezone,
            "attribution": geo.ATTRIBUTION,
            **layers,
        }

    @app.post("/places/outline")
    def place_outline(body: PlaceOutline, request: Request) -> Object:
        """The building outline at a declared position, where one is mapped.

        Germany answers from its states' LoD2 and the Netherlands, Switzerland
        and Liechtenstein from their own 3D models (including measured roof
        planes); every other country answers from open 2D building footprints.
        A position with no mapped building says so rather than guessing.
        """
        actor = verified_actor(request.scope)
        with workspace.database.read() as connection:
            active_actor(connection, actor)
        place = geo.lookup(body.query.strip(), body.country)
        if place is None:
            raise NotFound("place not found")
        official = _official_3d_outline(place, body.latitude, body.longitude)
        if official is not None:
            return official
        found = footprints.outline_payload(place.country, body.latitude, body.longitude)
        if found is None:
            return {
                "schema_version": 1,
                "found": False,
                "country_code": place.country,
            }
        return {
            "schema_version": 1,
            "found": True,
            "country_code": place.country,
            "outline": found["outline"],
            "source": found["source"],
            "licence": found["licence"],
            "planes": found.get("planes", []),
        }

    @app.post("/handoffs/prepare")
    def prepare_handoff(body: HandoffPrepare, request: Request) -> Object:
        return Handoffs(workspace).prepare(
            verified_actor(request.scope, write=True),
            body.project_id,
            body.report_run_id,
            body.expected_revision,
            key=body.key,
        )

    @app.post("/handoffs/admit-inquiry")
    def admit_inquiry(body: InquiryAdmission, request: Request) -> Object:
        return Handoffs(workspace).admit_inquiry(
            verified_actor(request.scope, write=True),
            body.handoff_id,
            body.snapshot_sha256,
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
        check_direct_beam(assets, actor, None, body.inputs)
        check_geometric_pv(assets, actor, None, body.inputs)
        check_equipment_candidate(
            workspace, actor, None, body.inputs, products=products
        )
        if products is not None:
            products.check_project(body.inputs)
        return project_view(
            workspace.create(
                actor,
                body.title,
                body.inputs,
                key=body.key,
                input_contract=body.input_contract,
            )
        )

    @app.post("/projects/list")
    def listing(body: ProjectList, request: Request) -> Object:
        page_size = (
            min(30, limits.max_page_size) if body.page_size is None else body.page_size
        )
        if page_size > limits.max_page_size:
            raise InvalidInput("project page exceeds deployment limit")
        return project_page(
            workspace,
            verified_actor(request.scope),
            page_size,
            body.after,
            body.title_query,
        )

    @app.post("/projects/read")
    def read(body: ProjectRead, request: Request) -> Object:
        return project_view(
            workspace.get(
                verified_actor(request.scope), body.project_id, revision=body.revision
            )
        )

    @app.post("/projects/assistant")
    def assistant(body: ProjectAssistant, request: Request) -> Object:
        return assistant_context(
            workspace,
            verified_actor(request.scope),
            body.project_id,
            body.revision,
            list(body.run_ids),
            body.locale,
            unsaved_changes=body.unsaved_changes,
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
        check_direct_beam(assets, actor, body.project_id, body.inputs)
        check_geometric_pv(assets, actor, body.project_id, body.inputs)
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
                input_contract=body.input_contract,
            )
        )

    @app.post("/projects/admit-inquiry")
    def admit_project_inquiry(body: ProjectInquiry, request: Request) -> Object:
        return workspace.admit_project_inquiry(
            verified_actor(request.scope, write=True), body.project_id, body.revision
        )

    @app.post("/projects/prepared-handoffs")
    def prepared_handoffs(body: PreparedHandoffs, request: Request) -> Object:
        return workspace.prepared_handoffs(
            verified_actor(request.scope, write=True), body.project_id
        )

    @app.post("/projects/delete")
    def delete(body: ProjectDelete, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "projects/delete", body)
        if previous is not None:
            return previous
        return workspace.delete(
            actor, body.project_id, body.expected_revision, key=body.key
        )

    @app.post("/projects/delete-after-inquiry-check")
    def checked_delete(body: CheckedProjectDelete, request: Request) -> Object:
        return workspace.delete(
            verified_actor(request.scope, write=True),
            body.project_id,
            body.expected_revision,
            key=body.key,
            inquiry_generation=body.inquiry_generation,
        )

    @app.post("/projects/runs")
    def runs(body: ProjectRuns, request: Request) -> Object:
        page_size = (
            min(20, limits.max_page_size) if body.page_size is None else body.page_size
        )
        if page_size > limits.max_page_size:
            raise InvalidInput("run page exceeds deployment limit")
        return run_page(
            workspace,
            verified_actor(request.scope),
            body.project_id,
            page_size,
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
        from .installation_terminals import has_terminal_feature

        project = workspace.get(verified_actor(request.scope), body.project_id)
        if (
            body.expected_revision is not None
            and body.expected_revision != project.revision
        ):
            raise Conflict("project inputs have changed")
        if products is None:
            raise VersionUnavailable("current Woo installation evidence is unavailable")
        inputs: Object = {"geometry": body.geometry, "installation": body.installation}
        for field in (
            "pv_string_plan",
            "pv_plant_string_plan",
            "equipment_plant",
            "equipment_plant_setup",
        ):
            if field in project.inputs:
                inputs[field] = project.inputs[field]
        plan = InstallationInputs.read(body.installation)
        basis = product_basis(
            plan,
            products.equipment_basis(include_cables=True),
            allow_stale=inputs.get("pv_plant_string_plan") is not None
            or has_terminal_feature(plan),
        )
        reply = route_takeoff(
            inputs,
            basis,
            bind_geometry=body.bind_geometry,
            allow_stale_products=inputs.get("pv_plant_string_plan") is not None,
        )
        products.confirm_basis(basis, require_reference=False)
        reply["project_id"] = body.project_id
        if body.expected_revision is not None:
            reply["project_revision"] = project.revision
        reply["runtime_sha256"] = energy.kernel.runtime.sha256
        return reply

    @app.post("/runs/read")
    def run_read(body: RunRead, request: Request) -> Object:
        actor = verified_actor(request.scope)
        return owned_run_view(workspace, actor, workspace.run(actor, body.run_id))

    @app.post("/runs/inputs")
    def run_inputs(body: RunInputsRead, request: Request) -> Object:
        run = workspace.run(verified_actor(request.scope), body.run_id)
        if run.project_id != body.project_id:
            raise NotFound("run not found in this project")
        inputs = workspace.pinned_inputs(run.manifest)
        return {
            "schema_version": 1,
            "project_id": run.project_id,
            "run_id": run.id,
            "manifest_sha256": run.manifest_sha256,
            "inputs": display_document(inputs, project_panels(inputs), inputs=True),
        }

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

    @app.post("/runs/calculate")
    def calculate(body: EnergyCalculate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/calculate", body)
        if previous is not None:
            return previous
        project, run = energy.calculate(
            actor,
            body.project_id,
            body.expected_revision,
            body.inputs,
            key=body.key,
            input_contract=body.input_contract,
        )
        return {
            "schema_version": 1,
            "project": project_view(project),
            "run": run_view(run),
        }

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

    @app.post("/runs/direct-beam")
    def prepare_direct_beam(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/direct-beam", body)
        if previous is not None:
            return previous
        if direct_beam is None:
            raise VersionUnavailable("direct-beam visibility is not configured")
        return run_view(
            direct_beam.evaluate(
                actor, body.project_id, body.expected_revision, key=body.key
            )
        )

    @app.post("/runs/geometric-pv")
    def prepare_geometric_pv(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/geometric-pv", body)
        if previous is not None:
            return previous
        if geometric_pv is None:
            raise VersionUnavailable("geometric PV generation is not configured")
        return run_view(
            geometric_pv.evaluate(
                actor, body.project_id, body.expected_revision, key=body.key
            )
        )

    @app.post("/runs/pvgis-reference")
    def prepare_pvgis_reference(body: EnergyEvaluate, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/pvgis-reference", body)
        if previous is not None:
            return previous
        if pvgis_reference is None:
            raise VersionUnavailable("PVGIS roof reference is not configured")
        return run_view(
            pvgis_reference.evaluate(
                actor, body.project_id, body.expected_revision, key=body.key
            )
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

    @app.post("/runs/check-equipment")
    def check_current_equipment(body: EquipmentFind, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/check-equipment", body)
        if previous is not None:
            return previous
        if equipment is None:
            raise VersionUnavailable("equipment qualification is not configured")
        project, run = equipment.check(
            actor,
            body.project_id,
            body.expected_revision,
            body.inputs,
            key=body.key,
            input_contract=body.input_contract,
        )
        return {
            "schema_version": 1,
            "project": project_view(project),
            "run": run_view(run),
        }

    @app.post("/runs/find-equipment")
    def find_current_equipment(body: EquipmentFind, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        previous = previous_result(actor, "runs/find-equipment", body)
        if previous is not None:
            return previous
        if equipment_search is None:
            raise VersionUnavailable("equipment search is not configured")
        project, run = equipment_search.find(
            actor,
            body.project_id,
            body.expected_revision,
            body.inputs,
            key=body.key,
            input_contract=body.input_contract,
        )
        return {
            "schema_version": 1,
            "project": project_view(project),
            "run": run_view(run),
        }

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

    @app.post("/equipment/certificates/read")
    def equipment_certificates(body: CertificateRead, request: Request) -> Object:
        return CertificateEvidence(workspace).read(
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

    @app.post("/weather/assets")
    def owned_weather(body: WeatherAssetsRead, request: Request) -> Object:
        if direct_beam is None and geometric_pv is None:
            raise VersionUnavailable(
                "retained-weather geometry services are not configured"
            )
        if body.page_size > limits.max_page_size:
            raise InvalidInput("weather page exceeds deployment limit")
        return weather_assets(
            assets,
            verified_actor(request.scope),
            body.project_id,
            offset=body.offset,
            page_size=body.page_size,
        )

    @app.post("/weather/preview")
    def preview_weather(body: ProfilePreviewRead, request: Request) -> Object:
        selected = direct_beam or geometric_pv
        if selected is None:
            raise VersionUnavailable(
                "retained-weather geometry services are not configured"
            )
        if body.page_size > limits.max_page_size:
            raise InvalidInput("weather page exceeds deployment limit")
        return weather_preview(
            assets,
            verified_actor(request.scope),
            body.project_id,
            body.asset_id,
            selected.kernel.weather_limits,
            offset=body.offset,
            page_size=body.page_size,
        )

    @app.post("/assets/read")
    def asset_read(body: AssetRead, request: Request) -> Object:
        return asset_view(
            assets.customer_asset(
                verified_actor(request.scope), body.project_id, body.asset_id
            )
        )

    @app.post("/assets/content")
    def asset_content(body: AssetRead, request: Request) -> Response:
        asset = assets.customer_asset(
            verified_actor(request.scope), body.project_id, body.asset_id
        )
        return Response(
            workspace.blobs.read(asset.content_sha256),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{body.asset_id}"'},
        )

    @app.post("/profiles/csv")
    def csv_profile(body: CsvImport, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        return asset_view(intake.csv(actor, body))

    @app.post("/profiles/standard")
    def standard_profile(body: StandardProfile, request: Request) -> Object:
        actor = verified_actor(request.scope, write=True)
        return asset_view(intake.standard(actor, body))

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
