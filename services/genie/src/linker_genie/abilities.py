"""HTTP client for WordPress Abilities (`wp-abilities/v1`).

The service holds no WordPress identity of its own: no service token, no
Authorization header. A login-gated ability asked without a customer answers
401 and that maps to the `login_required` fact, so the model asks the customer
to log in instead of failing the turn (docs/specs/13-genie.md R7).

A call that fails transiently - a 5xx, or the connection itself dropping -
is retried before the turn gives up on it. The WordPress side reads through
a Redis object cache, and when Redis hiccups mid-request the ability dies
fast with a 500 (the review instance's PHP error log holds a burst of
Predis connection exceptions, one per dead request; the instance now runs
its object cache in graceful mode, and this retry covers whatever transient
failure still slips through). Three attempts with an exponential backoff
ride the blip out; a call that still fails raises `AbilityError`, which the
turn cycle turns into the deterministic fallback - the failure is logged in
the turn's meta, never swallowed.

The customer's identity rides only where the answer depends on the customer: a
signed-in customer's turn carries the shell's short-lived identity token (valid
120 seconds after it is minted; the browser never sees it, the service never
stores or logs it), and the service sends it as `USER_CONTEXT_HEADER` on the
abilities in `USER_CONTEXT_ABILITIES` — the customer's own inquiry list, and the
product abilities whose prices follow the account (#242: CommerceState shows an
approved account its net prices and nobody else). WordPress accepts it on
`/wp-abilities/` requests only, verifies the signature and the expiry, and
answers as that customer; an expired or forged token answers as a guest.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx

from linker_genie.facts import TurnFacts, collect, merge

# The header the shell's token travels in; WordPress' UserContext accepts it.
USER_CONTEXT_HEADER = "X-Linker-User-Context"
# The ability that answers about the browsing customer's own inquiries.
USER_CONTEXT_ABILITY = "linker/inquiry-status"
# Every ability whose answer depends on the browsing customer: the inquiry list,
# and the product abilities whose commerce object carries the customer's prices
# (ProductCommerce in linker-commerce; compare-products' columns read the same
# rule). check-compatibility, size-hint and handoff-team answer the same for
# everybody and never see the token.
USER_CONTEXT_ABILITIES = frozenset(
    {
        USER_CONTEXT_ABILITY,
        "linker/search-products",
        "linker/get-product",
        "linker/compare-products",
    }
)

ABILITY_NAMES = (
    "linker/search-products",
    "linker/get-product",
    "linker/compare-products",
    "linker/check-compatibility",
    "linker/size-hint",
    "linker/inquiry-status",
    "linker/handoff-team",
)

# Attempts per ability call, and the first backoff wait (doubled per retry).
# Both stay small: the calls ride the loopback and one turn has the shell's
# 60 s proxy budget, of which a single call may already spend 20 s.
ABILITY_ATTEMPTS = 3
ABILITY_BACKOFF = 0.25


class AbilityError(RuntimeError):
    """The WordPress abilities endpoint refused or could not be reached."""


class AbilityClient:
    """GET `/wp-json/wp-abilities/v1/abilities/{name}/run`, as the customer or a guest."""

    def __init__(
        self,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        # One ability call times out at twenty seconds: the slowest call is a
        # search over the catalogue plus embedding work, and one turn makes at
        # most four calls (MAX_TOOL_CALLS) inside the shell's 60 s proxy
        # timeout, so a single call must stay well under both.
        timeout: float = 20.0,
        # The clock of the retry backoff; injected so tests need no waiting.
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )
        self._sleep = sleep

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
        # The slash in `linker/search-products` stays raw: the production site
        # sits behind LiteSpeed, which answers an encoded slash with 404
        # (measured 2026-10-14: `linker%2Fsearch-products` 404, the raw path
        # 200), and every ability name carries one. The name is checked against
        # the allowlist above, so nothing unquoted can slip through.
        path = f"/wp-json/wp-abilities/v1/abilities/{quote(name, safe='/')}/run"
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
            if user_context and name in USER_CONTEXT_ABILITIES
            else None
        )
        response = self._get(name, path, params, headers)
        if response.status_code == 401:
            # A login-gated ability asked without a user: the caller must ask
            # for a login, not fail the turn (docs/specs/13-genie.md R7).
            # Every 401 maps here: the product abilities are open to guests,
            # so only the inquiry list answers 401, and only without a valid
            # customer.
            return {"error": "login_required"}
        if response.status_code >= 400:
            raise AbilityError(
                f"{name} returned {response.status_code} for {dict(params)}"
            )
        body = response.json()
        if isinstance(body, dict) and "result" in body:
            return body["result"]
        return body

    def _get(
        self,
        name: str,
        path: str,
        params: dict[str, Any],
        headers: dict[str, str] | None,
    ) -> httpx.Response:
        """GET with the transient-failure retry (module docstring)."""
        for attempt in range(1, ABILITY_ATTEMPTS + 1):
            try:
                response = self._client.get(path, params=params, headers=headers)
            except httpx.TransportError as error:
                if attempt == ABILITY_ATTEMPTS:
                    raise AbilityError(
                        f"{name} could not be reached: {error}"
                    ) from error
            else:
                # 4xx answers are final: the 401 is the login_required fact
                # and every other 4xx is the caller's mistake. Only a 5xx -
                # the shape a dying ability call answers with - retries.
                if response.status_code < 500 or attempt == ABILITY_ATTEMPTS:
                    return response
            self._sleep(ABILITY_BACKOFF * 2 ** (attempt - 1))
        raise AbilityError(f"{name} did not answer after {ABILITY_ATTEMPTS} attempts")

    def record(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        user_context: str | None = None,
        locale: str = "en",
    ) -> tuple[Any, TurnFacts]:
        """Run the ability and collect its facts in the turn's language."""
        payload = self.run(name, arguments, user_context)
        gathered = collect(name, payload, locale)
        # The result is logged with the call: the quality check judges the
        # answer against what the model read, not against a later replay
        # (stock, prices and a signed-in customer's inquiries change).
        gathered.tool_calls.append(
            {"name": name, "arguments": arguments or {}, "ok": True, "result": payload}
        )
        return payload, gathered


def gather(parts: list[TurnFacts]) -> TurnFacts:
    return merge(parts)
