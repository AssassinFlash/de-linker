"""Strict structured output of one Genie turn (docs/specs/13-genie.md).

The model may only emit IDs and `{fact:ID}` placeholders. Numbers are filled
in after the run (hydration). Illegal structure is refused by Pydantic.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

Locale = Literal["en", "de"]
# The eight kinds of page Genie tells apart (#234, docs/specs/13-genie.md 目标 3), and
# `other` for the rest (contact, legal, forms, the tools). The shell decides the type
# (plugins/linker-tools/includes/Genie/PageContext.php).
PageType = Literal[
    "home",
    "product",
    "category",
    "solution",
    "blog",
    "faq",
    "draft",
    "account",
    "other",
]
AskField = Literal[
    "phase",
    "application",
    "pv_kwp",
    "kwh",
    "backup",
    "brand",
    "voltage",
]

# The one list of deciding-question fields, read back out of the Literal
# above. The prompt's reminder and the fallback template derive their wording
# from it instead of copying the names a third time.
ASK_FIELDS: tuple[AskField, ...] = get_args(AskField)
ActionName = Literal[
    "open_configurator",
    "add_to_draft",
    "save_solution",
    "view_inquiry",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextBlock(Strict):
    type: Literal["text"] = "text"
    text: str
    refs: list[str] = Field(default_factory=list)


class AskBlock(Strict):
    type: Literal["ask"] = "ask"
    field: AskField
    options: list[str] = Field(default_factory=list)


# Why a card shows no price: the product page's own reasons
# (linker-commerce ProductCommerce::REASONS, CommerceState::page_reason).
PriceReason = Literal["login", "pending", "restricted", "project", "unpriced"]


class CardPrice(Strict):
    """A product card's price line, filled by the service, never by the model (#242).

    `text` is what the customer's own product page prints where the price stands,
    in the turn's language: the price for an approved partner account, otherwise
    the page's sentence, with `reason` saying why there is no price. The shell
    only renders it.
    """

    product_id: int
    text: str
    reason: PriceReason | None = None


class CardsBlock(Strict):
    type: Literal["cards"] = "cards"
    product_ids: list[int]
    # Filled after the run from the turn's tool results (prices.fill); the model
    # does not see the field, and whatever it puts there is replaced.
    prices: SkipJsonSchema[list[CardPrice] | None] = None


class CompareBlock(Strict):
    type: Literal["compare"] = "compare"
    product_ids: list[int] = Field(min_length=2, max_length=4)


class ActionBlock(Strict):
    type: Literal["action"] = "action"
    name: ActionName
    args: dict[str, Any] = Field(default_factory=dict)


class HandoffBlock(Strict):
    type: Literal["handoff"] = "handoff"
    summary: str


class DocumentBlock(Strict):
    """A hosted document as a link, never as a URL in the text (#233).

    The model writes only `ref`: a search-knowledge chunk ID or a pairing document
    fact ID (`compat.document.N`, `compat.document.BATTERYID.N`) of this turn. The
    service fills `label` and `url` from the tool result when it hydrates the turn.
    """

    type: Literal["document"] = "document"
    ref: str
    label: str | None = None
    url: str | None = None


# Why Genie offers the team's contact (#243, contact.py): the customer asked for a
# person, a company or service question, frustration, or the third round of one question.
ContactReason = Literal["asked", "service", "dissatisfied", "repeat"]


class ContactBlock(Strict):
    """The offer "Let Linker contact me", rendered by the shell as the contact card.

    The service adds it after the answer (contact.decide); it is not one of the blocks
    the model may write, so no model output can offer or send a contact request.
    """

    type: Literal["contact"] = "contact"
    reason: ContactReason


Block = Annotated[
    TextBlock
    | AskBlock
    | CardsBlock
    | CompareBlock
    | ActionBlock
    | HandoffBlock
    | DocumentBlock,
    Field(discriminator="type"),
]


class TurnOutput(Strict):
    """One assistant turn: language plus a short list of blocks."""

    language: Locale
    blocks: list[Block] = Field(min_length=1)

    @model_validator(mode="after")
    def at_most_one_ask(self) -> TurnOutput:
        asks = [block for block in self.blocks if isinstance(block, AskBlock)]
        if len(asks) > 1:
            raise ValueError("at most one ask block per turn")
        return self


class PageContext(Strict):
    """The page the customer is on when they send the turn (#234).

    The shell sends what the page shows: its type, address and title, and the IDs of
    what it shows. The service reads the page's content itself from those IDs
    (`linker_genie.page`); the title is only how the page names itself.
    """

    type: PageType = "other"
    # A product page's product, as the turn's product IDs are: the English post
    # (search-products' IDs, lexicon.py), also on the German page.
    product_id: int | None = None
    # The products of the solution draft, English posts like product_id.
    draft_ids: list[int] | None = None
    # A page address of at most 2,048 characters: the sitemaps protocol's limit for a
    # page URL (sitemaps.org, "less than 2,048 characters"); the shell cuts to it
    # (PageContext.php URL_LENGTH).
    url: str | None = Field(default=None, max_length=2048)
    # The longest published title of the snapshot of 2026-10-18 has 95 characters, the
    # longest term name 46; 300 leaves three times the room (PageContext.php
    # TITLE_LENGTH mirrors it).
    title: str | None = Field(default=None, max_length=300)
    # The page or blog post the page shows, in the page's own language (on a product
    # page: the product post the visitor reads, the German one on a German page).
    post_id: int | None = None
    # The product category the page lists, in the page's own language.
    category_id: int | None = None


class UserContext(Strict):
    logged_in: bool = False
    partner: bool = Field(
        default=False,
        description=(
            "Whether the customer is an approved partner account, the one kind "
            "of account the site shows net prices (CommerceState). Guests, "
            "pending and restricted accounts are not. The shell sends the site's "
            "own answer (linker_commerce_visitor_sees_prices, #242), never "
            "'signed in'; absent reads as not approved. The turn log keeps it so "
            "the quality judges can tell a price shown to an approved account "
            "from one shown to anybody else."
        ),
    )
    context: str | None = Field(
        default=None,
        description=(
            "The signed-in customer's identity token, minted by the shell and "
            "valid for UserContext::TTL seconds (plugins/linker-tools; nothing "
            "marks it used, the window is the whole of its life). The service "
            "sends it back on the abilities that "
            "answer for this customer (abilities.USER_CONTEXT_ABILITIES: the "
            "inquiry list and the product abilities, whose prices follow the "
            "account) and never stores or logs it."
        ),
    )


class TurnMessage(Strict):
    role: Literal["user", "assistant"]
    content: str


class TurnRequest(Strict):
    conversation_id: str
    messages: list[TurnMessage]
    locale: Locale = "en"
    page_context: PageContext = Field(default_factory=PageContext)
    user: UserContext = Field(default_factory=UserContext)


class VoteRequest(Strict):
    """A customer's feedback on one logged turn: +1 or -1."""

    vote: Literal[1, -1]
