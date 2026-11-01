"""Typed Woo cable facts, never editable project electrical parameters."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .geometry_documents import Hash, Identifier, Nonnegative, Number, Positive, Text


class CableEvidence(Document):
    document_id: Text
    document_revision: Hash
    blob_sha256: Hash
    product_id: Count
    url: Annotated[str, Field(pattern=r"^https://de-linker\.com/wp-content/uploads/")]
    page: Count
    quote: Annotated[str, Field(min_length=1, max_length=2000)]


class CableParameterSet(Document):
    id: Identifier
    current_kind: Literal["dc", "ac"]
    temperature_c: Number
    frequency_hz: Positive | None
    arrangement: Text | None
    resistance_ohm_per_km: Positive
    reactance_ohm_per_km: Nonnegative | None
    resistance_basis: Literal["maximum", "nominal"]
    source: CableEvidence

    @model_validator(mode="after")
    def domain(self) -> Self:
        if self.current_kind == "dc" and (
            self.frequency_hz is not None or self.reactance_ohm_per_km is not None
        ):
            raise ValueError("DC resistance facts must not masquerade as AC impedance")
        if self.current_kind == "ac" and (
            self.frequency_hz is None
            or self.reactance_ohm_per_km is None
            or self.arrangement is None
        ):
            raise ValueError("AC impedance needs its frequency and arrangement")
        return self


class CableReferenceCurrentRating(Document):
    """One cited manufacturer table row, not a site ampacity clearance."""

    id: Identifier
    laying: Literal["single_in_air", "single_on_surface", "two_touching_on_surface"]
    ambient_temperature_c: Number
    rated_conductor_temperature_c: Number
    current_a: Positive
    source: CableEvidence


class CableFacts(Document):
    schema_version: SchemaVersion
    construction: Literal["single_conductor", "multicore_cable"]
    core_count: Count
    cross_section_mm2: Positive
    conductor_material: Text
    insulation: Text
    source: CableEvidence
    parameter_sets: list[CableParameterSet]
    # Older publications lack this optional, source-bound table entirely.
    reference_current_ratings: list[CableReferenceCurrentRating] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def identities(self) -> Self:
        if len({p.id for p in self.parameter_sets}) != len(self.parameter_sets):
            raise ValueError("cable parameter set IDs must be distinct")
        if len({p.id for p in self.reference_current_ratings}) != len(
            self.reference_current_ratings
        ):
            raise ValueError("cable reference-current IDs must be distinct")
        if self.reference_current_ratings and self.construction != "single_conductor":
            raise ValueError("reference-current table requires a single conductor")
        if self.construction == "single_conductor" and self.core_count != 1:
            raise ValueError("a single conductor has one core")
        return self
