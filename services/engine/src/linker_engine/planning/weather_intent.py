"""A frozen local download operation; no external job or start permit."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherIntent:
    run_id: str
    manifest_sha256: str
    plan_sha256: str
    deadline_at: float
    capture_sha256: str | None
