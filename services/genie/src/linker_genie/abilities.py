"""HTTP client for WordPress Abilities (`wp-abilities/v1`).

Every ability is called anonymously, with no token and no Authorization
header. A login-gated ability answers 401 and that maps to the
`login_required` fact, so the model asks the customer to log in instead of
failing the turn (docs/specs/13-genie.md R7).

The one exception is the customer's own inquiry list: the turn carries the
shell's short-lived identity token (valid 120 seconds after it is minted; the
browser never sees it, the service never stores it), and the service sends it
on exactly one ability call — `linker/inquiry-status` — as
`USER_CONTEXT_HEADER`. WordPress accepts it on `/wp-abilities/` requests only,
verifies the signature and the expiry, and nothing else in the service can
use it.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from linker_genie.facts import TurnFacts, collect, merge

# The header the shell's token travels in; WordPress' UserContext accepts it.
USER_CONTEXT_HEADER = "X-Linker-User-Context"
# The one ability that answers about the browsing customer.
USER_CONTEXT_ABILITY = "linker/inquiry-status"

ABILITY_NAMES = (
    "linker/search-products",
    "linker/get-product",
    "linker/compare-products",
    "linker/check-compatibility",
    "linker/size-hint",
    "linker/inquiry-status",
    "linker/handoff-team",
    "linker/search-knowledge",
)


class AbilityError(RuntimeError):
    """The WordPress abilities endpoint refused or could not be reached."""


class AbilityClient:
    """GET `/wp-json/wp-abilities/v1/abilities/{name}/run`, anonymously."""

    def __init__(
        self,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        # One ability call times out at twenty seconds: the slowest call is a
        # search over the catalogue plus embedding work, and one turn makes at
        # most four calls (MAX_TOOL_CALLS) inside the shell's 60 s proxy
        # timeout, so a single call must stay well under both.
        timeout: float = 20.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def run(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        user_context: str | None = None,
    ) -> Any:
        if name not in ABILITY_NAMES:
            raise AbilityError(f"unknown ability {name}")
        path = f"/wp-json/wp-abilities/v1/abilities/{quote(name, safe='')}/run"
        # Read-only abilities take GET; the input rides as nested query params,
        # which the abilities REST controller reads back as `input`.
        params: dict[str, Any] = {}
        for key, value in (arguments or {}).items():
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    params[f"input[{key}][{index}]"] = item
            else:
                params[f"input[{key}]"] = value
        headers = (
            {USER_CONTEXT_HEADER: user_context}
            if user_context and name == USER_CONTEXT_ABILITY
            else None
        )
        response = self._client.get(path, params=params, headers=headers)
        if response.status_code == 401:
            # A login-gated ability asked without a user: the caller must ask
            # for a login, not fail the turn (docs/specs/13-genie.md R7).
            # Every 401 maps here; without a token there is no other meaning.
            return {"error": "login_required"}
        if response.status_code >= 400:
            raise AbilityError(
                f"{name} returned {response.status_code} for {dict(params)}"
            )
        body = response.json()
        if isinstance(body, dict) and "result" in body:
            return body["result"]
        return body

    def record(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        user_context: str | None = None,
    ) -> tuple[Any, TurnFacts]:
        payload = self.run(name, arguments, user_context)
        gathered = collect(name, payload)
        gathered.tool_calls.append(
            {"name": name, "arguments": arguments or {}, "ok": True}
        )
        return payload, gathered


def gather(parts: list[TurnFacts]) -> TurnFacts:
    return merge(parts)
