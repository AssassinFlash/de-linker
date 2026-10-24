"""HTTP entry point: `uvicorn linker_engine.app:app`.

Configuration comes from the environment:
- LINKER_ENGINE_FEED: the engineering feed (JSON file of #8's feed endpoint);
- LINKER_ENGINE_COMPATIBILITY: data/compatibility.json of linker-commerce;
- LINKER_ENGINE_CACHE: directory for the PVGIS and LoD2 caches
  (default ~/.cache/linker-engine);
- LINKER_ENGINE_CORS_ORIGINS: comma-separated origins allowed to call the API.
The feed and the compatibility file are validated against their schemas when
they are first needed; an invalid one is refused, never patched.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import commercial, geo, imagery, pdf, report, residential, version
from .compatibility import Compatibility
from .engine import Engine
from .gate import Gate
from .models import (
    CommercialInput,
    CommercialResult,
    PlaceResult,
    ReportRequest,
    ResidentialInput,
    ResidentialResult,
    RoofPackRequest,
    RoofPlaneResult,
    RoofRequest,
    RoofResult,
    SelectionRequest,
)
from .products import Products
from .publication import (
    Publication,
    PublicationChanged,
    PublicationUnavailable,
    ReferenceEvidenceUnavailable,
    View,
    fingerprint,
)
from .pvgis import Pvgis, YieldUnavailable
from .roof import service as roof_service
from .roof.lod2 import Lod2Unavailable
from .selections import Selections


@dataclass
class Settings:
    feed: Path
    compatibility: Path
    cache: Path

    @classmethod
    def from_environment(cls) -> Settings:
        missing = [
            name
            for name in ("LINKER_ENGINE_FEED", "LINKER_ENGINE_COMPATIBILITY")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(f"set {', '.join(missing)}")
        cache = os.environ.get("LINKER_ENGINE_CACHE") or str(
            Path.home() / ".cache" / "linker-engine"
        )
        return cls(
            feed=Path(os.environ["LINKER_ENGINE_FEED"]),
            compatibility=Path(os.environ["LINKER_ENGINE_COMPATIBILITY"]),
            cache=Path(cache),
        )


class Services:
    """The loaded data and clients, created once per process."""

    def __init__(self, settings: Settings, source: tuple[bytes, ...]) -> None:
        self.settings = settings
        feed_path = settings.feed.resolve()
        manifest_path = feed_path.parent / "manifest.json"
        feed = feed_path.read_bytes()
        compatibility = (
            feed_path.parent / "compatibility.json"
            if manifest_path.exists()
            else settings.compatibility
        ).read_bytes()
        if manifest_path.exists():
            generation = json.loads(manifest_path.read_text())
            if (
                generation["feed_sha256"] != hashlib.sha256(feed).hexdigest()
                or generation["compatibility_sha256"]
                != hashlib.sha256(compatibility).hexdigest()
            ):
                raise ValueError("engineering generation bytes do not match manifest")
        loaded_feed = json.loads(feed)
        if loaded_feed.get("compatibility") != json.loads(compatibility):
            raise ValueError("feed and compatibility are not one generation")
        self.publication = Publication(loaded_feed)
        self.engine = Engine(
            products=Products.from_feed(json.loads(feed)),
            compatibility=Compatibility(json.loads(compatibility)),
            pvgis=Pvgis(settings.cache / "pvgis"),
        )
        self.selections = Selections(settings.cache / "private")
        self.version = version.digest(source, feed, compatibility)

    @cached_property
    def roof(self) -> roof_service.RoofService:
        return roof_service.RoofService(
            self.settings.cache / "lod2", self.engine.products.module
        )


# Captured after module imports, before a running app accepts any requests.
# Publishing uses immutable releases; later feed writes cannot relabel loaded data.
SOURCE = version.source_bytes(Path(__file__).resolve().parent)


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Solution Configurator engine",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Commercial CSV is capped at 4MB; report logo at 700kB (models.py).
    # 6MiB leaves JSON headroom without accepting unbounded parse/temp work.
    app.add_middleware(Gate, limit=6 * 1024 * 1024, version=lambda: services().version)
    origins = [
        o.strip()
        for o in os.environ.get("LINKER_ENGINE_CORS_ORIGINS", "").split(",")
        if o.strip()
    ]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    holder: dict[str, Services] = {}
    loading = threading.Lock()
    source = SOURCE

    def services() -> Services:
        with loading:
            if "services" not in holder:
                holder["services"] = Services(
                    settings or Settings.from_environment(), source
                )
            return holder["services"]

    # The private planner consumes this same loader; it has no second product
    # registry or mutable feed cache. Construction remains lazy and locked.
    app.state.planning_product_provider = services

    def unavailable(error: Exception, code: str) -> HTTPException:
        detail = {"error": code, "message": str(error)}
        if isinstance(error, ReferenceEvidenceUnavailable):
            detail["reason"] = "reference_evidence_unavailable"
        return HTTPException(status_code=503, detail=detail)

    @app.middleware("http")
    async def loaded_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.method == "POST" and response.status_code < 400:
            response.headers["X-Linker-Engine-Version"] = services().version
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

    @app.get("/resource/version")
    def resource_version(request: Request, response: Response) -> dict[str, Any]:
        """Authenticated read of the loaded snapshot; never an anonymous proxy route."""
        expected = os.environ.get("GENIE_SERVICE_TOKEN", "")
        if not expected:
            raise HTTPException(status_code=503, detail="service token unavailable")
        given = request.headers.get("x-linker-service-token", "").encode(
            "latin-1", "ignore"
        )
        if not hmac.compare_digest(given, expected.encode()):
            raise HTTPException(status_code=401, detail="unauthorized")
        try:
            current = services().version
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(
                status_code=503, detail="engine version unavailable"
            ) from error
        response.headers["Cache-Control"] = "private, no-store"
        snapshot: dict[str, Any] = {
            "version": current,
            "source_revision": str(
                services().publication.feed.get("source_revision", "")
            ),
            "compatibility_revision": str(
                services().publication.feed.get("compatibility_revision", "")
            ),
        }
        if request.query_params.get("ready") == "1":
            try:
                snapshot["prepared_products"] = (
                    services().publication.prepared_products(services().engine)
                )
            except PublicationUnavailable as error:
                raise unavailable(error, "publication_unavailable") from error
        return snapshot

    @app.get("/geo/plz/{plz}")
    def place(plz: str) -> PlaceResult:
        """Map position, federal state and aerial imagery service for a postcode."""
        found = geo.lookup(plz)
        if found is None:
            raise HTTPException(
                status_code=404, detail={"error": "unknown_plz", "field": "plz"}
            )
        return PlaceResult(
            plz=found.plz,
            latitude=found.latitude,
            longitude=found.longitude,
            state=found.state,
            place=found.name,
            attribution=geo.ATTRIBUTION,
            imagery=imagery.for_state(found.state),
        )

    def compute(
        request: ResidentialInput | CommercialInput,
    ) -> ResidentialResult | CommercialResult:
        loaded = services()
        try:
            view = loaded.publication.view(
                loaded.engine,
                require_reference=isinstance(request, ResidentialInput)
                and request.existing_inverter is None,
            )
            if isinstance(request, ResidentialInput):
                design = residential.design(view.engine, request)
                result: ResidentialResult | CommercialResult = residential.result(
                    design, report.residential(design, now())
                )
            else:
                result = commercial.design(view.engine, request, now())
            loaded.publication.confirm(view)
            result.publication = view.dependencies
            result.selection_fingerprint = fingerprint(
                request.model_dump(mode="json"),
                result.model_dump(mode="json", by_alias=True),
                view.dependencies,
            )
            loaded.selections.remember(request.model_dump(mode="json"), result)
            return result
        except PublicationChanged as error:
            raise HTTPException(
                status_code=409, detail={"error": "publication_changed"}
            ) from error
        except PublicationUnavailable as error:
            raise unavailable(error, "publication_unavailable") from error
        except residential.DesignInputError as error:
            raise HTTPException(
                status_code=422, detail={"error": "invalid_input", "field": error.field}
            ) from error
        except YieldUnavailable as error:
            raise unavailable(error, "yield_unavailable") from error
        except commercial.LoadProfileError as error:
            raise HTTPException(
                status_code=422, detail={"error": "load_profile", "message": str(error)}
            ) from error

    @app.post("/design/residential", response_model_by_alias=True)
    def design_residential(
        request: ResidentialInput,
    ) -> ResidentialResult | CommercialResult:
        return compute(request)

    @app.post("/design/commercial")
    def design_commercial(
        request: CommercialInput,
    ) -> ResidentialResult | CommercialResult:
        return compute(request)

    @app.post("/selection/validate", response_model_by_alias=True)
    def selection_validate(
        request: SelectionRequest, http: Request
    ) -> ResidentialResult | CommercialResult:
        expected = os.environ.get("GENIE_SERVICE_TOKEN", "")
        if not expected or not hmac.compare_digest(
            http.headers.get("x-linker-service-token", "").encode("latin-1", "ignore"),
            expected.encode(),
        ):
            raise HTTPException(status_code=401, detail="unauthorized")
        if (request.kind == "residential") != isinstance(
            request.input, ResidentialInput
        ):
            raise HTTPException(
                status_code=422, detail={"error": "invalid_input", "field": "kind"}
            )
        return confirmed(request.input, request.selection_fingerprint, request.kind)

    def confirmed(
        input_: ResidentialInput | CommercialInput,
        selection_fingerprint: str,
        kind: str,
    ) -> ResidentialResult | CommercialResult:
        loaded = services()
        result = loaded.selections.read(
            input_.model_dump(mode="json"), selection_fingerprint, kind
        )
        if result is None or not result.publication:
            raise HTTPException(status_code=409, detail={"error": "selection_changed"})
        try:
            loaded.publication.confirm(
                View(loaded.engine, result.publication),
                require_reference=reference_used(input_, result),
            )
        except PublicationChanged as error:
            raise HTTPException(
                status_code=409, detail={"error": "publication_changed"}
            ) from error
        except PublicationUnavailable as error:
            raise unavailable(error, "publication_unavailable") from error
        return result

    def reference_used(
        input_: ResidentialInput | CommercialInput,
        result: ResidentialResult | CommercialResult,
    ) -> bool:
        return (
            isinstance(input_, ResidentialInput)
            and input_.existing_inverter is None
            and isinstance(result, ResidentialResult)
            and bool(result.candidates.inverters or result.candidates.excluded)
        )

    @app.post("/roof/outline")
    def roof_outline(request: RoofRequest) -> RoofResult:
        try:
            loaded = services()
            view = loaded.publication.reference_view(loaded.engine)
            result = loaded.roof.outline(request)
            loaded.publication.confirm(view)
            result.publication = view.dependencies
            return result
        except PublicationChanged as error:
            raise HTTPException(
                status_code=409, detail={"error": "publication_changed"}
            ) from error
        except PublicationUnavailable as error:
            raise unavailable(error, "publication_unavailable") from error
        except Lod2Unavailable as error:
            raise unavailable(error, "lod2_unavailable") from error

    @app.post("/roof/pack")
    def roof_pack(request: RoofPackRequest) -> RoofPlaneResult:
        """Modules on a roof plane drawn by hand."""
        loaded = services()
        try:
            view = loaded.publication.reference_view(loaded.engine)
            result = roof_service.pack_drawn(request, view.engine.products.module)
            loaded.publication.confirm(view)
            result.publication = view.dependencies
            return result
        except PublicationChanged as error:
            raise HTTPException(
                status_code=409, detail={"error": "publication_changed"}
            ) from error
        except PublicationUnavailable as error:
            raise unavailable(error, "publication_unavailable") from error

    @app.post("/report/pdf")
    def report_pdf(request: ReportRequest) -> Response:
        result = confirmed(request.input, request.selection_fingerprint, "residential")
        if not isinstance(result, ResidentialResult):
            raise HTTPException(status_code=409, detail={"error": "selection_changed"})
        try:
            document = pdf.render(result.report, request.logo)
            # Rendering can take time: validate again immediately before bytes.
            loaded = services()
            loaded.publication.confirm(
                View(loaded.engine, result.publication or {}),
                require_reference=reference_used(request.input, result),
            )
        except PublicationChanged as error:
            raise HTTPException(
                status_code=409, detail={"error": "publication_changed"}
            ) from error
        except PublicationUnavailable as error:
            raise unavailable(error, "publication_unavailable") from error
        except pdf.LogoError as error:
            raise HTTPException(
                status_code=422, detail={"error": "invalid_input", "field": "logo"}
            ) from error
        name = f"linker-design-report-{request.input.plz}-{request.input.locale}.pdf"
        return Response(
            content=document,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    return app


app = create_app()
