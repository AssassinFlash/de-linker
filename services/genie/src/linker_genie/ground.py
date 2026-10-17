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
(docs/specs/10-knowledge-index.md): a number the answer states from a
document must occur in a cited chunk. A document's numbers reach the answer
only as figures of a retrieved chunk (`{fact:CHUNK_ID.nK}`, `figures.tag`),
and each figure's value is checked against the chunk texts of this turn.
Product facts (`pID.FIELD`) come from the product data, not from documents,
and are not held to the chunk texts. Check 5 forbids bare digits in the model
text either way.

Beside the five, the checks of the understanding layer (#233):

6. A document is a document block whose `ref` names a document of this turn's
   tools; no URL stands in the text, neither written nor through a placeholder.
7. The domain words of AGENTS.md §3 are kept: no article, catalogue, cart or
   basket (Artikel, Katalog, Warenkorb) in the model's text.
8. The route's requirements (route.py): a product word's search shows its cards; a
   sizing turn carries the configurator action and no cards; a product, document,
   pairing, comparison or sizing turn is never the team handoff.

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
from linker_genie.figures import is_code
from linker_genie.hydrate import leftover_placeholders
from linker_genie.route import Route
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    CardsBlock,
    CompareBlock,
    DocumentBlock,
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
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
# AGENTS.md §3: products and product categories — never article, catalogue, cart or
# basket; the German counterparts are Artikel, Katalog and Warenkorb. The prompts
# carry the same list (prompts/*/system.md).
BANNED_WORDS = re.compile(
    r"\b(?:articles?|catalogues?|catalogs?|carts?|baskets?|"
    r"artikel[ns]?|katalog(?:e|en|s)?|warenk(?:o|ö)rb(?:e|en|s)?)\b",
    re.IGNORECASE,
)


# A model code written whole: upper-case letters and digits joined by hyphens or
# slashes, with at least one letter ("CB2-100.3-HV5", "HS3-5K-T2-W/G-PX"). Its
# numeric segments are part of the name, not numbers: "CB2-100.3-HV5" was refused
# as the number "100.3" again and again (trial question 10, 2026-10-17), although
# the prompt asks for model names as plain codes. "3-phase" (lower case) and
# "10-20" (no letter) are not codes and stay caught.
_MODEL_CODE = re.compile(
    r"(?<![\w.])(?=[A-Z0-9.,/-]*[A-Z])[A-Z0-9]+(?:[.,][0-9]+)?"
    r"(?:[-/][A-Z0-9]+(?:[.,][0-9]+)?)+(?![\w])"
)


def _bare_numbers(text: str) -> list[str]:
    """Digit tokens that stand outside alphanumeric model codes.

    A model code keeps its numeric segments: "CB2-100.3-HV5" is a name, written
    plainly (`_MODEL_CODE`, #233; and a whole word that `figures.is_code` reads as
    a name, #257, which also covers codes written in lower case).
    """
    text = _MODEL_CODE.sub(" ", text)
    return [
        token
        for word in text.split()
        if not is_code(word)
        for token in _TOKEN.findall(word)
        if _NUMERIC_TOKEN.fullmatch(token)
    ]


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    failures: tuple[str, ...]

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def check(
    output: TurnOutput, facts: TurnFacts, route: Route | None = None
) -> CheckResult:
    """Run the anchoring checks. Empty failures means the turn is grounded."""
    failures: list[str] = []
    failures.extend(_refs_and_placeholders(output, facts))
    failures.extend(_cards_and_qualified(output, facts))
    failures.extend(_actions(output, facts))
    failures.extend(_handoff_only_when_out_of_scope(output))
    failures.extend(_no_bare_numbers(output, facts))
    failures.extend(_login_required_is_a_login_request(output, facts))
    failures.extend(_documents(output, facts))
    failures.extend(_domain_words(output))
    if route is not None:
        failures.extend(_route(output, facts, route))
    return CheckResult(ok=not failures, failures=tuple(failures))


def _model_texts(output: TurnOutput) -> list[str]:
    texts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            texts.append(block.text)
        elif isinstance(block, HandoffBlock):
            texts.append(block.summary)
        elif isinstance(block, AskBlock):
            texts.extend(block.options)
    return texts


def _documents(output: TurnOutput, facts: TurnFacts) -> list[str]:
    failures: list[str] = []
    for block in output.blocks:
        if isinstance(block, DocumentBlock):
            if block.ref not in facts.documents:
                failures.append(f"document {block.ref!r} is not in this turn's tools")
            if block.label is not None or block.url is not None:
                failures.append("a document block carries only its ref")
    for text in _model_texts(output):
        if _URL.search(PLACEHOLDER.sub("", text)):
            failures.append("a URL stands in the text; use a document block")
        for fact_id in leftover_placeholders(text):
            fact = _fact_known(facts, fact_id)
            if fact_id in facts.documents or (fact and _URL.search(fact.value)):
                failures.append(
                    f"placeholder {fact_id!r} would print a URL; use a document block"
                )
    return failures


def _domain_words(output: TurnOutput) -> list[str]:
    failures: list[str] = []
    for text in _model_texts(output):
        found = BANNED_WORDS.findall(PLACEHOLDER.sub("", text))
        if found:
            failures.append(
                f"banned words {sorted({w.lower() for w in found})!r}: say product, "
                "product category or solution draft"
            )
    return failures


def _route(output: TurnOutput, facts: TurnFacts, route: Route) -> list[str]:
    failures: list[str] = []
    cards = [b for b in output.blocks if isinstance(b, CardsBlock)]
    if route.show_products and facts.qualified_ids:
        shown = {pid for block in cards for pid in block.product_ids}
        if not shown & facts.qualified_ids:
            failures.append(
                "the customer named products: show the search result as cards"
            )
    if route.no_cards and cards:
        failures.append(f"a {route.name} turn shows no product cards")
    if route.action and "size.configurator_url" in facts.facts:
        if not any(
            isinstance(b, ActionBlock) and b.name == route.action for b in output.blocks
        ):
            failures.append(f"a {route.name} turn carries the {route.action} action")
    if route.no_handoff and any(isinstance(b, HandoffBlock) for b in output.blocks):
        failures.append(f"a {route.name} turn is not a question for the team")
    if route.name in ("person", "service") and any(
        isinstance(b, HandoffBlock) for b in output.blocks
    ):
        if any(not isinstance(b, HandoffBlock) for b in output.blocks):
            # The mailbox sentence once, as the handoff block (trial question 18
            # printed it twice: a text block and the handoff block).
            failures.append("a handoff turn is the handoff block alone")
    return failures


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
        if block.name == "open_configurator" and "size.configurator_url" in facts.facts:
            # The service writes this URL from size-hint (hydrate.py); what the
            # model put there is replaced, not checked.
            continue
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
                    if fact is None or fact.source != "search-knowledge":
                        continue
                    if fact.id.endswith(".text") or fact.id in facts.chunk_ids:
                        continue
                    digits = _bare_numbers(fact.value)
                    if digits and not any(
                        digit in cited_chunk_text for digit in digits
                    ):
                        failures.append(
                            f"number in {fact_id!r} does not appear in a cited chunk"
                        )
    return failures
