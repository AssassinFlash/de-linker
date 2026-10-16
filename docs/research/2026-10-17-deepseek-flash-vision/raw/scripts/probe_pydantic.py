"""Send an image (and a PDF) through Genie's own model construction (pydantic-ai 2.55.0).

Usage: <genie venv python> -I probe_pydantic.py <worktree services/genie/src> <raw dir> image|pdf

The model is linker_genie.agent.build_model() from the worktree, unchanged:
OpenAIChatModel + DeepSeekProvider, deepseek-flash, official https://api.deepseek.com/v1.
An httpx2 request hook records the exact JSON body pydantic-ai puts on the wire;
base64 payloads are replaced by a placeholder and no header is recorded.
"""

import base64
import datetime
import hashlib
import json
import pathlib
import sys
import time

SRC = pathlib.Path(sys.argv[1]).resolve()
RAW = pathlib.Path(sys.argv[2]).resolve()
KIND = sys.argv[3]
sys.path.insert(0, str(SRC))

import linker_genie.agent as genie_agent  # noqa: E402
from pydantic_ai import Agent, BinaryContent  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402

assert pathlib.Path(genie_agent.__file__).resolve().is_relative_to(SRC), genie_agent.__file__

NAMEPLATE_PROMPT = (
    "This photo shows the nameplate (rating label) of a device. Transcribe it exactly as "
    "printed: the brand, the model, the product type, every rating with its label and value, "
    "the serial number and any marks. Do not correct, complete or guess anything; write null "
    "for anything you cannot read. Answer in JSON: {\"brand\": str|null, \"model\": str|null, "
    "\"product_type\": str|null, \"ratings\": [{\"label\": str, \"value\": str}], "
    "\"serial\": str|null, \"marks\": [str]}"
)
PDF_PROMPT = "What does the attached PDF say? Quote its text."

if KIND == "image":
    path, media_type, prompt = RAW / "nameplate-probe.png", "image/png", NAMEPLATE_PROMPT
else:
    path, media_type, prompt = RAW / "datasheet-probe.pdf", "application/pdf", PDF_PROMPT
data = path.read_bytes()
b64 = base64.b64encode(data).decode()
placeholder = f"<base64 of raw/{path.name}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}>"

model = genie_agent.build_model()
wire: list[dict] = []


async def on_request(request) -> None:  # type: ignore[no-untyped-def]
    body = request.content.decode().replace(b64, placeholder)
    wire.append({"method": request.method, "url": str(request.url), "body": json.loads(body)})


async def on_response(response) -> None:  # type: ignore[no-untyped-def]
    wire[-1]["status"] = response.status_code


http = model.client._client  # the httpx2.AsyncClient inside AsyncOpenAI
http.event_hooks = {"request": [on_request], "response": [on_response]}

agent = Agent(
    model,
    instructions="You read photos and files that a customer attached to a question.",
    # Genie's own setting (agent.make_generate): JSON output without fences.
    model_settings={"extra_body": {"response_format": {"type": "json_object"}}} if KIND == "image" else None,
)
started = datetime.datetime.now(datetime.UTC)
t0 = time.monotonic()
record: dict = {
    "library": {"pydantic_ai_slim": "2.55.0", "openai": "3.28.0", "model_class": type(model).__name__,
                "provider_class": type(model._provider).__name__, "model_name": model.model_name},
    "requested_at_utc": started.isoformat(timespec="seconds"),
}
out = RAW / f"probe-{'3-image' if KIND == 'image' else '4-pdf'}-pydantic-ai.json"
try:
    result = agent.run_sync([prompt, BinaryContent(data=data, media_type=media_type)])
    record["wall_seconds"] = round(time.monotonic() - t0, 2)
    record["outcome"] = "ok"
    record["output"] = result.output
    # pydantic-ai 2.x: `usage` is a property holding a RunUsage.
    usage = result.usage() if callable(result.usage) else result.usage
    record["usage"] = {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                       "requests": usage.requests, "details": dict(usage.details)}
except ModelHTTPError as err:
    record["wall_seconds"] = round(time.monotonic() - t0, 2)
    record["outcome"] = "ModelHTTPError"
    record["error"] = {"status_code": err.status_code, "model_name": err.model_name, "body": err.body}
except Exception as err:  # noqa: BLE001 - the record must be written whatever happens
    record["outcome"] = f"{type(err).__name__}: {err}"
finally:
    record["wire"] = wire
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n")
print(record["outcome"], record.get("wall_seconds"), "s", [w.get("status") for w in wire])
