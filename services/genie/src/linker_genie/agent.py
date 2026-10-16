"""Pydantic AI agent: abilities as tools, strict TurnOutput, at most four tools.

The chat model is deepseek-flash on the official DeepSeek API
(https://api.deepseek.com; DEEPSEEK_BASE_URL or GENIE_BASE_URL may point the
client elsewhere) — owner ruling 2026-10-11, and the only chat model Genie
has: there is no provider switch. The earlier Anthropic option
(claude-haiku-4-5 through the aihubmix OpenAI-compatible endpoint,
docs/acceptance/2026-10-10/13/panel-results.md) was withdrawn by the same
ruling; the aihubmix key keeps serving only the Jev review cascade and the
gemini-embedding-2 index (tickets 33/10), not Genie conversation. The key
comes from the environment (DEEPSEEK_API_KEY, GENIE_API_KEY to override),
backfilled from ~/.config/terravolt-builder/deepseek.env. Nothing here
writes a secret.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from linker_genie.abilities import ABILITY_NAMES, AbilityClient
from linker_genie.facts import TurnFacts, merge
from linker_genie.schema import ASK_FIELDS, TurnOutput, TurnRequest

MAX_TOOL_CALLS = 4
# The input objects the abilities accept (docs/specs/13-genie.md §A). The REST
# introspection of an ability is permission-protected, so the shapes live here,
# next to the only consumer. The source of truth is the `input_schema` each
# ability class declares in plugins/linker-commerce/includes/Abilities/ (the
# device-class enum: Products/SelectionFacts.php DEVICE_CLASSES; the
# check-compatibility input: Abilities/CheckCompatibility.php);
# tests/test_input_docs.py locks this table against those PHP sources.
INPUT_DOCS: dict[str, str] = {
    "linker/search-products": (
        "{device_class?: 'inverters'|'home-storage'|'battery-systems'|"
        "'all-in-one-systems'|'ems-monitoring'|'ev-chargers'|'accessories', "
        "application?: 'home'|'commercial', "
        "phase?: 1|3, pv_kwp?: number>=0, kwh_min?: number, kwh_max?: number, "
        "brand?: string, series?: string, future?: ['battery'], text?: string, "
        "with_pairings?: boolean, lang: 'en'|'de', limit?: int 1..12} — "
        "no other fields exist; phase is the NUMBER 1 or 3."
    ),
    "linker/get-product": "{product_id: int>=1, lang: 'en'|'de'}",
    "linker/compare-products": "{product_ids: [2..4 ints], lang: 'en'|'de'}",
    "linker/check-compatibility": (
        "{inverter_id: int, battery_id: int} or {product_ids: [2 ints]} — "
        "exactly one of the two forms; inverter_id+battery_id for a known "
        "pair, product_ids to check the two products of a mixed pair."
    ),
    "linker/size-hint": (
        "{pv_kwp?: number, annual_load_kwh?: number, phase?: 1|3, "
        "backup?: 'none'|'needed'|'needed_accessory_ok', plz?: string} — "
        "no lang field"
    ),
    "linker/inquiry-status": "{}",
    "linker/handoff-team": "{summary: string}",
    "linker/search-knowledge": "{query: string, lang: 'en'|'de', product_ids?: [int]}",
}
PROMPTS = Path(__file__).resolve().parents[2] / "prompts"
# Owner ruling 2026-10-11: the one chat model, on the official DeepSeek API.
CHAT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
# docs/specs/33-judge-bakeoff.md: the key lives here and never enters the
# repository — backfilled into the environment on use.
CREDENTIALS_FILE = Path("~/.config/terravolt-builder/deepseek.env").expanduser()


def _env_with_credentials() -> dict[str, str]:
    """The environment, backfilled from the DeepSeek credentials file."""
    values = dict(os.environ)
    if CREDENTIALS_FILE.exists():
        for line in CREDENTIALS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                name = name.strip().removeprefix("export ").strip()
                values.setdefault(name, value.strip().strip("'\""))
    return values


class ToolBudget:
    """Counts ability calls in one turn; the fifth is refused."""

    def __init__(self, limit: int = MAX_TOOL_CALLS) -> None:
        self.limit = limit
        self.used = 0
        self.parts: list[TurnFacts] = []

    def allow(self) -> bool:
        if self.used >= self.limit:
            return False
        self.used += 1
        return True

    def facts(self) -> TurnFacts:
        return merge(self.parts)


def instructions(locale: str) -> str:
    language = "de" if locale.startswith("de") else "en"
    return (PROMPTS / language / "system.md").read_text(encoding="utf-8")


def provider_name() -> str:
    # A constant, not an environment read: owner ruling 2026-10-11 deleted the
    # GENIE_PROVIDER switch together with the Anthropic option, so a stale
    # variable in a serving environment cannot bring that option back. The
    # value lives in code so it survives any restart (review 2026-10-10,
    # must-fix 5) and names the provider the turn log records.
    return CHAT_PROVIDER


def model_name() -> str:
    return os.environ.get("GENIE_MODEL", DEFAULT_MODEL)


def build_model() -> Any:
    """deepseek-flash on the official DeepSeek API.

    Imported lazily so unit tests need no key. DeepSeekProvider (not the
    generic OpenAI one) is what knows this endpoint's behavior — the
    `reasoning_content` thinking field and its send-back during tool loops.
    The provider pins its own base_url, so the overridable one is carried by
    the client it wraps (GENIE_BASE_URL / DEEPSEEK_BASE_URL > the official
    https://api.deepseek.com).

    The profile states what the endpoint measures (2026-10-11, see
    docs/acceptance/2026-10-11/13/deepseek-flash/): deepseek-flash
    (DeepSeek-V4.1-Flash)
    always thinks — its effort levels are low/high/max with no "none" — and
    answers any forced tool_choice with 400 "Thinking mode does not support
    this tool_choice". pydantic-ai's name table only knows the older
    `deepseek-v4-*` SKUs, so the two facts are declared here: with thinking
    always on and forcing unavailable while thinking, pydantic-ai resolves
    every request (the output tool would force `required`, since TurnOutput
    leaves no direct text output) down to `auto` itself.
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.deepseek import DeepSeekProvider

    env = _env_with_credentials()
    key = env.get("GENIE_API_KEY") or env.get("DEEPSEEK_API_KEY") or ""
    base = env.get("GENIE_BASE_URL") or env.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    return OpenAIChatModel(
        model_name(),
        provider=DeepSeekProvider(
            openai_client=AsyncOpenAI(base_url=base.rstrip("/") + "/v1", api_key=key),
        ),
        profile={
            "thinking_enabled_by_default": True,
            "supports_forced_tool_choice_with_thinking": False,
        },
    )


def make_generate(
    client: AbilityClient,
    model: Any | None = None,
) -> Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]:
    """A `cycle.Generate` that runs the Pydantic AI agent with the ability client."""

    def generate(
        request: TurnRequest, retry_reason: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        from pydantic_ai import Agent, Tool

        budget = ToolBudget()
        tools = []
        for name in ABILITY_NAMES:
            runner = _ability_runner(
                client, budget, name, request.user.context, request.locale
            )
            doc = INPUT_DOCS.get(name)
            runner.__doc__ = f"Call the WordPress ability {name}." + (
                f" Input object: {doc}" if doc else ""
            )
            tools.append(Tool(runner, name=_tool_name(name)))
        settings: Any = {
            # Chat models answer with ```json fences unless the API is told
            # to emit raw JSON (measured 2026-10-10 on aihubmix; the fence
            # broke strict parsing and cost the turn). DeepSeek's official
            # endpoint honors the same response_format — see
            # docs/acceptance/2026-10-11/13/ for the direct-connection checks.
            "extra_body": {"response_format": {"type": "json_object"}},
        }
        chosen_model: Any = model or build_model()
        agent: Agent[None, TurnOutput] = Agent(
            chosen_model,
            output_type=TurnOutput,
            instructions=instructions(request.locale),
            tools=tools,
            model_settings=settings,
            retries={"output": 1, "tools": 1},
        )
        result = agent.run_sync(_user_prompt(request, retry_reason))
        output = result.output
        if not isinstance(output, TurnOutput):
            output = TurnOutput.model_validate(output)
        return output, budget.facts()

    return generate


def _tool_name(ability: str) -> str:
    return ability.replace("/", "_").replace("-", "_")


def _ability_runner(
    client: AbilityClient,
    budget: ToolBudget,
    name: str,
    user_context: str | None = None,
    locale: str = "en",
) -> Callable[[dict[str, Any] | None], Any]:
    def run(arguments: dict[str, Any] | None = None) -> Any:
        """Call a Linker commerce ability and return its JSON result."""
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        payload, gathered = client.record(name, arguments, user_context, locale)
        budget.parts.append(gathered)
        return payload

    run.__name__ = _tool_name(name)
    # The docstring is set by make_generate from INPUT_DOCS; setting it here
    # too would only be overwritten.
    return run


def _user_prompt(request: TurnRequest, retry_reason: str | None) -> str:
    lines = [
        f"locale={request.locale}",
        f"page={request.page_context.type}",
        f"logged_in={request.user.logged_in}",
    ]
    if request.page_context.product_id:
        lines.append(f"product_id={request.page_context.product_id}")
    if request.page_context.draft_ids:
        lines.append(
            "draft_ids=" + ",".join(str(i) for i in request.page_context.draft_ids)
        )
    if retry_reason:
        lines.append("The previous answer failed grounding: " + retry_reason)
        lines.append("Produce a new structured turn that passes the checks.")
    for message in request.messages:
        lines.append(f"{message.role}: {message.content}")
    lines.append(
        "Reminder: answer as strict TurnOutput JSON. No number in text in "
        "any form — no digits (10), no spelled-out words (ten, forty-eight, "
        "zehn, achtundvierzig), no model name spelled letter by letter; "
        "numbers go in {fact:PRODUCTID.FIELD} placeholders naming exactly "
        "the fact keys the tools returned (device_class, application, "
        "phase, ac_power_kw, pv_input_kw, usable_kwh, nominal_kwh, "
        "kwh_range, pID.price, compat.verdict, compat.verdict.BATTERYID, "
        "compat.condition.N, compat.document.N, handoff.sentence_en, "
        "handoff.sentence_de); never a subfield like kwh_range.min. A range "
        "placeholder renders the whole range. Or leave the number unsaid. "
        "Every ID of a cards block must appear in the text block's refs. "
        "Out-of-scope turns: call handoff-team, then one handoff block "
        "summarized as {fact:handoff.sentence_en} or "
        "{fact:handoff.sentence_de}. A guest inquiry (inquiry-status "
        "returned login_required, logged_in=false) is not out of scope: "
        "do not call handoff-team; answer with exactly one text block, "
        "'Please log in to your account to view this inquiry.' in English or "
        "'Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.' "
        "in German, and nothing else. Ask at most one question and only "
        f"with field in {'|'.join(ASK_FIELDS)}."
    )
    return "\n".join(lines)
