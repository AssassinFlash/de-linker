"""Five anchoring checks on a structured turn (docs/specs/13-genie.md).

These run after Pydantic accepts the shape and before hydration is shown.
They do not rewrite the model's text. A failure is a reason to retry once,
then fall back to the deterministic template.

The five checks, matching the ticket and old-repo-006 §2:

1. Every `{fact:ID}` and every `refs` id is in this turn's tool results, and
   a fact placeholder can be rendered (has a value).
2. Card / compare product IDs ⊆ this turn's tool product IDs; cards ⊆ text
   refs when a text block names products; recommended ⊆ search-products
   qualified when that tool ran.
3. Action names are on the allow-list (enforced by the schema) and arguments
   only use IDs from this turn's tools.
4. Out-of-scope company/service/logistics answers are only a handoff block
   (no product cards or actions beside it). The model chooses handoff via
   the schema; this check catches a mixed turn.
5. Bare numbers must not appear in model text (they belong in `{fact:ID}`).
   Digit runs inside a placeholder do not count.

Ask's wording "数字出现在被引块" is the knowledge-index citation rule
(docs/specs/10-knowledge-index.md): a number the answer states must occur in
a cited chunk. When the turn cites chunks, filled numbers are checked
against those chunk texts. When it does not cite chunks, check 5 still
forbids bare digits in the model text.

Registered reading of guarantee 2: "推荐 ⊆ search-products 的 qualified"
means qualified by this turn's tool results. That is search-products'
`qualified` list, plus the batteries its own `pairings` released (verdict
`released` / `released_with_accessory`) — the tool cleared those pairs, the
same rank as qualification. A product-page or compare turn whose cards come
from get-product / compare-products has no qualified set — those cards are
the subject of the answer, not recommendations, and they stay gated by
"product IDs ⊆ this turn's tool results". Card IDs are always required to
be cited in the text refs; that half of the guarantee is unconditional.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from linker_genie.facts import Fact, TurnFacts
from linker_genie.hydrate import leftover_placeholders
from linker_genie.schema import (
    ActionBlock,
    CardsBlock,
    CompareBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)

BARE_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
PLACEHOLDER = re.compile(r"\{fact:[^}]+\}")
# A token of letters+digits (GW10K, H2, ETA-G20) is a model code, not a
# number; a pure numeric token (48, 5.0, 700) is one.
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:[.,][0-9]+)?")
_NUMERIC_TOKEN = re.compile(r"\d+(?:[.,]\d+)?")


def _bare_numbers(text: str) -> list[str]:
    """Digit tokens that stand outside alphanumeric model codes."""
    return [token for token in _TOKEN.findall(text) if _NUMERIC_TOKEN.fullmatch(token)]


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    failures: tuple[str, ...]

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def check(output: TurnOutput, facts: TurnFacts) -> CheckResult:
    """Run the anchoring checks. Empty failures means the turn is grounded."""
    failures: list[str] = []
    failures.extend(_refs_and_placeholders(output, facts))
    failures.extend(_cards_and_qualified(output, facts))
    failures.extend(_actions(output, facts))
    failures.extend(_handoff_only_when_out_of_scope(output))
    failures.extend(_no_bare_numbers(output, facts))
    failures.extend(_login_required_is_a_login_request(output, facts))
    return CheckResult(ok=not failures, failures=tuple(failures))


def _refs_and_placeholders(output: TurnOutput, facts: TurnFacts) -> list[str]:
    known = facts.ids()
    failures: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            for fact_id in leftover_placeholders(block.text):
                if _fact_known(facts, fact_id) is None:
                    failures.append(
                        f"placeholder {fact_id!r} is not in this turn's tools"
                    )
            for ref in block.refs:
                if ref not in known:
                    failures.append(f"ref {ref!r} is not in this turn's tools")
        elif isinstance(block, HandoffBlock):
            # The handoff summary hydrates too (the team mailbox sentence is a
            # fact of the handoff-team tool), so its placeholder is checked.
            for fact_id in leftover_placeholders(block.summary):
                if _fact_known(facts, fact_id) is None:
                    failures.append(
                        f"placeholder {fact_id!r} is not in this turn's tools"
                    )
    return failures


def _cards_and_qualified(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    text_product_refs: set[int] = set()
    for block in output.blocks:
        if isinstance(block, TextBlock):
            for ref in block.refs:
                if ref.isdigit():
                    text_product_refs.add(int(ref))
                elif ref.startswith("p") and ref[1:].split(".", 1)[0].isdigit():
                    text_product_refs.add(int(ref[1:].split(".", 1)[0]))
    for block in output.blocks:
        if isinstance(block, CardsBlock | CompareBlock):
            for product_id in block.product_ids:
                if product_id not in facts.product_ids:
                    failures.append(
                        f"product {product_id} is not in this turn's tool results"
                    )
                if facts.qualified_ids and product_id not in facts.qualified_ids:
                    failures.append(
                        f"product {product_id} is not in search-products qualified"
                    )
            if isinstance(block, CardsBlock):
                extra = set(block.product_ids) - text_product_refs
                for product_id in extra:
                    failures.append(f"card {product_id} is not cited in the text refs")
    return failures


def _actions(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    fact_values = {fact.value for fact in facts.facts.values()}
    for block in output.blocks:
        if not isinstance(block, ActionBlock):
            continue
        args = block.args
        product_id = args.get("product_id")
        if product_id is not None and product_id not in facts.product_ids:
            failures.append(f"action {block.name} product_id is not from this turn")
        product_ids = args.get("product_ids")
        if isinstance(product_ids, list):
            for item in product_ids:
                if item not in facts.product_ids:
                    failures.append(f"action {block.name} product_ids contains {item}")
        # An action's URL is only allowed when a tool of this turn returned
        # it (size-hint's configurator_url). A URL the model invented — or a
        # view_inquiry URL, which no tool returns — is refused here; the
        # shell links such actions to the account page itself.
        url = args.get("url")
        if isinstance(url, str) and url and url not in fact_values:
            failures.append(f"action {block.name} url is not from this turn's tools")
    return failures


def _login_required_is_a_login_request(
    output: TurnOutput, facts: TurnFacts
) -> list[str]:
    """R7 unsigned-out: a guest inquiry fact may only ship the login sentence.

    The fact is recorded by `facts._from_inquiry` when inquiry-status answers
    401. The model has answered that turn with the team mailbox sentence
    (PR #96, German "Wo steht meine Proforma?"); grounding refuses that shape
    so the cycle falls back to `template.login_required` instead of hydrating
    the mailbox sentence.
    """
    if "inquiry.login_required" not in facts.facts:
        return []
    from linker_genie.template import LOGIN_REQUIRED

    expected = LOGIN_REQUIRED[output.language]
    if (
        len(output.blocks) == 1
        and isinstance(output.blocks[0], TextBlock)
        and output.blocks[0].text == expected
        and not output.blocks[0].refs
    ):
        return []
    return [
        "a guest inquiry turn must be the login request and nothing else "
        "(no team mailbox sentence, no inquiry data)"
    ]


def _handoff_only_when_out_of_scope(output: TurnOutput) -> list[str]:
    handoffs = [block for block in output.blocks if isinstance(block, HandoffBlock)]
    others = [block for block in output.blocks if not isinstance(block, HandoffBlock)]
    if handoffs and any(
        isinstance(block, CardsBlock | CompareBlock | ActionBlock) for block in others
    ):
        return ["a handoff turn may not also recommend products or actions"]
    return []


def _fact_known(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' (model shorthand)."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def _no_bare_numbers(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    cited_chunk_text = " ".join(
        fact.value
        for fact in facts.facts.values()
        if fact.source == "search-knowledge" and fact.id.endswith(".text")
    )
    for block in output.blocks:
        if isinstance(block, TextBlock):
            texts = [block.text]
        elif isinstance(block, HandoffBlock):
            texts = [block.summary]
        else:
            continue
        for text in texts:
            stripped = PLACEHOLDER.sub("", text)
            numbers = _bare_numbers(stripped)
            if numbers:
                failures.append(f"model text contains numbers {numbers!r}")
                continue
            if cited_chunk_text:
                for fact_id in leftover_placeholders(text):
                    fact = facts.facts.get(fact_id)
                    if fact is None:
                        fact = _fact_known(facts, fact_id)
                    if fact is None:
                        continue
                    digits = _bare_numbers(fact.value)
                    if digits and not any(
                        digit in cited_chunk_text for digit in digits
                    ):
                        failures.append(
                            f"number in {fact_id!r} does not appear in a cited chunk"
                        )
    return failures
