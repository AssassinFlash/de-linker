"""HTTP entry point: `uvicorn linker_genie.app:app`.

POST /assistant/turn and POST /turn (alias) stream one grounded turn as SSE.
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

from linker_genie.abilities import AbilityClient
from linker_genie.agent import make_generate, model_name, provider_name
from linker_genie.cycle import TurnResult, run
from linker_genie.log import TurnLog
from linker_genie.schema import TurnRequest, VoteRequest

app = FastAPI(title="Genie - Linker's AI assistant")

_log: TurnLog | None = None
_client: AbilityClient | None = None


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
        # No token is sent, ever: see linker_genie.abilities. A token that
        # carries WordPress rights must not be configured until #16's
        # user-context passthrough exists (leftovers of ticket 13).
        _client = AbilityClient(os.environ.get("GENIE_WP_URL", "http://127.0.0.1"))
    return _client


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}


@app.post("/assistant/turn")
@app.post("/turn")
def assistant_turn(body: TurnRequest, request: Request) -> StreamingResponse:
    """One conversation turn, grounded and hydrated, as SSE."""
    generate = getattr(request.app.state, "generate", None) or make_generate(
        ability_client()
    )
    try:
        result = run(body, generate)
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
        )
        raise
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
    )
    return StreamingResponse(
        _sse(result, turn_id),
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


def _sse(result: TurnResult, turn_id: int) -> Iterator[str]:
    meta = {
        "turn_id": turn_id,
        "grounded": result.grounded,
        "fallback": result.fallback,
        "attempts": result.attempts,
        "failures": list(result.failures),
        "language": result.output.language,
    }
    yield _event("meta", meta)
    for block in result.output.blocks:
        yield _event("block", block.model_dump())
    yield _event("done", {"ok": True})


def _event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
