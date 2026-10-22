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

import hmac
import json
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path

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
)
from .products import Products
from .pvgis import Pvgis, YieldUnavailable
from .roof import service as roof_service
from .roof.lod2 import Lod2Unavailable


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
        feed = settings.feed.read_bytes()
        compatibility = settings.compatibility.read_bytes()
        self.engine = Engine(
            products=Products.from_feed(json.loads(feed)),
            compatibility=Compatibility(json.loads(compatibility)),
            pvgis=Pvgis(settings.cache / "pvgis"),
        )
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

    def unavailable(error: Exception, code: str) -> HTTPException:
        return HTTPException(
            status_code=503, detail={"error": code, "message": str(error)}
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

    @app.get("/resource/version")
    def resource_version(request: Request, response: Response) -> dict[str, str]:
        """Authenticated read of the loaded snapshot; never an anonymous proxy route."""
        if os.environ.get("LINKER_ENGINE_GATE_MODE", "off") != "enforce":
            raise HTTPException(status_code=503, detail="engine gate unavailable")
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
        return {"version": current}

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

    @app.post("/design/residential", response_model_by_alias=True)
    def design_residential(request: ResidentialInput) -> ResidentialResult:
        try:
            design = residential.design(services().engine, request)
        except residential.DesignInputError as error:
            raise HTTPException(
                status_code=422, detail={"error": "invalid_input", "field": error.field}
            ) from error
        except YieldUnavailable as error:
            raise unavailable(error, "yield_unavailable") from error
        return residential.result(design, report.residential(design, now()))

    @app.post("/design/commercial")
    def design_commercial(request: CommercialInput) -> CommercialResult:
        try:
            return commercial.design(services().engine, request, now())
        except commercial.LoadProfileError as error:
            raise HTTPException(
                status_code=422, detail={"error": "load_profile", "message": str(error)}
            ) from error

    @app.post("/roof/outline")
    def roof_outline(request: RoofRequest) -> RoofResult:
        try:
            return services().roof.outline(request)
        except Lod2Unavailable as error:
            raise unavailable(error, "lod2_unavailable") from error

    @app.post("/roof/pack")
    def roof_pack(request: RoofPackRequest) -> RoofPlaneResult:
        """Modules on a roof plane drawn by hand."""
        return roof_service.pack_drawn(request, services().engine.products.module)

    @app.post("/report/pdf")
    def report_pdf(request: ReportRequest) -> Response:
        try:
            design = residential.design(services().engine, request.input)
        except residential.DesignInputError as error:
            raise HTTPException(
                status_code=422, detail={"error": "invalid_input", "field": error.field}
            ) from error
        except YieldUnavailable as error:
            raise unavailable(error, "yield_unavailable") from error
        try:
            document = pdf.render(report.residential(design, now()), request.logo)
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
