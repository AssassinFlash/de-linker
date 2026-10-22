"""Typed lifecycle failures; transport adapters map them without exposing other owners."""


class PlanningError(Exception):
    """A recoverable, named planning operation failure."""

    code = "planning_error"


class NotFound(PlanningError):
    """Missing and unauthorised references have the same public response."""

    code = "not_found"


class Conflict(PlanningError):
    """A revision, idempotency key or immutable record conflicts."""

    code = "conflict"


class LeaseLost(PlanningError):
    """This worker can no longer publish or renew this attempt."""

    code = "lease_lost"


class VersionUnavailable(PlanningError):
    """Pinned bytes or a supported schema version cannot be read."""

    code = "version_unavailable"


class InvalidInput(PlanningError):
    """The command is not finite JSON or has an invalid lifecycle parameter."""

    code = "invalid_input"
