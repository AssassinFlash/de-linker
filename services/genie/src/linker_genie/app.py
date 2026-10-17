"""HTTP entry point: `uvicorn linker_genie.app:app`.

POST /assistant/turn and POST /turn (alias) stream one grounded turn as SSE: the
understanding layer prepares the turn (understand.py), the agent writes it.
POST /turn/{id}/vote and POST /assistant/turn/{id}/vote store a customer's
thumbs-up or thumbs-down for a logged turn. GET /health reports that the
process is up.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from linker_genie import jev, page
from linker_genie.abilities import AbilityClient
from linker_genie.agent import make_generate, model_name, provider_name
from linker_genie.cycle import TurnResult, run
from linker_genie.log import TurnLog
from linker_genie.prices import commerce_lookup
from linker_genie.schema import TurnRequest, VoteRequest
from linker_genie.storeapi import StoreVocabulary
from linker_genie.understand import Prepared, Understander

app = FastAPI(title="Genie - Linker's AI assistant")

_log: TurnLog | None = None
_client: AbilityClient | None = None
_understander: Understander | None = None
_pages: page.PageReader | None = None


def _log_path() -> Path:
    return Path(
        os.environ.get(
            "GENIE_LOG", str(Path.home() / ".cache" / "linker-genie" / "turns.sqlite")
        )
    )


def turn_log() -> TurnLog:
    global _log
    if _log is None:
        _log = TurnLog(_log_path())
    return _log


def ability_client() -> AbilityClient:
    global _client
    if _client is None:
        # No service token, ever: the only identity is the customer's own
        # short-lived token, passed per call (linker_genie.abilities).
        _client = AbilityClient(_wp_url())
    return _client


def _wp_url() -> str:
    return os.environ.get("GENIE_WP_URL", "http://127.0.0.1")


def page_reader() -> page.PageReader:
    """The pages of the site this service serves (page.py, #234)."""
    global _pages
    if _pages is None:
        _pages = page.PageReader(_wp_url())
    return _pages


def understander() -> Understander:
    """Product words from the site's Store API, Jev on OpenRouter, and the customer's
    page read from the site (understand.py)."""
    global _understander
    if _understander is None:
        _understander = Understander(
            StoreVocabulary(_wp_url()).get, jev.from_env(), pages=page_reader().read
        )
    return _understander


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}


@app.post("/assistant/turn")
@app.post("/turn")
def assistant_turn(body: TurnRequest, request: Request) -> StreamingResponse:
    """One conversation turn, grounded and hydrated, as SSE."""
    prepare = getattr(request.app.state, "prepare", None)
    prepared: Prepared = (
        prepare(body)
        if prepare is not None
        else understander().prepare(body, ability_client())
    )
    generate = getattr(request.app.state, "generate", None) or make_generate(
        ability_client(), prepared=prepared, pages=page_reader().read
    )
    commerce = getattr(request.app.state, "commerce", None) or commerce_lookup(
        ability_client(), body
    )
    try:
        result = run(body, generate, prepared.route, prepared.facts, commerce)
    except Exception as error:  # noqa: BLE001 - logged, then re-raised
        turn_log().record(
            conversation_id=body.conversation_id,
            locale=body.locale,
            grounded=False,
            failures=(f"internal: {error}",),
            fallback=True,
            provider=provider_name(),
            model=model_name(),
            tool_calls=[],
            output={},
            question=_question(body),
            page=body.page_context.model_dump(),
            understanding=prepared.log,
            approved=body.user.partner,
        )
        raise
    if result.retried and result.attempts > 1:
        prepared.log["retried"] = list(result.retried)
    if result.price_failures:
        # A card whose price line could not be read shows none; the cause is
        # logged with the turn, never swallowed (prices.fill).
        prepared.log["price_failures"] = list(result.price_failures)
    turn_id = turn_log().record(
        conversation_id=body.conversation_id,
        locale=body.locale,
        grounded=result.grounded,
        failures=result.failures,
        fallback=result.fallback,
        provider=provider_name(),
        model=model_name(),
        tool_calls=result.facts.tool_calls,
        output=result.output.model_dump(),
        question=_question(body),
        page=body.page_context.model_dump(),
        understanding=prepared.log,
        approved=body.user.partner,
    )
    return StreamingResponse(
        _sse(result, turn_id, prepared),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/turn/{turn_id}/vote")
@app.post("/assistant/turn/{turn_id}/vote")
def turn_vote(turn_id: int, body: VoteRequest) -> dict[str, bool]:
    """Store the customer's vote on one logged turn."""
    if not turn_log().vote(turn_id, body.vote):
        raise HTTPException(status_code=404, detail="unknown turn")
    return {"ok": True}


def _question(body: TurnRequest) -> str:
    """The customer message this turn answers: the thread's last user message."""
    for message in reversed(body.messages):
        if message.role == "user":
            return message.content
    return ""


def _sse(result: TurnResult, turn_id: int, prepared: Prepared) -> Iterator[str]:
    meta = {
        "turn_id": turn_id,
        "grounded": result.grounded,
        "fallback": result.fallback,
        "attempts": result.attempts,
        "failures": list(result.failures),
        "language": result.output.language,
        # The understanding layer's decision, so a degraded turn is visible to
        # whatever reads the stream (Jev unavailable → route "model").
        "route": prepared.route.name,
        "intent": (prepared.log.get("jev") or {}).get("intent"),
        "jev_error": prepared.log.get("jev_error"),
    }
    yield _event("meta", meta)
    for block in result.output.blocks:
        yield _event("block", block.model_dump())
    yield _event("done", {"ok": True})


def _event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
