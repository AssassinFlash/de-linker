"""An authenticated inventory request never redirects to a different origin."""

from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Any


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    """Check before urllib copies the authenticated request's headers."""

    def __init__(self, base: str) -> None:
        self._origin = self._origin_of(base)

    @staticmethod
    def _origin_of(url: str) -> tuple[str, str | None, int | None]:
        parsed = urllib.parse.urlsplit(url)
        default_port = {"http": 80, "https": 443}.get(parsed.scheme)
        return parsed.scheme, parsed.hostname, parsed.port or default_port

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if self._origin_of(newurl) != self._origin:
            raise RuntimeError("Inventory REST redirect left the configured origin.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)
