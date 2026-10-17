"""Strict structured output of one Genie turn (docs/specs/13-genie.md).

The model may only emit IDs and `{fact:ID}` placeholders. Numbers are filled
in after the run (hydration). Illegal structure is refused by Pydantic.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

Locale = Literal["en", "de"]
PageType = Literal["category", "product", "draft", "account", "other"]
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


class CardsBlock(Strict):
    type: Literal["cards"] = "cards"
    product_ids: list[int]


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
    type: PageType = "other"
    product_id: int | None = None
    draft_ids: list[int] | None = None


class UserContext(Strict):
    logged_in: bool = False
    partner: bool = Field(
        default=False,
        description=(
            "Whether the customer is an approved partner account, the one kind "
            "of account the site shows net prices (CommerceState). Guests, "
            "pending and restricted accounts are not. The shell does not send "
            "it yet (#242 makes prices follow the account); absent reads as not "
            "approved. The turn log keeps it so the quality judges can tell a "
            "price shown to an approved account from one shown to anybody else."
        ),
    )
    context: str | None = Field(
        default=None,
        description=(
            "The signed-in customer's identity token, minted by the shell and "
            "valid for 120 seconds (nothing marks it used; the window is the "
            "whole of its life). The service sends it back on the one ability "
            "that answers about this customer (linker/inquiry-status) and never "
            "stores it."
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
