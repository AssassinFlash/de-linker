"""Product words: the deterministic first step of every turn (docs/specs/13-genie.md, goal 2).

The vocabulary is read from the published WooCommerce products — the one hand-kept
source of product data (AGENTS.md §4) — and a customer message is matched against it
in code before any model sees it: brands, series, models, SKUs and categories, in
English and German, regardless of case, spaces or hyphens. A brand or model word is
therefore never read as a name or as small talk ("saj" answered "Hello saj" on
2026-10-16, turns.sqlite on linker-services).

Keys are compared after normalization: lower case, letters and digits only, so
"H2-10K-T3", "h2 10k t3" and "H210KT3" are one key. A message is cut into words on
whitespace and on hyphens, and every run of one to `MAX_WORDS` consecutive words is
looked up; a longer hit wins over the shorter hits inside it. A hyphenated body
inside a longer code is its own key when the join is an interior of width
`SHORT_BODY_WIDTH`, mixes a letter and a digit, and names one product ("BD-8" of
"EF BD-8-S2", and of a code that has no brand token, "BD-8-S2"). The trailing
segment ("S2", "G20") is not a key. A body that more than one product holds, or a
shared trailing suffix with no other product word, is a fixed question (route.py),
not a search and not a guess.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["brand", "series", "model", "category"]

# The longest model name in the vocabulary is five words ("OCEAN 2 LFP Battery Base",
# "EF HD-P1-10K0-S2" cut on hyphens; snapshot 2026-10-15); six leaves one word of room.
MAX_WORDS = 6
# A model code taken from a title must be at least four letters and digits long: the
# shortest real code is four ("L260"; "GM330" is five; snapshot 2026-10-15). A
# shorter token is not a full code. A trailing piece such as "S2" or "G20" is a
# suffix by where it sits, not because three characters is below four: "G20" is
# three characters and is still a suffix. A body the hyphen splits into short
# pieces ("BD-8") is recovered by _short_bodies.
MIN_CODE = 4
# Width of an interior model body ("BD" + "8" → "bd8"). This is not `MIN_CODE - 1`.
# "G20" is three characters and is a suffix: position and uniqueness keep it out,
# not length. #330 first round (campaign-330/evidence/final.jsonl, class
# misspelling, 10 messages; notes in docs/research/2026-10-20-campaign-330/NOTES.md):
# the only short-code miss is A3-EN "BD-8", whose normalized body is three
# characters. The other nine are longer codes (O for 0, an extra letter, spaced
# pieces) and passed without this key. Class E is 11/11 on case, hyphen and space,
# so this is not an edit distance. Dossier
# docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §1.1: no competitor
# publishes a misspelling rule, and the strategy is designed here. No
# four-character interior body failed, so a join of four characters is not a key.
# The 2026-10-15 snapshot (106 products) is the catalog the rule was checked
# against. It is not why the width is 3.
SHORT_BODY_WIDTH = 3
# A series alias without its brand ("h2" of saj-h2) must carry a digit or be at least
# three characters: "et" (goodwe-et) and "ci" (saj-ci-line) are ordinary letter pairs
# in English and German text, "h2", "b2", "hs3" and "esa" are not (_series_aliases).
MIN_SERIES_LETTERS = 3

# The device classes search-products filters on (plugins/linker-commerce/includes/
# Products/SelectionFacts.php DEVICE_CLASSES); a category outside the list takes its
# nearest listed ancestor there too.
DEVICE_CLASSES = (
    "inverters",
    "home-storage",
    "battery-systems",
    "all-in-one-systems",
    "ems-monitoring",
    "ev-chargers",
    "accessories",
)

# The pa_phase slugs of the English products (snapshot 2026-10-15) as search-products'
# phase filter takes them.
PHASES = {"single-phase": 1, "three-phase": 3}

_WORD = re.compile(r"[^\s/,;:!?()\[\]\"'„“”‚‘’]+")


def normalize(text: str) -> str:
    """Lower case, letters and digits only; umlauts kept as letters."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if ch.isalnum())


# A category word is compared without its plural ending only when five letters stay,
# so that short words are never cut into something else.
MIN_STEM = 5


def _forms(key: str) -> set[str]:
    """The key and the key without one plural ending, for category words.

    English -s/-es and German -en/-n/-e cover the category names on the site
    (Inverters, EV Chargers, Ladestationen, Batteriesysteme): "ladestation" and
    "ladestationen" share the form "ladestation", "inverter" and "inverters" share
    "inverter". The forms are only ever compared with each other, never shown.
    """
    forms = {key}
    for ending in ("en", "es", "s", "n", "e"):
        if key.endswith(ending) and len(key) - len(ending) >= MIN_STEM:
            forms.add(key[: -len(ending)])
    return forms


@dataclass(frozen=True)
class Entry:
    """One product word: what it names and how search-products is asked for it."""

    kind: Kind
    label: str
    # The value search-products filters on: the brand or series slug, the model as
    # it stands in the titles (the `text` filter), or the device class.
    value: str
    product_ids: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Match:
    """A product word found in a message."""

    kind: Kind
    label: str
    value: str
    product_ids: frozenset[int]
    words: str


@dataclass
class Vocabulary:
    """Normalized key → the entries it names."""

    entries: dict[str, list[Entry]] = field(default_factory=dict)
    # Product ID → device class, for routing a pairing question to the inverter.
    device_class: dict[int, str] = field(default_factory=dict)
    # Product ID → its title, for describing the page to Jev.
    names: dict[int, str] = field(default_factory=dict)
    # Product ID → its model as the titles write it, for search-products' text filter.
    labels: dict[int, str] = field(default_factory=dict)
    # Product ID → 1 or 3 (pa_phase), and series slug → its products: a family
    # named without a model is searched per phase when it has both (route.py).
    phase: dict[int, int] = field(default_factory=dict)
    series_members: dict[str, set[int]] = field(default_factory=dict)
    # Brand slug → its products, and product ID → its brand and series slugs: a
    # parts-list row that names only a brand (or a brand and a family) is not one
    # product (#251, parts.py); the candidates and a typed model's fit come from
    # these maps.
    brand_members: dict[str, set[int]] = field(default_factory=dict)
    brand_of: dict[int, set[str]] = field(default_factory=dict)
    # Brand slug → the name the store publishes, for naming a catalog brand when
    # the customer's brand word and the model disagree (route.py, #363).
    brand_names: dict[str, str] = field(default_factory=dict)
    series_of: dict[int, set[str]] = field(default_factory=dict)
    # Category keys are compared by their plural-less forms as well (_forms).
    category_forms: dict[str, list[Entry]] = field(default_factory=dict)
    # A shape-valid interior join that more than one product holds. route.py asks
    # which model, instead of searching the family the other words name.
    unresolved_bodies: frozenset[str] = frozenset()
    # Trailing segments shared by two or more products ("s2", "g20"). A message
    # that is only a pointer plus one of these asks which model (route.py).
    shared_suffixes: frozenset[str] = frozenset()

    def add(self, key: str, entry: Entry) -> None:
        if not key:
            return
        bucket = self.entries.setdefault(key, [])
        if entry not in bucket:
            bucket.append(entry)
        if entry.kind == "category":
            for form in _forms(key):
                forms = self.category_forms.setdefault(form, [])
                if entry not in forms:
                    forms.append(entry)

    def lookup(self, key: str) -> list[Entry]:
        found = list(self.entries.get(key, []))
        for form in _forms(key):
            for entry in self.category_forms.get(form, []):
                if entry not in found:
                    found.append(entry)
        return found

    def match(self, text: str) -> list[Match]:
        """Every product word of `text`, longest first, without overlaps."""
        return self._scan(text)[0]

    def model_codes(self) -> tuple[str, ...]:
        """Model codes as the titles and pa_model write them, each once.

        A code the customer types that is not among these is not a product word
        (route.py): the lexicon only matches codes it has seen.
        """
        seen: list[str] = []
        for entries in self.entries.values():
            for entry in entries:
                if entry.kind == "model" and entry.value not in seen:
                    seen.append(entry.value)
        return tuple(seen)

    def bare(self, text: str) -> bool:
        """Whether `text` is nothing but product words ("EMS", "SAJ H2", "Zubehör")."""
        matches, taken = self._scan(text)
        return bool(matches) and all(taken)

    def _scan(self, text: str) -> tuple[list[Match], list[bool]]:
        words = _words(text)
        taken = [False] * len(words)
        found: list[Match] = []
        for size in range(min(MAX_WORDS, len(words)), 0, -1):
            for start in range(len(words) - size + 1):
                if any(taken[start : start + size]):
                    continue
                key = "".join(normalize(word) for word in words[start : start + size])
                entries = self.lookup(key)
                if not entries:
                    continue
                for index in range(start, start + size):
                    taken[index] = True
                phrase = " ".join(words[start : start + size])
                for entry in entries:
                    # The English and German name of one category are two
                    # entries with one value; the match names the value once.
                    if any(
                        (m.kind, m.value, m.product_ids)
                        == (entry.kind, entry.value, entry.product_ids)
                        for m in found
                    ):
                        continue
                    found.append(
                        Match(
                            entry.kind,
                            entry.label,
                            entry.value,
                            entry.product_ids,
                            phrase,
                        )
                    )
        return found, taken


def _words(text: str) -> list[str]:
    """Words cut on whitespace, punctuation and hyphens ("Hybrid-Wechselrichter")."""
    words: list[str] = []
    for token in _WORD.findall(text):
        words.extend(part for part in token.split("-") if part)
    return [word.strip(".") for word in words if word.strip(".")]


@dataclass(frozen=True)
class Product:
    """The few fields of a Store API product the vocabulary reads."""

    id: int
    name: str
    sku: str
    brands: tuple[tuple[str, str], ...]  # (name, slug)
    series: tuple[str, ...]  # slugs; the site's series names are their slugs
    models: tuple[str, ...]
    categories: tuple[tuple[str, str], ...]  # (name, slug)
    phases: tuple[str, ...] = ()  # pa_phase slugs: single-phase, three-phase


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    slug: str
    parent: int


def build(
    products: Iterable[Product],
    categories: Iterable[Category],
    translated: Iterable[tuple[Product, Iterable[Category]]] = (),
) -> Vocabulary:
    """The vocabulary of the English products, plus German titles and categories.

    German products are their own posts that share the English SKU (Polylang); the
    turn's product IDs are the English ones (search-products' IDs), so a German word
    is joined to the English product through the SKU, and a German category to its
    English one through the products both contain.
    """
    vocabulary = Vocabulary()
    products = list(products)
    by_slug = {category.slug: category for category in categories}
    by_id = {category.id: category for category in by_slug.values()}
    by_sku = {product.sku: product for product in products if product.sku}
    for product in products:
        _add_product(vocabulary, product)
        for _name, slug in product.categories:
            device = _device_class(slug, by_slug, by_id)
            if device is not None:
                vocabulary.device_class.setdefault(product.id, device)
    for category in by_slug.values():
        # Only a category that is a device class names one: a child such as
        # backup-power or meters-current-transformers sits under accessories, and
        # "Notstrom" asks for backup-capable systems, not for every accessory.
        if category.slug not in DEVICE_CLASSES:
            continue
        _add_category(vocabulary, category.name, category.slug, category.slug)
    german_titles: dict[int, str] = {}
    for german, german_categories in translated:
        english = by_sku.get(german.sku)
        if english is None:
            continue
        # The same title codes `_add_codes` indexes, joined to the English id.
        # A later short-body pass reads them too (EN and DE keep one structure).
        german_titles[english.id] = german.name
        _add_codes(vocabulary, english, german.name)
        english_slugs = {slug for _name, slug in english.categories}
        for category in german_categories:
            if (category.name, category.slug) not in german.categories:
                continue
            # The German category is the English one this product sits in; a product
            # in two listed classes leaves the German name unjoined (unknown, as
            # SelectionFacts treats it).
            devices = {
                device
                for device in (
                    _device_class(slug, by_slug, by_id) for slug in english_slugs
                )
                if device is not None
            }
            if len(devices) != 1:
                continue
            device = devices.pop()
            if device not in english_slugs:
                # The product sits in a child category; its German name is the
                # child's, not the device class's.
                continue
            _add_category(vocabulary, category.name, category.slug, device)
    brand_keys = {
        key
        for key, entries in vocabulary.entries.items()
        if any(entry.kind == "brand" for entry in entries)
    }
    for key in brand_keys:
        # A series named after its brand alone ("chint") is the brand.
        vocabulary.entries[key] = [
            entry for entry in vocabulary.entries[key] if entry.kind != "series"
        ]
    _add_short_bodies(vocabulary, products, german_titles)
    return vocabulary


def _add_category(vocabulary: Vocabulary, name: str, slug: str, device: str) -> None:
    """A device-class category by its name, its slug and each side of an "&"."""
    label = _clean(name)
    entry = Entry("category", label, device)
    vocabulary.add(normalize(label), entry)
    vocabulary.add(normalize(slug), entry)
    if "&" in label:
        for side in label.split("&"):
            vocabulary.add(normalize(side), entry)


def _clean(name: str) -> str:
    return name.replace("&amp;", "&")


def _device_class(
    slug: str, by_slug: dict[str, Category], by_id: dict[int, Category]
) -> str | None:
    category = by_slug.get(slug)
    while category is not None:
        if category.slug in DEVICE_CLASSES:
            return category.slug
        category = by_id.get(category.parent)
    return None


def _add_product(vocabulary: Vocabulary, product: Product) -> None:
    ids = frozenset({product.id})
    for name, slug in product.brands:
        vocabulary.add(normalize(name), Entry("brand", name, slug))
        vocabulary.add(normalize(slug), Entry("brand", name, slug))
        vocabulary.brand_names.setdefault(slug, name)
    brand_slugs = [slug for _name, slug in product.brands]
    for slug in product.series:
        entry = Entry("series", slug, slug)
        vocabulary.add(normalize(slug), entry)
        for alias in _series_aliases(slug, brand_slugs, product.name):
            vocabulary.add(normalize(alias), entry)
    codes = _codes(product.name)
    # The label search-products' `text` filter is given: the model as the site names
    # it, else the first code of the title, which the title then contains.
    label = (
        product.models[0] if product.models else (codes[0] if codes else product.sku)
    )
    vocabulary.names[product.id] = product.name
    vocabulary.labels[product.id] = label
    for slug in product.phases:
        if slug in PHASES:
            vocabulary.phase[product.id] = PHASES[slug]
    for slug in product.series:
        vocabulary.series_members.setdefault(slug, set()).add(product.id)
        vocabulary.series_of.setdefault(product.id, set()).add(slug)
    for _name, slug in product.brands:
        vocabulary.brand_members.setdefault(slug, set()).add(product.id)
        vocabulary.brand_of.setdefault(product.id, set()).add(slug)
    for model in product.models:
        vocabulary.add(normalize(model), Entry("model", model, model, ids))
    _add_codes(vocabulary, product, product.name)
    sku_tail = _sku_tail(product.sku, brand_slugs)
    for sku in (product.sku, sku_tail):
        if sku:
            vocabulary.add(normalize(sku), Entry("model", label, label, ids))


def _add_codes(vocabulary: Vocabulary, product: Product, title: str) -> None:
    """The model codes of a title ("GW10K-EHA-G20"), for products without pa_model."""
    ids = frozenset({product.id})
    for code in _codes(title):
        vocabulary.add(normalize(code), Entry("model", code, code, ids))


def _codes(title: str) -> list[str]:
    """Title tokens before the bracket that mix letters and digits."""
    head = title.split("(", 1)[0]
    codes = []
    for token in head.split():
        key = normalize(token)
        if (
            len(key) >= MIN_CODE
            and any(ch.isdigit() for ch in key)
            and any(ch.isalpha() for ch in key)
        ):
            codes.append(token)
    return codes


def _add_short_bodies(
    vocabulary: Vocabulary, products: list[Product], german_titles: dict[int, str]
) -> None:
    """Index a hyphenated model body that names exactly one product.

    See `_short_bodies` for the rule. The search text is the source string that
    contains the body ("EF BD-8-S2", or "BD-8-S2" when that is the only source),
    not `models[0]` when the body sits on a later model. A key that already
    names something else (a series alias, a full code) is left as it is.
    """
    chosen, labels, unresolved = _short_bodies(products, german_titles)
    vocabulary.unresolved_bodies = frozenset(unresolved)
    vocabulary.shared_suffixes = _shared_suffixes(products, german_titles, set(chosen))
    for key, product_id in chosen.items():
        if key in vocabulary.entries:
            continue
        label = labels.get(key, "")
        if not label:
            continue
        vocabulary.add(key, Entry("model", label, label, frozenset({product_id})))


def _short_bodies(
    products: list[Product], german_titles: dict[int, str]
) -> tuple[dict[str, int], dict[str, str], set[str]]:
    """Interior joins that name one product, the source text, and the rest.

    The matcher cuts on hyphens, so "EF BD-8-S2" is the words EF, BD, 8, S2 and
    "BD-8-S2" is BD, 8, S2. "BD" and "8" are each shorter than `MIN_CODE` and
    were never keys; their join "bd8" is the body a customer writes. A join is
    a key only when all of the following hold. The width is `SHORT_BODY_WIDTH`
    (see that constant for the #330 measurement). Dossier §1.1 leaves the
    misspelling strategy to be designed; this is that design, and it is not an
    edit distance.

    - The trailing segment is never in the join. It is the suffix ("S2", "G20"),
      excluded by position. A code of at least four segments whose first segment
      is letters only skips that leading brand as well ("EF" of "EF BD-8-S2"),
      and only when two or more segments sit between it and the suffix. A
      three-segment code has no separate brand token ("BD-8-S2", a SKU of that
      shape): the join starts at the first piece.
    - Each piece is shorter than `MIN_CODE`. The join is exactly
      `SHORT_BODY_WIDTH` characters and has both a letter and a digit. A
      two-character join and a four-character join are not keys. A letters-only
      join is not a key.
    - The products that structurally produce the join and the products whose
      name, German title, SKU or model merely contain it are the same set, and
      that set has one product. "20K" inside both GW20K-ETA-G20 and H2-20K-T3
      is not a key. A second product that only contains the body as a substring
      is not a key either: the body is unresolved, and the route asks.

    The label of a key is the first source that produced it: a model, an English
    title code, a German title code (the same tokens `_add_codes` reads, mapped
    to the English id), the SKU tail, then the raw SKU. On the 2026-10-15
    snapshot the only such joins are bd8 (product 3582, "EF BD-8-S2") and bd5
    (product 3581, "EF BD-5-S2"). That snapshot is the catalog the rule was
    checked against, not the reason the width is 3.
    """
    identity = {
        product.id: _code_identity(product, german_titles.get(product.id, ""))
        for product in products
    }
    owners: dict[str, set[int]] = {}
    labels: dict[str, str] = {}
    for product in products:
        german = german_titles.get(product.id, "")
        for source in _code_sources(product, german):
            for key in _interior_joins(source):
                owners.setdefault(key, set()).add(product.id)
                labels.setdefault(key, source)
    chosen: dict[str, int] = {}
    unresolved: set[str] = set()
    for key, ids in owners.items():
        holders = {pid for pid, text in identity.items() if key in text}
        if holders == ids and len(ids) == 1:
            chosen[key] = next(iter(ids))
        else:
            unresolved.add(key)
    return chosen, labels, unresolved


def _interior_joins(code: str) -> list[str]:
    """Width-`SHORT_BODY_WIDTH` mixed joins that exclude the trailing segment."""
    segments = _segments(code)
    if len(segments) < 3:
        return []
    last = len(segments) - 1
    start_at = 1 if segments[0].isalpha() and last - 1 >= 2 else 0
    found: list[str] = []
    for start in range(start_at, last):
        # `end` stops at `last`, so the trailing segment is never included.
        for end in range(start + 2, last + 1):
            piece = segments[start:end]
            if any(len(normalize(part)) >= MIN_CODE for part in piece):
                continue
            key = normalize("".join(piece))
            if len(key) != SHORT_BODY_WIDTH or not _mixed(key):
                continue
            found.append(key)
    return found


def _code_sources(product: Product, german_name: str = "") -> list[str]:
    """Model strings, title codes and the SKU. Not the marketing words.

    German title codes are the tokens `_codes` already accepts (the head, before
    a bracket). A code that exists only inside parentheses is not a title code
    in either language. The raw SKU covers a code that is the whole SKU
    ("BD-8-S2") and not a `DLK-<brand>-<tail>` tail.
    """
    brand_slugs = [slug for _name, slug in product.brands]
    sources = list(product.models)
    sources.extend(_codes(product.name))
    if german_name:
        sources.extend(_codes(german_name))
    tail = _sku_tail(product.sku, brand_slugs)
    if tail:
        sources.append(tail)
    if product.sku:
        sources.append(product.sku)
    return sources


def _segments(code: str) -> list[str]:
    """Pieces of a model code on spaces and hyphens ("EF BD-8-S2")."""
    segments: list[str] = []
    for token in code.split():
        segments.extend(part for part in token.split("-") if part)
    return segments


def _code_identity(product: Product, german_name: str = "") -> str:
    """Name, German title, SKU and model, normalized, for the one-product check."""
    return normalize(
        " ".join((product.name, german_name, product.sku, *product.models))
    )


def _shared_suffixes(
    products: list[Product], german_titles: dict[int, str], chosen: set[str]
) -> frozenset[str]:
    """Trailing segments that two or more products share, minus short-body keys.

    Length is 2 through `SHORT_BODY_WIDTH`, and the token mixes a letter and a
    digit, so "S2" and "G20" count and "AC", "2" and a four-character tail do
    not. A suffix that is also a chosen body stays a body.
    """
    holders: dict[str, set[int]] = {}
    for product in products:
        german = german_titles.get(product.id, "")
        seen: set[str] = set()
        for source in _code_sources(product, german):
            segments = _segments(source)
            if len(segments) < 2:
                continue
            key = normalize(segments[-1])
            if 2 <= len(key) <= SHORT_BODY_WIDTH and _mixed(key):
                seen.add(key)
        for key in seen:
            holders.setdefault(key, set()).add(product.id)
    return frozenset(
        key for key, ids in holders.items() if len(ids) >= 2 and key not in chosen
    )


def _mixed(key: str) -> bool:
    """Whether a key has both a letter and a digit."""
    return any(ch.isalpha() for ch in key) and any(ch.isdigit() for ch in key)


def _series_aliases(slug: str, brand_slugs: list[str], title: str) -> list[str]:
    """The series as customers write it: with the brand spaced, and without it.

    Without the brand, a one-word alias must carry a digit ("h2", "b2", "hs3") or
    stand in the product title as an upper-case word ("ESA", "OCEAN"): the series
    slugs also hold ordinary words ("saj-data-collectors", "saj-accessories",
    "goodwe-meters") that are not names a customer means a series by.
    """
    aliases = [slug.replace("-", " ")]
    rest = slug
    for brand in brand_slugs:
        if slug.startswith(brand + "-"):
            rest = slug[len(brand) + 1 :]
    if rest == slug:
        return aliases
    parts = rest.split("-")
    title_words = set(title.split("(", 1)[0].split())
    candidates = [parts[0]]
    if len(parts) > 1:
        candidates.append(rest)
        if parts[1].isdigit():
            # "ocean-2-battery" → "ocean 2"
            candidates.append(f"{parts[0]} {parts[1]}")
    for candidate in candidates:
        key = normalize(candidate)
        words = candidate.split("-") if "-" in candidate else candidate.split()
        if len(words) > 1 and len(key) >= MIN_SERIES_LETTERS:
            aliases.append(" ".join(words))
        elif any(ch.isdigit() for ch in key) or (
            len(key) >= MIN_SERIES_LETTERS and candidate.upper() in title_words
        ):
            aliases.append(candidate)
    return aliases


def _sku_tail(sku: str, brand_slugs: list[str]) -> str:
    """ "DLK-SAJ-H210KT3" → "H210KT3": the SKU without the shop and brand prefixes."""
    parts = sku.split("-")
    if len(parts) >= 3 and parts[1].lower() in {slug.lower() for slug in brand_slugs}:
        return "-".join(parts[2:])
    return ""
