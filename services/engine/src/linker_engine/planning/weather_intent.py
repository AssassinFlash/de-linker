"""A private start permit; it records an external effect, never publication rights."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherIntent:
    run_id: str
    manifest_sha256: str
    plan_sha256: str
    nonce: str
    deadline_at: float
    may_start: bool
    remote_run_id: str | None
    acknowledgement_sha256: str | None
    observation_sha256: str | None
    capture_sha256: str | None
    abort_sha256: str | None
