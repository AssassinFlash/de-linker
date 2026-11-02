"""Project-supplied, condition-bound evidence for circuit protection checks."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import model_validator

from .energy_inputs import Document
from .geometry_documents import Hash, Identifier, Nonnegative, Positive, Text


class FaultRange(Document):
    minimum_fault_a: Nonnegative
    maximum_fault_a: Positive
    source_note: Text

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.minimum_fault_a > self.maximum_fault_a:
            raise ValueError("minimum fault current exceeds maximum fault current")
        return self


class BreakingEvidence(Document):
    capacity_a: Positive
    rated_voltage_v: Positive
    current_kind: Literal["ac", "dc"]
    source_note: Text


class DisconnectionEvidence(Document):
    device_worst_case_clear_s: Positive
    required_clear_s: Positive
    device_source_note: Text
    limit_source_note: Text


class ThermalEvidence(Document):
    run_id: Identifier
    core_role: Literal[
        "dc_positive", "dc_negative", "line", "neutral", "l1", "l2", "l3", "pe"
    ]
    maximum_let_through_a2s: Positive
    coverage_min_fault_a: Nonnegative
    coverage_max_fault_a: Positive
    maximum_clear_s: Positive
    k_a_sqrt_s_per_mm2: Positive
    k_source_note: Text
    let_through_source_note: Text

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.coverage_min_fault_a > self.coverage_max_fault_a:
            raise ValueError("thermal evidence fault range is reversed")
        return self


class ProtectionAssessment(Document):
    id: Identifier
    circuit_id: Identifier
    protection_material_id: Identifier | None
    operating_condition_id: Identifier | None
    scenario: Text
    fault_range: FaultRange | None
    breaking: BreakingEvidence | None
    disconnection: DisconnectionEvidence | None
    thermal: list[ThermalEvidence]
    confirmed_context_sha256: Hash | None

    @model_validator(mode="after")
    def distinct_thermal_targets(self) -> Self:
        keys = [(item.run_id, item.core_role) for item in self.thermal]
        if len(keys) != len(set(keys)):
            raise ValueError("thermal evidence targets must be distinct")
        return self
