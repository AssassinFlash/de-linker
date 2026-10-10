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

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import commercial, geo, imagery, pdf, report, residential
from .catalog import Catalog
from .compatibility import Compatibility
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
from .products import Engine
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

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def engine(self) -> Engine:
        return Engine(
            catalog=Catalog.load(self.settings.feed),
            compatibility=Compatibility.load(self.settings.compatibility),
            pvgis=Pvgis(self.settings.cache / "pvgis"),
        )

    @cached_property
    def roof(self) -> roof_service.RoofService:
        return roof_service.RoofService(
            self.settings.cache / "lod2", self.engine.catalog.module
        )


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Solution Configurator engine")
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

    def services() -> Services:
        if "services" not in holder:
            holder["services"] = Services(settings or Settings.from_environment())
        return holder["services"]

    def unavailable(error: Exception, code: str) -> HTTPException:
        return HTTPException(
            status_code=503, detail={"error": code, "message": str(error)}
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

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
        return roof_service.pack_drawn(request, services().engine.catalog.module)

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
