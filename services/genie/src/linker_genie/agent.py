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

import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linker_genie import attachments, knowledge, page, planning, solution, timing
from linker_genie.abilities import ABILITY_NAMES, Abilities, AbilityError
from linker_genie.conversation import customer_messages, last_customer_message
from linker_genie.embedding import EmbeddingError
from linker_genie.facts import TurnFacts, merge
from linker_genie.failure import note
from linker_genie.language import LANGUAGE_RETRY_PREFIX, turn_language, with_tool_lang
from linker_genie.prefill import stated_size_hint
from linker_genie.route import NAMED_MODEL_RULE
from linker_genie.schema import ASK_FIELDS, TurnOutput, TurnRequest
from linker_genie.tools import MAX_TOOL_CALLS as TOOL_LIMIT
from linker_genie.understand import Prepared

# The per-turn call limit lives with the other shared names (tools.py).
MAX_TOOL_CALLS = TOOL_LIMIT
# pydantic-ai AgentRetries.tools: retries after the first call, then
# UnexpectedModelBehavior ("Tool '…' exceeded max retries count of N",
# tool_manager._check_max_retries). The library default is 1, which is what
# G5-EN exhausted. N=2 is three attempts, the same count as
# abilities.ABILITY_ATTEMPTS (#103, spec 13): a validation error is handed
# back to the model, and a call that still fails is the degraded sentence.
# Dossier 2026-10-19 §1.15 publishes no competitor count; the recovery path
# there is retry, then a failure the customer can see. Output stays 1
# because cycle.run already asks once more after a bad structure.
TOOL_RETRIES = 2
# The route's results go into the prompt as JSON; a search answers with up to six
# cards with their facts (route.SEARCH_LIMIT), and a document search with up to 16
# chunks: 9,500 to 23,400 characters as the model reads them on the 18 questions of
# eval/knowledge (median 14,700; measured 2026-10-17, #257). The ceiling holds a
# document search and a product search together, and only keeps a runaway result
# from crowding the conversation out of the context.
MAX_RESULT_CHARS = 48_000
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
        "device_classes?: [those slugs], "
        "application?: 'home'|'commercial', "
        "phase?: 1|3, pv_kwp?: number>=0, ac_power_min?: number>=0, "
        "kwh_min?: number, kwh_max?: number, "
        "brand?: string, series?: string, future?: ['battery'], text?: string, "
        "with_pairings?: boolean, "
        "extreme?: 'smallest'|'largest'|'cheapest', "
        "lang: 'en'|'de', limit?: int 1..12} — "
        "no other fields exist; phase is the NUMBER 1 or 3. "
        "extreme aggregates the qualified set: smallest and largest take "
        "ac_power_kw when ac_power_min is set and energy when the floor is "
        "kWh; cheapest ranks by a price this account can see and is not "
        "applied when prices are hidden."
    ),
    "linker/get-product": "{product_id: int>=1, lang: 'en'|'de'}",
    "linker/compare-products": "{product_ids: [2..4 ints], lang: 'en'|'de'}",
    "linker/check-compatibility": (
        "{inverter_id: int, battery_id: int} or {product_ids: [2 ints]} — "
        "exactly one of the two forms; inverter_id+battery_id for a known "
        "pair, product_ids to check the two products of a mixed pair."
    ),
    "linker/size-hint": (
        "{} — pass an empty object. The service fills pv_kwp, "
        "annual_load_kwh, phase (1|3), backup "
        "('none'|'needed'|'needed_accessory_ok') and plz (five digits) "
        "from values the customer stated in the conversation, and leaves "
        "out every field they did not state. Do not send those fields "
        "yourself; a guess is dropped."
    ),
    "linker/inquiry-status": "{}",
    "linker/handoff-team": "{summary: string}",
    solution.NAME: solution.INPUT_DOC,
    planning.NAME: planning.INPUT_DOC,
    knowledge.NAME: knowledge.INPUT_DOC,
    page.NAME: page.INPUT_DOC,
}
# Every tool the model may call: the WordPress abilities, and the document search,
# the page read and the saved-solution read this process runs itself (linker_genie.
# knowledge, linker_genie.page, linker_genie.solution). The solution read is one of
# the WordPress abilities but has its own runner, because its figures are tagged in
# this process before the model reads them; it is not a generic ability tool.
TOOL_NAMES = (
    *(name for name in ABILITY_NAMES if name != solution.NAME),
    knowledge.NAME,
    page.NAME,
    solution.NAME,
    planning.NAME,
)
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


@dataclass(frozen=True)
class DeepSeekAccess:
    """The key and the address of the official DeepSeek API, from the environment."""

    key: str
    base_url: str


def deepseek_access() -> DeepSeekAccess:
    """The one place the DeepSeek key and base URL are resolved (review round 1 of
    PR #309): the chat model (`build_model`), the image reads (`app.vision`) and the
    attachment evaluation all take them from here. GENIE_* wins over DEEPSEEK_*; the
    credentials file backfills; the address defaults to the official API."""
    env = _env_with_credentials()
    return DeepSeekAccess(
        key=env.get("GENIE_API_KEY") or env.get("DEEPSEEK_API_KEY") or "",
        base_url=env.get("GENIE_BASE_URL")
        or env.get("DEEPSEEK_BASE_URL")
        or DEFAULT_BASE_URL,
    )


class ToolBudget:
    """Counts ability calls in one turn; the fifth is refused."""

    def __init__(self, limit: int = MAX_TOOL_CALLS, used: int = 0) -> None:
        self.limit = limit
        # The route's own calls (understand.py) count against the same four.
        self.used = used
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
    import httpx2
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.profiles.openai import OpenAIModelProfile
    from pydantic_ai.providers.deepseek import DeepSeekProvider

    from linker_genie.provider_budget import OpenAITransport

    access = deepseek_access()
    return OpenAIChatModel(
        model_name(),
        provider=DeepSeekProvider(
            openai_client=AsyncOpenAI(
                base_url=access.base_url.rstrip("/") + "/v1",
                api_key=access.key,
                # cycle.run already owns the bounded retry; keep budget errors
                # out of SDK connection retries and debit every actual send.
                max_retries=0,
                http_client=httpx2.AsyncClient(transport=OpenAITransport()),
            ),
        ),
        profile=OpenAIModelProfile(
            thinking_enabled_by_default=True,
            supports_forced_tool_choice_with_thinking=False,
            # The official API takes no document (a PDF is refused with 400, and
            # pydantic-ai's nested `file` block is refused before that; research
            # docs/research/2026-10-17-deepseek-flash-vision/ §5): a document handed
            # to the agent by mistake fails here, before any request is paid for.
            # Attachments reach the agent as text (attachments.py, #236).
            openai_chat_supports_document_input=False,
        ),
    )


def make_generate(
    client: Abilities,
    model: Any | None = None,
    prepared: Prepared | None = None,
    search: knowledge.Search | None = None,
    pages: page.Reader | None = None,
    clock: timing.Timing | None = None,
) -> Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]:
    """A `cycle.Generate` that runs the Pydantic AI agent with the ability client.

    With `prepared`, the route's results are already fetched: the model reads them
    from the prompt and may call the tools left in the budget. The facts it returns
    are only its own calls'; the cycle merges them with the route's (cycle.run).
    `search` is the document search (default: the published index, knowledge.SEARCH).
    A route whose document search failed ends the turn here: the error is raised
    and the cycle answers with its fallback, never with an answer that lacks the
    documents it needed (#257, docs/specs/10-knowledge-index.md 失败显式).
    `pages` reads the customer's page (page.py, #234) when the model asks for it.
    `clock` only times each tool call the model makes (timing.py, #336).
    """
    document_search = search or knowledge.SEARCH

    def generate(
        request: TurnRequest, retry_reason: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        from pydantic_ai import Agent, Tool

        if prepared is not None and prepared.knowledge_error:
            raise knowledge.KnowledgeUnavailable(prepared.knowledge_error)
        budget = ToolBudget(used=prepared.calls_made if prepared else 0)
        customer = customer_messages(request)
        # Instructions, tool lang and fact collection follow the answer
        # language. The user prompt still names the page as locale=.
        expected = turn_language(request)
        tools = []
        for name in TOOL_NAMES:
            if name == knowledge.NAME:
                runner = _knowledge_runner(
                    document_search, budget, expected, clock, prepared
                )
            elif name == page.NAME:
                runner = _page_runner(pages, budget, request, clock)
            elif name == solution.NAME:
                runner = _solution_runner(client, budget, request, expected, clock)
            elif name == planning.NAME:
                runner = _planning_runner(budget, request, clock)
            else:
                runner = _ability_runner(
                    client,
                    budget,
                    name,
                    request.user.context,
                    expected,
                    customer,
                    clock,
                    prepared,
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
            instructions=instructions(expected),
            tools=tools,
            model_settings=settings,
            retries={"output": 1, "tools": TOOL_RETRIES},
        )
        try:
            result = agent.run_sync(_user_prompt(request, retry_reason, prepared))
        except Exception as error:
            # The SDK wraps transport failures. Budget refusal must remain an
            # explicit refusal, rather than a generated degraded answer.
            from linker_judges.budget import BudgetError

            cause: BaseException | None = error
            while cause is not None:
                if isinstance(cause, BudgetError):
                    raise cause from None
                cause = cause.__cause__
            raise
        output = result.output
        if not isinstance(output, TurnOutput):
            output = TurnOutput.model_validate(output)
        return output, budget.facts()

    return generate


def _tool_name(ability: str) -> str:
    return ability.replace("/", "_").replace("-", "_")


def _timed(
    clock: timing.Timing | None,
    key: str,
    work: Callable[[dict[str, Any] | None], Any],
) -> Callable[[dict[str, Any] | None], Any]:
    """`work` inside `key`'s phase. A refused call never reaches here (the
    runners guard first), so it is absent from the record, not timed as an
    instant: skipped is not fast (#336, timing.py)."""

    def run(arguments: dict[str, Any] | None = None) -> Any:
        with timing.phase(clock, key):
            return work(arguments)

    return run


def _note_call_failure(
    prepared: Prepared | None, error: BaseException, *, prefix: str
) -> None:
    """Record a model-tool failure next to the route's `call_failures`.

    The runners raise into pydantic-ai. The note keeps the class the catch
    site already knew (#410). Without this line the turn log never sees the
    500, and a later handoff-team can ship the sales sentence.
    """
    if prepared is None:
        return
    failures = prepared.log.get("call_failures")
    if not isinstance(failures, list):
        failures = []
        prepared.log["call_failures"] = failures
    failures.append(note(error, prefix=prefix).dump())


# `search-products` `text` matches title, SKU and model only
# (SearchProducts::text_ok). "hybrid" is not in the ESA or H2-15K titles, so
# the needle drops those products even when phase and AC power already match
# (baseline b03). A model or series code is not one of these words.
_CLASS_TEXT_WORDS = frozenset(
    {
        "hybrid",
        "hybrids",
        "inverter",
        "inverters",
        "wechselrichter",
        "hybrid-wechselrichter",
        "hybridwechselrichter",
        "three-phase",
        "single-phase",
        "3-phase",
        "1-phase",
        "dreiphasig",
        "dreiphasige",
        "dreiphasiger",
        "dreiphasigen",
        "einphasig",
        "einphasige",
        "einphasiger",
        "einphasigen",
    }
)
_SEARCH_NARROWING = frozenset(
    {"phase", "ac_power_min", "kwh_min", "kwh_max", "brand", "series", "pv_kwp"}
)


def _class_text_tokens(text: str) -> list[str]:
    """Words of `text`, keeping a hyphenated token whole."""
    tokens: list[str] = []
    current: list[str] = []
    for char in text.casefold():
        if char.isalnum() or char == "-":
            current.append(char)
            continue
        if current:
            token = "".join(current).strip("-")
            if token:
                tokens.append(token)
            current = []
    if current:
        token = "".join(current).strip("-")
        if token:
            tokens.append(token)
    return tokens


def without_class_text(
    name: str, arguments: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Drop a class-word `text` when a structured filter already narrows the search.

    The copy is new. A code, a series word, or a search that has only `text`
    is unchanged: that needle is the filter.
    """
    if name != "linker/search-products" or not arguments or "text" not in arguments:
        return arguments
    text = arguments.get("text")
    if not isinstance(text, str) or not text.strip():
        return arguments
    if not any(arguments.get(key) not in (None, "") for key in _SEARCH_NARROWING):
        return arguments
    tokens = _class_text_tokens(text)
    if not tokens or any(token not in _CLASS_TEXT_WORDS for token in tokens):
        return arguments
    return {key: value for key, value in arguments.items() if key != "text"}


def _ability_runner(
    client: Abilities,
    budget: ToolBudget,
    name: str,
    user_context: str | None = None,
    locale: str = "en",
    message: str | Sequence[str] = "",
    clock: timing.Timing | None = None,
    prepared: Prepared | None = None,
) -> Callable[[dict[str, Any] | None], Any]:
    def call(arguments: dict[str, Any] | None) -> Any:
        # size-hint ignores `arguments` (#365): the model's object is not a
        # source. pv_kwp, annual_load_kwh, phase, backup and plz reach the
        # tool only from what the customer stated in this conversation (each
        # user message, a later one overriding the same field). The code
        # route sends the same dict.
        sent = (
            stated_size_hint(message)
            if name == "linker/size-hint"
            else without_class_text(name, with_tool_lang(name, arguments, locale))
        )
        try:
            payload, gathered = client.record(name, sent, user_context, locale)
        except AbilityError as error:
            _note_call_failure(prepared, error, prefix=name)
            raise
        budget.parts.append(gathered)
        return payload

    timed = _timed(clock, timing.tool_key(name), call)

    def run(arguments: dict[str, Any] | None = None) -> Any:
        """Call a Linker commerce ability and return its JSON result."""
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        return timed(arguments)

    run.__name__ = _tool_name(name)
    # The docstring is set by make_generate from INPUT_DOCS; setting it here
    # too would only be overwritten.
    return run


def _knowledge_runner(
    search: knowledge.Search,
    budget: ToolBudget,
    locale: str = "en",
    clock: timing.Timing | None = None,
    prepared: Prepared | None = None,
) -> Callable[[dict[str, Any] | None], Any]:
    def call(arguments: dict[str, Any] | None) -> Any:
        try:
            payload, gathered = knowledge.record(
                search, with_tool_lang(knowledge.NAME, arguments, locale), locale
            )
        except (EmbeddingError, knowledge.KnowledgeUnavailable) as error:
            _note_call_failure(prepared, error, prefix=knowledge.NAME)
            raise
        budget.parts.append(gathered)
        return knowledge.model_view(payload)

    timed = _timed(clock, timing.tool_key(knowledge.NAME), call)

    def run(arguments: dict[str, Any] | None = None) -> Any:
        """Search the hosted documents and return the matching chunks."""
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        return timed(arguments)

    run.__name__ = _tool_name(knowledge.NAME)
    return run


def _page_runner(
    pages: page.Reader | None,
    budget: ToolBudget,
    request: TurnRequest,
    clock: timing.Timing | None = None,
) -> Callable[[dict[str, Any] | None], Any]:
    def call(arguments: dict[str, Any] | None) -> Any:
        del arguments
        assert pages is not None  # run guards it; a refused read never gets here
        question = last_customer_message(request)
        try:
            payload, gathered = page.record(
                pages, request.page_context, question, request.user.logged_in
            )
        except page.PageUnavailable as error:
            return {"error": f"the page could not be read: {error}"}
        budget.parts.append(gathered)
        return page.model_view(payload)

    timed = _timed(clock, timing.tool_key(page.NAME), call)

    def run(arguments: dict[str, Any] | None = None) -> Any:
        """Read the page the customer is on and return what it says."""
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        if pages is None:
            return {"error": "the page cannot be read in this turn"}
        return timed(arguments)

    run.__name__ = _tool_name(page.NAME)
    return run


def _solution_runner(
    client: Abilities,
    budget: ToolBudget,
    request: TurnRequest,
    locale: str = "en",
    clock: timing.Timing | None = None,
) -> Callable[[dict[str, Any] | None], Any]:
    """The saved solution the page carries (#496); the model passes no argument.

    The id is the page context's, never the model's: a solution is the one the
    customer opened Genie on, and the ability refuses another customer's id in
    any case.
    """

    def call(arguments: dict[str, Any] | None) -> Any:
        del arguments
        solution_id = request.page_context.solution_id or 0
        if not solution_id:
            return {"error": "no saved solution on this page"}
        payload, gathered = solution.record(
            client, solution_id, request.user.context, locale
        )
        budget.parts.append(gathered)
        return solution.model_view(payload)

    timed = _timed(clock, timing.tool_key(solution.NAME), call)

    def run(arguments: dict[str, Any] | None = None) -> Any:
        """Read the saved solution the customer's page carries and return its figures."""
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        return timed(arguments)

    run.__name__ = _tool_name(solution.NAME)
    return run


def _planning_runner(
    budget: ToolBudget,
    request: TurnRequest,
    clock: timing.Timing | None = None,
) -> Callable[[dict[str, Any] | None], Any]:
    def call(arguments: dict[str, Any] | None) -> Any:
        del arguments
        payload, gathered = planning.record(
            request.planning_context, request.page_context
        )
        budget.parts.append(gathered)
        return planning.model_view(payload)

    timed = _timed(clock, timing.tool_key(planning.NAME), call)

    def run(arguments: dict[str, Any] | None = None) -> Any:
        if not budget.allow():
            return {"error": f"tool budget {MAX_TOOL_CALLS} exhausted"}
        return timed(arguments)

    run.__name__ = _tool_name(planning.NAME)
    return run


def _page_lines(request: TurnRequest) -> list[str]:
    """The page the customer is on, as the prompt names it (#234)."""
    context = request.page_context
    lines = [f"page={context.type}"]
    if context.planning_project_id:
        lines.append(
            "This page selects a saved planning project revision and optional result(s). "
            "Use linker_read_planning_project for its inputs and figures; only that "
            "server-verified result establishes readable data. " + planning.RULE
        )
    if context.title:
        lines.append(f"page_title={context.title}")
    path = page.page_path(context.url)
    if path:
        lines.append(f"page_url={path}")
    lines.append(
        "The customer is on this page: 'this page', 'here', 'this one' and 'it' "
        "without another subject mean this page or its product. To know what the "
        "page says, use the read-page result (or call linker_read_page); the page "
        "rule is in the reminder below."
    )
    if context.solution_id:
        lines.append(
            f"The page carries the customer's own saved solution {context.solution_id}: "
            "'my solution', 'the design', 'the report' and its figures mean that "
            "solution. To know its figures, use the read-solution result (or call "
            "linker_read_solution); the solution rule is in the reminder below."
        )
    return lines


def _result_view(
    item: dict[str, Any], *, compact_warranty: bool = False
) -> dict[str, Any]:
    """A route result as the model reads it, like the model's own call of that tool."""
    result = item.get("result")
    if not isinstance(result, dict):
        return item
    if item.get("name") == knowledge.NAME:
        return {
            **item,
            "result": knowledge.model_view(result, compact_warranty=compact_warranty),
        }
    if item.get("name") == page.NAME:
        return {**item, "result": page.model_view(result)}
    if item.get("name") == solution.NAME:
        return {**item, "result": solution.model_view(result)}
    if item.get("name") == planning.NAME:
        return {**item, "result": planning.model_view(result)}
    return item


def _route_results(items: list[dict[str, Any]]) -> tuple[str, bool]:
    """Keep overlong warranty results complete instead of cutting JSON mid-hit."""
    view = [_result_view(item) for item in items]
    encoded = json.dumps(view, ensure_ascii=False)
    if len(encoded) <= MAX_RESULT_CHARS:
        return encoded, False
    has_warranty = any(
        item.get("name") == knowledge.NAME
        and isinstance(item.get("result"), dict)
        and isinstance(item["result"].get("hits"), list)
        and any(
            isinstance(hit, dict) and hit.get("warranty_terms") is True
            for hit in item["result"].get("hits", [])
        )
        for item in items
    )
    if not has_warranty:
        return encoded[:MAX_RESULT_CHARS], False
    view = [_result_view(item, compact_warranty=True) for item in items]
    encoded = json.dumps(view, ensure_ascii=False)
    while len(encoded) > MAX_RESULT_CHARS:
        result = next(
            (
                item["result"]
                for item in reversed(view)
                if item.get("name") == knowledge.NAME
                and isinstance(item.get("result"), dict)
                and item["result"].get("hits")
            ),
            None,
        )
        if result is None:
            return json.dumps(
                [{"error": "Prepared results exceed the model context; search again."}]
            ), True
        result["hits"].pop()
        result["omitted_from_model_view"] = result.get("omitted_from_model_view", 0) + 1
        encoded = json.dumps(view, ensure_ascii=False)
    return encoded, True


def _user_prompt(
    request: TurnRequest, retry_reason: str | None, prepared: Prepared | None = None
) -> str:
    lines = [
        f"locale={request.locale}",
        *_page_lines(request),
        f"logged_in={request.user.logged_in}",
        f"partner={request.user.partner}",
    ]
    if request.page_context.product_id:
        lines.append(f"product_id={request.page_context.product_id}")
    if request.page_context.draft_ids:
        lines.append(
            "draft_ids=" + ",".join(str(i) for i in request.page_context.draft_ids)
        )
    if request.page_context.solution_id:
        lines.append(f"solution_id={request.page_context.solution_id}")
    if prepared is not None and prepared.route.hint:
        lines.append("Service routing: " + prepared.route.hint)
    if prepared is not None and prepared.results:
        # A document search reads as the model's own call would: tagged text, no
        # URL, no figure table (knowledge.model_view).
        results, compact_warranty = _route_results(prepared.results)
        if compact_warranty:
            lines.append(
                "For compact warranty hits, warranty_figures maps each short figure "
                "ID (such as n1) to its original value. Use it to select the matching "
                "policy row; copy the chosen warranty_answers value unchanged, "
                "including its fact placeholders. If passages were omitted, search again."
            )
        lines.append(
            "Tool results the service already fetched for this turn (use them; "
            "do not call the same tool again with the same input): " + results
        )
    if prepared is not None and prepared.attachments:
        # The customer's files as the service read them (#236): the text of each, the
        # long ones cut to the passages nearest the question (attachments.model_view).
        question = last_customer_message(request)
        files = json.dumps(
            [attachments.model_view(item, question) for item in prepared.attachments],
            ensure_ascii=False,
        )
        lines.append(
            "Files the customer attached in this conversation, as the service read "
            "them. " + attachments.RULE + " Files: " + files[:MAX_RESULT_CHARS]
        )
    if prepared is not None and prepared.facts.documents:
        # The refs a document block may name, spelled out: the model guessed
        # `p4106.document.1` where get-product had listed one document (trial
        # question 10, 2026-10-17), and grounding refused the turn twice.
        lines.append(
            "Document refs you may link, and no others: "
            + "; ".join(
                f"{ref} = {document.title}"
                for ref, document in prepared.facts.documents.items()
            )
        )
    if retry_reason:
        # A language miss is its own re-ask (#374). Grounding failures keep the
        # older line. A turn that failed both starts with the language prefix,
        # and the grounding reasons follow in the same sentence.
        if retry_reason.startswith(LANGUAGE_RETRY_PREFIX):
            lines.append(
                "The previous answer used the wrong language. "
                + retry_reason
                + " Rewrite the whole answer in that language. The page, the "
                "document chunks and the tool results may be in the other "
                "language; they do not choose the answer."
            )
        else:
            lines.append("The previous answer failed grounding: " + retry_reason)
        lines.append("Produce a new structured turn that passes the checks.")
    for message in request.messages:
        lines.append(f"{message.role}: {message.content}")
    lines.append(
        "Reminder: answer as strict TurnOutput JSON. No number in text in "
        "any form — no digits (10), no spelled-out words (ten, forty-eight, "
        "zehn, achtundvierzig), no model name spelled letter by letter; "
        "the terms single-phase, three-phase, einphasig and dreiphasig are "
        "words, not numbers, and are written as such; "
        "a code word or identifier from an attached file (for example "
        "ZEPHYR-C334) is not a number in text and is written literally, as "
        "the file writes it; a numeric value from that file still goes in "
        "{fact:attN.nK}; "
        "numbers go in {fact:PRODUCTID.FIELD} placeholders naming exactly "
        "the fact keys the tools returned (device_class, application, "
        "phase, ac_power_kw, pv_input_kw, usable_kwh, nominal_kwh, "
        "kwh_range, compat.verdict, compat.verdict.BATTERYID, "
        "compat.condition.N, handoff.sentence, inquiry.login); never a "
        "subfield like kwh_range.min. A range "
        "placeholder renders the whole range. A figure from a document chunk "
        "goes in {fact:CHUNK_ID.nK}, the [nK=…] tag shown in that chunk's text; "
        "put the chunk IDs you rely on in refs, the service links their "
        "documents. Or leave the number unsaid. A price is never written in "
        "text, not even as a placeholder: show the product as a card, whose "
        "price line the service fills for this account; with partner=True say "
        "the card shows the net price, otherwise say once that approved partner "
        "accounts see net prices. "
        + page.RULE
        + " "
        + solution.RULE
        + " "
        + planning.RULE
        + " "
        "A document (a search-knowledge chunk ID, compat.document.N, "
        "compat.document.BATTERYID.N, or pPRODUCTID.document.N for the documents "
        "get-product listed this turn — such a ref exists only after get-product "
        "returned it) is never a placeholder and never a URL in "
        'the text: add a block {"type":"document","ref":"<that ID>"}. '
        "Cite only a ref that appears in this turn's tool results. "
        "A document, a chunk and a product the tools did not return are not cited. "
        "When check-compatibility returned not_released, the text is only "
        "{fact:compat.condition.N} for each condition, in order (the first "
        "condition is compat.condition.0; use no index the check did not "
        "return), and document "
        "blocks for that check's compat.document.N. No cards and no other "
        "sentence. When search-products for inverters, with the battery model "
        "as text, returned no qualified product, the next call is "
        "search-products with with_pairings true and text set to the one "
        "family word in the datasheet title. Do not call search-knowledge "
        "instead. "
        "Never write article, catalogue, cart or basket (Artikel, Katalog, "
        "Warenkorb): say product, product category, solution draft. "
        "Every ID of a cards block must appear in the text block's refs. "
        "Out-of-scope turns: call handoff-team, then one handoff block "
        "summarized as {fact:handoff.sentence}. The service fills that "
        "placeholder with the mailbox sentence in the answer language. "
        "A guest inquiry (inquiry-status returned login_required, "
        "logged_in=false) is not out of scope: do not call handoff-team; "
        "answer with exactly one text block whose text is exactly "
        "{fact:inquiry.login}, and nothing else. "
        "When a released pairing condition names a partner model code, write "
        "that code in the text as the condition writes it. Cards do not "
        "replace the code. "
        + NAMED_MODEL_RULE
        # TALK, PROMISE, REPLY_PROMISE and PARTNER in template.py own the
        # customer sentences this reminder repeats. The system prompts and
        # route._SHAPE_HINT repeat them too; change the sentence there first.
        + " Every answer needs one clickable next step. Cards, a compare "
        "block, a document, an action, an ask, or the handoff block already "
        "count. A short clarification or plain text with none of those blocks "
        "asks which product category, field application, options home and "
        "commercial (German: Wohngebäude and Gewerbe). "
        "A greeting or an identity question says you are Linker's AI "
        "assistant, names products, compatibility, documents and sizing, and "
        "asks which product category, field application, options home and "
        "commercial (German: Wohngebäude and Gewerbe). "
        "What happens after an inquiry is sent: the team replies within one "
        "working day (German: das Linker-Team antwortet innerhalb eines "
        "Werktags), with view_inquiry and empty args, and without a handoff. "
        "Partner net prices with no product named: approved partner accounts "
        'see net prices. A guest sees "Net price after partner sign-in" on '
        'the product card. An account under review sees "Account under '
        'review. Prices after approval." No price number, and one '
        "application ask. "
        "A company question is the handoff block only; the service adds the "
        "contact card and the one-working-day reply. "
        "Ask at most one "
        f"question and only with field in {'|'.join(ASK_FIELDS)}."
    )
    return "\n".join(lines)
