"""A nameplate photo against our products: how sure the match is, decided in code (#236).

deepseek-flash reads the brand and the model off the photo (attachments.py); whether
that is one of our products is decided here, by the product words of the Woo products
(lexicon.py), never by the model's own confidence (ticket #236: "置信度由产品数据的确定性
命中决定"). Four grades:

- `exact`: the model as printed is one of our models, word for word after
  normalization ("H2-10K-T3", "h2 10k t3");
- `partial`: a series of ours or part of the model matches (the family is right, the
  model is not certain): the customer picks from the family's products;
- `none`: what the nameplate reads is not in our range (our brand perhaps, not this
  model);
- `unreadable`: the model could not be read (a brand alone names no device): a
  sharper photo or the model typed in.

The customer then confirms (the shell's buttons send a message naming the model), and
the next turn goes to the product or its pairings by the usual route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from linker_genie.lexicon import Match, Vocabulary, normalize
from linker_genie.schema import AttachmentReading

Grade = Literal["exact", "partial", "none", "unreadable"]
# Candidate products the card names as buttons: four buttons and "type the model" fit
# the dock's width at 390 px in two rows (docs/acceptance/2026-10-18/236/).
CANDIDATES = 4


@dataclass(frozen=True)
class Identified:
    """One nameplate's match: the grade and the product words that made it."""

    reading_id: str
    grade: Grade
    matches: tuple[Match, ...] = ()
    product_ids: tuple[int, ...] = field(default=())


def identify(
    reading: AttachmentReading, vocabulary: Vocabulary | None
) -> Identified | None:
    """The grade of a nameplate reading; None for any other reading."""
    if reading.kind != "nameplate" or reading.failed:
        return None
    if not reading.model:
        # A brand alone names no device: "we do not carry it" would be a guess.
        return Identified(reading.id, "unreadable")
    if vocabulary is None:
        # Without the product words nothing can be matched; the turn log names why
        # (understand.py, `vocabulary_error`).
        return Identified(reading.id, "none")
    if reading.model:
        printed = normalize(reading.model)
        for match in vocabulary.match(reading.model):
            if match.kind == "model" and normalize(match.words) == printed:
                return Identified(
                    reading.id, "exact", (match,), tuple(sorted(match.product_ids))
                )
    words = " ".join(
        part for part in (reading.brand, reading.model, reading.product_type) if part
    )
    matches = tuple(vocabulary.match(words))
    if any(m.kind in ("series", "model") for m in matches):
        return Identified(reading.id, "partial", matches)
    return Identified(reading.id, "none", matches)


def card(
    reading: AttachmentReading,
    identified: Identified | None,
    shown: list[int],
    labels: dict[int, str],
) -> dict[str, Any]:
    """What the shell shows for one attachment (the SSE `attachment` event).

    `shown` are the products the route found for the nameplate, in the search's order;
    the card names up to `CANDIDATES` of them by their model, for the customer to
    confirm. Words are the shell's (its .po); this carries codes and names only.
    """
    item: dict[str, Any] = {
        "id": reading.id,
        "name": reading.name,
        "kind": reading.kind,
        "failed": reading.failed,
    }
    if reading.kind == "document" or reading.pages is not None:
        item["pages"] = reading.pages
        item["pages_read"] = reading.pages_read
    if identified is not None:
        item.update(
            brand=reading.brand,
            model=reading.model,
            product_type=reading.product_type,
            match=identified.grade,
        )
        if identified.grade == "exact":
            ids = list(identified.product_ids)
        elif identified.grade == "partial":
            ids = shown
        else:
            ids = []
        item["products"] = [
            {"product_id": pid, "label": labels[pid]}
            for pid in ids[:CANDIDATES]
            if pid in labels
        ]
    return item
