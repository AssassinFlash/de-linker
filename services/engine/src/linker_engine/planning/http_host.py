"""Mount private planning outside the existing engine's Gate and CORS layers.

The legacy FastAPI app retains its lifespan and routes. Planning allocates
short-lived SQLite connections per operation, has no startup/background hook
and runs no numerical work in its HTTP lifetime.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, Router
from starlette.types import ASGIApp, Receive, Scope, Send

from .http_app import create_private_app
from .product_sources import ProductProvider
from .runtime_config import RuntimeConfig

LOG = logging.getLogger(__name__)


async def unavailable(scope: Scope, receive: Receive, send: Send) -> None:
    # No configured operation exists and no request body is consumed. This
    # response is private even when configuration/DB startup fails.
    response = JSONResponse(
        {"error": {"code": "service_unconfigured"}},
        status_code=503,
        headers={
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
    await response(scope, receive, send)


def configured_private_app(
    config: RuntimeConfig | None = None,
    *,
    product_provider: Callable[[], ProductProvider] | None = None,
) -> ASGIApp:
    try:
        settings = config or RuntimeConfig.from_environment()
        workspace, energy = settings.open()
        return create_private_app(
            workspace,
            energy,
            credential=lambda: os.environ.get("GENIE_SERVICE_TOKEN", ""),
            limits=settings.http_limits(),
            pv=settings.pv_service(workspace),
            weather=settings.weather_service(workspace),
            product_provider=product_provider,
        )
    except Exception:
        LOG.exception("planning service configuration is unavailable")
        return unavailable


class AsgiEndpoint:
    """Starlette Route treats functions as Request handlers, not ASGI apps."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)


class EngineApplications:
    def __init__(self, legacy: ASGIApp, planning: ASGIApp) -> None:
        self.legacy = legacy
        self.router = Router(
            routes=[
                # Cover the bare prefix without Router's public redirect.
                Route("/planning", endpoint=AsgiEndpoint(planning)),
                Mount("/planning", app=planning),
                Mount("/", app=legacy),
            ]
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.legacy(scope, receive, send)
        else:
            await self.router(scope, receive, send)
