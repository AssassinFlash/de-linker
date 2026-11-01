"""Typed lifecycle failures; transport adapters map them without exposing other owners."""

import re


class PlanningError(Exception):
    """A recoverable, named planning operation failure."""

    code = "planning_error"


class NotFound(PlanningError):
    """Missing and unauthorised references have the same public response."""

    code = "not_found"


class Conflict(PlanningError):
    """A revision, idempotency key or immutable record conflicts."""

    code = "conflict"


class EvaluationRevisionChanged(Conflict):
    """A new evaluation was refused before writing a run or receipt."""

    code = "evaluation_revision_changed"


class ProductEvidenceChanged(Conflict):
    """A new action was refused because its current Woo evidence changed."""

    code = "product_evidence_changed"


class LeaseLost(PlanningError):
    """This worker can no longer publish or renew this attempt."""

    code = "lease_lost"


class VersionUnavailable(PlanningError):
    """Pinned bytes or a supported schema version cannot be read."""

    code = "version_unavailable"


class ServiceDraining(PlanningError):
    """An operator closed new evaluation admission while preserving old work."""

    code = "service_draining"


class InvalidInput(PlanningError):
    """The command is not finite JSON or has an invalid lifecycle parameter."""

    code = "invalid_input"


class ReportSourceExportRequired(InvalidInput):
    """A source retained by the report does not permit export."""

    code = "report_source_export_required"


class ProjectInputContractRequired(InvalidInput):
    """An unaware editor was refused before replacing complete project inputs."""

    code = "project_input_contract_required"


class NumericalFailure(PlanningError):
    """A calculation produced values outside finite numerical representation."""

    code = "numerical_failure"


class EvidenceMissing(PlanningError):
    """A requested physical path lacks explicit supporting parameters."""

    code = "evidence_missing"

    def __init__(
        self,
        message: str,
        *,
        product_id: int | None = None,
        fact_id: str | None = None,
        constraint_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.public_details: dict[str, str | int] = {}
        if product_id is not None:
            if type(product_id) is not int or product_id <= 0:
                raise ValueError(
                    "public evidence product ID must be a positive integer"
                )
            self.public_details["product_id"] = product_id
        for key, value in (("fact_id", fact_id), ("constraint_id", constraint_id)):
            if value is not None:
                if not re.fullmatch(r"[a-z][a-z0-9_.:-]*", value):
                    raise ValueError(
                        "public evidence identity must be a canonical field/constraint ID"
                    )
                self.public_details[key] = value


class MethodDomainExceeded(PlanningError):
    """The requested physical topology/mode is outside this model's domain."""

    code = "method_domain_exceeded"
