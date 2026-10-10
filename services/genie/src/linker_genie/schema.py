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


Block = Annotated[
    TextBlock | AskBlock | CardsBlock | CompareBlock | ActionBlock | HandoffBlock,
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
    partner: bool = False


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
