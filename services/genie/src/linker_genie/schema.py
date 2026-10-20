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
    # The inquiry confirmation card (#250): the action only asks the shell to show
    # the card; the customer's Send button is the one writer (inquiry.py).
    "send_inquiry",
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


# A parts list (#251): the service's block, never the model's. The model does not
# write a parts turn at all (app._answer); the rows and the one add action come from
# `parts.py` alone.
class PartsCandidate(Strict):
    """One product an uncertain row may be: its ID and the names the card shows."""

    product_id: int
    # The model as our titles write it ("H2-10K-T3"): what a chip sends back.
    label: str
    # The product's full title, for the card's second line.
    name: str = ""


PartsStatus = Literal["matched", "uncertain", "missing", "skipped"]
# The longest row text the parts card shows and the facts carry (parts.TEXT_CHARS,
# where the source of the number is written).
PARTS_TEXT_CHARS = 300


class PartsRow(Strict):
    """One line of the customer's list and what code made of it."""

    # The row's position in the list, from 1: a chip answers "Row N: ...".
    line: int
    text: str = Field(max_length=PARTS_TEXT_CHARS)
    quantity: int
    status: PartsStatus
    product_id: int | None = None
    label: str | None = None
    # The candidates of an uncertain row, at most `parts.MAX_OPTIONS`.
    options: list[PartsCandidate] = Field(default_factory=list)


class PartsItem(Strict):
    """One line of the solution draft the add action writes."""

    product_id: int
    quantity: int


class PartsAdd(Strict):
    """The one native WooCommerce write: every confirmed row, merged by product."""

    items: list[PartsItem]
    # Distinct products and the rows they came from, for the button's words.
    products: int
    rows: int


class PartsBlock(Strict):
    """The parts list as the shell shows it: statuses, one question, one action."""

    type: Literal["parts"] = "parts"
    rows: list[PartsRow]
    # The first uncertain row the customer is being asked about, if any.
    ask_line: int | None = None
    # Filled only when at least one row is confirmed; the shell's one add.
    add: PartsAdd | None = None
    # The list had more than `parts.MAX_ROWS` rows and was cut there.
    truncated: bool = False


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


class DraftLine(Strict):
    """One line of the visitor's solution draft (#459).

    The shell reads it from the visitor's own cart: the English product id, as
    `draft_ids` are, and the line quantity the inquiry and contact handoff already
    read (`$line['quantity']`). The browser's copy is dropped (PageContext.php
    `sanitize`); the proxy fills this. Absent on a turn means the reader has no
    quantity for that line and does not guess 1.
    """

    product_id: int
    quantity: int


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
    # Those products' cart quantities, same English ids. The shell fills this from
    # the visitor's cart; a turn without it names the products and states no quantity.
    draft_lines: list[DraftLine] | None = None
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


# What a customer may attach (#236, docs/specs/13-genie.md "附件与铭牌"). The shell turns
# a photo into a JPEG (a HEIC photo too) before it is sent, so the wire carries the
# formats deepseek-flash reads (JPEG, PNG, WebP; docs/research/2026-10-17-deepseek-
# flash-vision/ §3.2) and PDF, which the service reads itself. A parts list travels as
# CSV or .xlsx (#251): text and a zip of XML, read in this process, never sent to a model.
UploadType = Literal[
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]
# A file's name as the thread shows it: the longest file name most file systems allow
# is 255 bytes (ext4, APFS, NTFS); the shell and the proxy cut to the same length.
NAME_LENGTH = 255
# The limits of one turn's uploads, the same numbers as the proxy's
# (plugins/linker-tools/includes/Genie/Attachments.php; tests/test_attachments.py locks
# the two together):
# - three files: a nameplate photo, a second angle of it and a datasheet;
# - an image of at most 6 MiB: the shell sends a JPEG of about 1.69 megapixels (the
#   size deepseek-flash scales every image to, research §3.3), a few hundred kilobytes;
#   six mebibytes holds even an uncompressed 1.69-megapixel image (5.07 MB of RGB) sent
#   by another client;
# - a PDF of at most 16 MiB: the largest hosted datasheet is 5.09 MB and the median
#   hosted manual 7.3 MB (uploads of the live snapshot 2026-10-18); a larger manual is
#   better sent as the pages that matter;
# - 20 MiB for the turn, well below deepseek-flash's 48 MiB request body (research §3.2).
MAX_FILES = 3
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_PDF_BYTES = 16 * 1024 * 1024
# A list file (#251): a 20-row list is two kilobytes; one mebibyte holds about
# twenty thousand lines of the shape customers paste, and no real parts list of
# MAX_ROWS rows comes near it. An Excel workbook may carry images and styles, so it
# keeps the image ceiling. Sources: the fixture lists of docs/research/
# 2026-10-17-ai-assistants/ (61 rows is the largest, Taobao, CN.md S32) and the
# 2026-10-15 snapshot's product titles.
MAX_CSV_BYTES = 1 * 1024 * 1024
MAX_XLSX_BYTES = 6 * 1024 * 1024
MAX_TURN_BYTES = 20 * 1024 * 1024


def base64_chars(size: int) -> int:
    """Characters of `size` bytes in base64: three bytes are four characters."""
    return -(-size // 3) * 4


_MAX_DATA_CHARS = base64_chars(MAX_PDF_BYTES)
# Readings kept per conversation and carried into every turn (Thread::READINGS); the
# oldest go first. Ten covers a session of several devices and their datasheets.
MAX_READINGS = 10
# The text kept of one reading: sixty thousand characters (about eighteen thousand
# tokens, 0.3 per character, research §3.3) hold a datasheet of every page the service
# reads; the model reads only the passages nearest the question of a longer one.
MAX_READING_CHARS = 60_000
# A turn's thread as the browser sends it: the proxy keeps sixty messages
# (Thread::LIMIT) and the longest answer in the turn logs of five local instances is
# 4 687 characters (the whole output JSON, 2026-10-18); sixty of 5 000 characters at
# JSON's worst escaping (six bytes, "\uXXXX", wp_json_encode's default) is 1.8 MB.
THREAD_BYTES = 2 * 1024 * 1024
# The largest turn request the service reads (app.py caps the body before parsing):
# the turn's files in base64, the conversation's readings at JSON's worst escaping,
# and the thread.
MAX_REQUEST_BYTES = (
    base64_chars(MAX_TURN_BYTES) + MAX_READINGS * MAX_READING_CHARS * 6 + THREAD_BYTES
)


class Upload(Strict):
    """One file the customer attached to this turn, as base64. Never stored."""

    name: str = Field(max_length=NAME_LENGTH)
    type: UploadType
    data: str = Field(max_length=_MAX_DATA_CHARS, repr=False)


# One printed field of a nameplate as the service keeps it (a brand, a model, a
# product type, a rating's label or value): the longest line printed on the eval's
# labels is the GoodWe BAT-AC label's "Crucial Material" row, 74 characters
# (eval/attachments, 2026-10-18), and the longest product type read was 62; two
# hundred keeps such a line whole with room for a wordier maker, and cuts a model's
# runaway answer (`attachments._short`).
FIELD_CHARS = 200
# Ratings kept of one nameplate: the most read off one label in the eval was 24 (the
# GoodWe GW10K-ET); sixty is two and a half times that.
MAX_RATINGS = 60
# A reading's id: "att" and its number in the conversation, counted from 1 and never
# reused (attachments.read numbers after the highest kept). At the hourly allowance
# of 20 files (Attachments::LIMIT) a conversation reaches 1 000 000 files after
# more than five years of uploads without pause; six digits hold that.
READING_ID = r"^att[1-9][0-9]{0,5}$"
# Why a file was not read (attachments.py): the shell shows the card's own words for
# each, and the turn log names it.
FailedReason = Literal[
    "not_base64",
    "empty",
    "too_large",
    "turn_too_large",
    "type",
    "too_many_pixels",
    "unreadable_image",
    "unreadable_pdf",
    "unreadable_list",
    "pdf_timeout",
    "pdf_failed",
    "unread",
    "no_reader",
    "channel_refused",
]


class Rating(Strict):
    """One line of a nameplate as printed: its label and its value."""

    label: str = Field(max_length=FIELD_CHARS)
    value: str = Field(max_length=FIELD_CHARS)


ReadingKind = Literal["nameplate", "document", "photo", "list"]


class AttachmentReading(Strict):
    """What the service read from one attachment (attachments.py).

    The proxy keeps it with the conversation (Thread::READINGS) and sends it back with
    every later turn, so the customer can ask about the file again without sending it
    again; the file itself is never kept. `failed` names why nothing could be read.
    """

    id: str = Field(pattern=READING_ID)
    name: str = Field(max_length=NAME_LENGTH)
    kind: ReadingKind
    brand: str | None = Field(default=None, max_length=FIELD_CHARS)
    model: str | None = Field(default=None, max_length=FIELD_CHARS)
    product_type: str | None = Field(default=None, max_length=FIELD_CHARS)
    ratings: list[Rating] = Field(default_factory=list, max_length=MAX_RATINGS)
    text: str = Field(default="", max_length=MAX_READING_CHARS)
    # A PDF's page count, and the pages read (text layer or rendered).
    pages: int | None = None
    pages_read: int | None = None
    # A CSV/Excel list had more rows than parts.MAX_ROWS; the reading keeps the
    # first MAX_ROWS and says so (parts.py, #251).
    truncated: bool = False
    failed: FailedReason | None = None


class TurnRequest(Strict):
    conversation_id: str
    messages: list[TurnMessage]
    locale: Locale = "en"
    page_context: PageContext = Field(default_factory=PageContext)
    user: UserContext = Field(default_factory=UserContext)
    # The files of this turn (#236). Separate from `messages`, which the proxy stores
    # as the thread: a file rides once and is read once.
    attachments: list[Upload] = Field(default_factory=list, max_length=MAX_FILES)
    # What earlier turns read from their files, kept by the proxy (Thread::READINGS).
    readings: list[AttachmentReading] = Field(
        default_factory=list, max_length=MAX_READINGS
    )


class VoteRequest(Strict):
    """A customer's feedback on one logged turn: +1 or -1."""

    vote: Literal[1, -1]


# Entries one process keeps (`page.PageReader`), and the most paths one
# invalidation names. The site has 25 pages per language, a few blog posts,
# 16 product categories and 106 products (snapshot 2026-10-18); 256 holds the
# pages customers ask from. A save names a page, its language twin, the
# previous slug, and the listings that show it. One call need not name more
# paths than the process holds; the shell sends another call past this.
# `PageCache::MAX_PATHS` is this same number (PHP cannot import it;
# tests/test_page.py reads that line).
CACHE_SIZE = 256


class PageInvalidate(Strict):
    """Pages whose cached text the shell asks the service to drop (#405).

    One save names a page, its language twin, the previous slug, and the
    listings that show it. `CACHE_SIZE` is the most paths one call carries;
    the shell sends another call past that.
    """

    paths: list[str] = Field(min_length=1, max_length=CACHE_SIZE)
