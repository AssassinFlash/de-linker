"""Release verdicts for inverter and battery pairs, and the parts named around an inverter.

Reads data/compatibility.json in the shape of `schemas/compatibility.schema.json`
(docs/specs/8-engineering-data.md, target shape 3). The verdict has three
values plus `unknown`, as the industry states releases: released, released
with an accessory, not released (docs/research/2026-10-09/
pv-wholesale-selection-tools.md, section 2.3). Only a manufacturer document
makes a release; a pair no entry covers is `unknown`, never assumed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from .catalog import validate

Verdict = Literal["released", "released_with_accessory", "not_released", "unknown"]
_STRICTNESS: dict[str, int] = {
    "not_released": 0,
    "released_with_accessory": 1,
    "released": 2,
}


@dataclass(frozen=True)
class Text:
    en: str
    de: str

    def get(self, locale: str) -> str:
        return self.de if locale == "de" else self.en


@dataclass(frozen=True)
class DocumentRef:
    url: str
    page: int | None = None


@dataclass(frozen=True)
class Accessory:
    model: str
    quantity: int
    per: Literal["system", "stack", "unit"]


@dataclass(frozen=True)
class PairResult:
    verdict: Verdict
    conditions: tuple[Text, ...] = ()
    documents: tuple[DocumentRef, ...] = ()
    modules: tuple[int, int] | None = None
    accessories: tuple[Accessory, ...] = ()

    @property
    def released(self) -> bool:
        return self.verdict in ("released", "released_with_accessory")


@dataclass(frozen=True)
class Requirement:
    kind: Literal["meter", "backup", "parallel_controller"]
    included: bool
    phase: int | None
    max_units: int | None
    accessories: tuple[Accessory, ...]
    conditions: tuple[Text, ...]
    documents: tuple[DocumentRef, ...]


@lru_cache(maxsize=512)
def _pattern(source: str) -> re.Pattern[str]:
    return re.compile(source)


def _texts(raw: list[dict[str, str]]) -> tuple[Text, ...]:
    return tuple(Text(item["en"], item["de"]) for item in raw)


def _documents(raw: list[dict[str, Any]]) -> tuple[DocumentRef, ...]:
    return tuple(DocumentRef(item["url"], item.get("page")) for item in raw)


def _accessories(raw: list[dict[str, Any]]) -> tuple[Accessory, ...]:
    return tuple(
        Accessory(item["model"], item["quantity"], item["per"]) for item in raw
    )


def _unique[T](items: list[T]) -> tuple[T, ...]:
    return tuple(dict.fromkeys(items))


class Compatibility:
    """Answers "what do the documents say about this pair / this inverter"."""

    def __init__(self, data: dict[str, Any]) -> None:
        validate(data, "compatibility.schema.json")
        self.version: str = data["version"]
        self._pairs: list[dict[str, Any]] = data["pairs"]
        self._requirements: list[dict[str, Any]] = data["requirements"]

    @classmethod
    def load(cls, path: Path) -> Compatibility:
        return cls(json.loads(path.read_text()))

    def pair(self, inverter_model: str, battery_model: str) -> PairResult:
        matches = [
            pair
            for pair in self._pairs
            if _pattern(pair["inverter"]).search(inverter_model)
            and _pattern(pair["battery"]).search(battery_model)
        ]
        if not matches:
            return PairResult("unknown")
        verdict = min(
            (pair["verdict"] for pair in matches), key=_STRICTNESS.__getitem__
        )
        ranges = [
            (pair["modules"]["min"], pair["modules"]["max"])
            for pair in matches
            if "modules" in pair
        ]
        modules = None
        if ranges:
            low = max(r[0] for r in ranges)
            high = min(r[1] for r in ranges)
            modules = (low, high) if low <= high else (low, low - 1)
        return PairResult(
            verdict=verdict,
            conditions=_unique(
                [t for pair in matches for t in _texts(pair["conditions"])]
            ),
            documents=_unique(
                [d for pair in matches for d in _documents(pair["documents"])]
            ),
            modules=modules,
            accessories=_unique(
                [
                    a
                    for pair in matches
                    for a in _accessories(pair.get("accessories", []))
                ]
            ),
        )

    def requirements(self, inverter_model: str, kind: str) -> list[Requirement]:
        return [
            Requirement(
                kind=item["kind"],
                included=item["included"],
                phase=item.get("phase"),
                max_units=item.get("max_units"),
                accessories=_accessories(item.get("accessories", [])),
                conditions=_texts(item["conditions"]),
                documents=_documents(item["documents"]),
            )
            for item in self._requirements
            if item["kind"] == kind
            and _pattern(item["inverter"]).search(inverter_model)
        ]
