"""The products of the engineering feed: the ones the engine may propose and
their cited figures.

The feed comes from linker-commerce (docs/specs/8-engineering-data.md, target
shape 5) and is validated against `schemas/feed.schema.json` when it is
loaded; a feed that does not match is refused, never patched. Top-level facts
are #7's SelectionFactSet; "unknown" is kept as `None` and never matches or
conflicts on its own (docs/specs/7-selection-facts.md).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import jsonschema

from . import units

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


class FeedError(ValueError):
    """The feed or the compatibility file does not match its schema."""


def validate(document: Any, schema_name: str) -> None:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        where = "/".join(str(part) for part in first.path)
        raise FeedError(
            f"{schema_name}: {len(errors)} error(s); first at /{where}: {first.message}"
        )


@dataclass(frozen=True)
class Citation:
    url: str
    page: int | None = None
    doc: str | None = None


@dataclass(frozen=True)
class Figure:
    value: str
    unit: str | None
    citation: Citation
    value_de: str | None = None
    qualifier: str | dict[str, Any] | list[Any] | None = None
    evidence_refs: tuple[str, ...] = ()
    columns: tuple[dict[str, str | int | float], ...] = ()


@dataclass(frozen=True)
class Document:
    url: str
    title: str
    type: str
    lang: str
    document_id: str | None = None
    document_revision: str | None = None
    blob_sha256: str | None = None
    product_ids: list[int] | None = None
    role: str | None = None
    citation_aliases: list[str] | None = None
    aliases: list[str] | None = None


def _known(value: Any) -> Any:
    return None if value == "unknown" else value


def _figures(raw: dict[str, Any]) -> dict[str, Figure]:
    return {
        key: Figure(
            value=str(entry["value"]),
            unit=entry.get("unit"),
            citation=Citation(
                entry["citation"]["url"],
                entry["citation"].get("page"),
                entry["citation"].get("doc"),
            ),
            value_de=entry.get("value_de"),
            qualifier=entry.get("qualifier"),
            evidence_refs=tuple(entry.get("evidence_refs", [])),
            columns=tuple(entry.get("columns", [])),
        )
        for key, entry in raw.items()
    }


@dataclass(frozen=True)
class Product:
    """A published product and the facts and figures the engine reads from it."""

    id: int
    sku: str
    model: str
    brand: str
    series: str | None
    device_class: str
    application: str | None
    phase: int | None
    ac_power_kw: float | None
    pv_input_kw: float | None
    usable_kwh: float | None
    nominal_kwh: float | None
    kwh_range: tuple[float, float] | None
    figures: dict[str, Figure] = field(repr=False)
    documents: tuple[Document, ...] = field(repr=False)

    @classmethod
    def from_feed(cls, raw: dict[str, Any]) -> Product:
        kwh_range = raw["kwh_range"]
        return cls(
            id=raw["id"],
            sku=raw["sku"],
            model=raw["model"],
            brand=raw["brand"],
            series=raw["series"],
            device_class=raw["device_class"],
            application=_known(raw["application"]),
            phase=_known(raw["phase"]),
            ac_power_kw=_known(raw["ac_power_kw"]),
            pv_input_kw=_known(raw["pv_input_kw"]),
            usable_kwh=_known(raw["usable_kwh"]),
            nominal_kwh=_known(raw["nominal_kwh"]),
            kwh_range=(kwh_range["min"], kwh_range["max"]) if kwh_range else None,
            figures=_figures(raw["figures"]),
            documents=tuple(Document(**document) for document in raw["documents"]),
        )

    def figure(self, key: str) -> Figure | None:
        return self.figures.get(key)

    def value(self, key: str) -> str | None:
        found = self.figures.get(key)
        return found.value if found else None

    # Inverter side ---------------------------------------------------------

    @cached_property
    def n_mppt(self) -> int | None:
        return units.count(self.value("n_mppt"))

    @cached_property
    def strings_per_mppt(self) -> list[int] | None:
        values = units.per_input(self.value("strings_per_mppt"), self.n_mppt)
        return [int(v) for v in values] if values else None

    @cached_property
    def mppt_max_current_a(self) -> list[float] | None:
        return units.per_input(self.value("mppt_max_current_a"), self.n_mppt)

    @cached_property
    def mppt_max_isc_a(self) -> list[float] | None:
        return units.per_input(self.value("mppt_max_isc_a"), self.n_mppt)

    @cached_property
    def mppt_voltage_range_v(self) -> tuple[float, float] | None:
        return units.number_range(self.value("mppt_voltage_range_v"))

    @cached_property
    def max_pv_input_v(self) -> float | None:
        return units.number(self.value("max_pv_input_v"))

    @cached_property
    def battery_voltage_range_v(self) -> tuple[float, float] | None:
        return units.number_range(self.value("battery_voltage_range_v"))

    # Battery side ----------------------------------------------------------

    @cached_property
    def modules_per_stack(self) -> tuple[int, int] | None:
        low = units.count(self.value("modules_per_stack_min"))
        high = units.count(self.value("modules_per_stack_max"))
        if high is None:
            return None
        return (low or 1, high)

    @cached_property
    def stacks_parallel_max(self) -> int | None:
        return units.count(self.value("stacks_parallel_max"))

    @cached_property
    def modules_per_system_max(self) -> int | None:
        return units.count(self.value("modules_per_system_max")) or units.count(
            self.value("max_battery_modules")
        )

    @cached_property
    def operating_voltage_range_v(self) -> tuple[float, float] | None:
        return units.number_range(self.value("system_operating_voltage_range_v"))


@dataclass(frozen=True)
class PvModule:
    """The reference PV module of the engineering overlay (a design assumption)."""

    id: str
    brand: str
    model: str
    pmax_w: float
    voc_v: float
    vmpp_v: float
    isc_a: float
    impp_a: float
    beta_voc_pct_per_c: float
    max_series_fuse_a: float
    length_m: float
    width_m: float
    figures: dict[str, Figure] = field(repr=False)
    documents: tuple[Document, ...] = field(repr=False)

    @classmethod
    def from_overlay(cls, raw: dict[str, Any]) -> PvModule:
        figures = _figures(raw["figures"])

        def need(key: str) -> float:
            found = figures.get(key)
            value = units.number(found.value) if found else None
            if value is None:
                raise FeedError(f"overlay {raw['id']}: figure {key} is missing")
            return value

        dimensions = figures.get("dimensions_mm")
        sides = [
            float(side)
            for side in (dimensions.value if dimensions else "")
            .replace("×", "x")
            .split("x")
            if side.strip().replace(".", "").isdigit()
        ]
        if len(sides) < 2:
            raise FeedError(f"overlay {raw['id']}: figure dimensions_mm is missing")
        return cls(
            id=raw["id"],
            brand=raw["brand"],
            model=raw["model"],
            pmax_w=need("pmax_w"),
            voc_v=need("voc_v"),
            vmpp_v=need("vmpp_v"),
            isc_a=need("isc_a"),
            impp_a=need("impp_a"),
            beta_voc_pct_per_c=need("beta_voc_pct_per_c"),
            max_series_fuse_a=need("max_series_fuse_a"),
            length_m=sides[0] / 1000,
            width_m=sides[1] / 1000,
            figures=figures,
            documents=tuple(Document(**document) for document in raw["documents"]),
        )


@dataclass(frozen=True)
class Products:
    """All products of one feed, indexed for the design steps."""

    generated_at: str
    compatibility_version: str
    products: tuple[Product, ...]
    reference_module: PvModule | None

    @property
    def module(self) -> PvModule:
        """Only paths that actually need a prepared reference may read it.

        A withdrawn reference does not prevent loading unrelated saleable
        products. HTTP consumers establish its current Woo evidence first.
        """
        if self.reference_module is None:
            raise FeedError("feed has no prepared reference PV module")
        return self.reference_module

    @classmethod
    def from_feed(cls, feed: dict[str, Any]) -> Products:
        validate(feed, "feed.schema.json")
        modules = [item for item in feed["overlay"] if item["kind"] == "pv_module"]
        return cls(
            generated_at=feed["generated_at"],
            compatibility_version=feed["compatibility_version"],
            products=tuple(Product.from_feed(raw) for raw in feed["products"]),
            reference_module=PvModule.from_overlay(modules[0]) if modules else None,
        )

    @classmethod
    def load(cls, path: Path) -> Products:
        return cls.from_feed(json.loads(path.read_text()))

    @cached_property
    def by_id(self) -> dict[int, Product]:
        return {product.id: product for product in self.products}

    def in_class(self, *device_classes: str) -> list[Product]:
        return [p for p in self.products if p.device_class in device_classes]

    def by_model_pattern(self, pattern: str) -> list[Product]:
        import re

        compiled = re.compile(pattern)
        return [p for p in self.products if compiled.search(p.model)]
