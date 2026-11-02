"""Explicit operator lifecycle policy; none of these values model equipment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion

type Duration = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Count = Annotated[int, Field(strict=True, gt=0)]


class ExpandedJobPolicy(Document):
    """Per-job bounds limited to the measured single-core host envelope."""

    cpu_quota_percent: Annotated[int, Field(strict=True, gt=0, le=20)]
    memory_max_bytes: Annotated[int, Field(strict=True, gt=0, le=1258291200)]
    minimum_available_bytes: Annotated[int, Field(strict=True, ge=1610612736)]
    timeout_seconds: Annotated[float, Field(gt=0, le=600, allow_inf_nan=False)]
    health_ports: tuple[
        Annotated[int, Field(strict=True, ge=1, le=65535)],
        Annotated[int, Field(strict=True, ge=1, le=65535)],
    ]

    @model_validator(mode="after")
    def distinct_health_ports(self) -> Self:
        if self.health_ports[0] == self.health_ports[1]:
            raise ValueError("two distinct health endpoints required")
        return self


class WorkerPolicy(Document):
    schema_version: SchemaVersion
    # Operator labels share the private command-key transport bound, not a
    # physical limit (http_documents.Key; 548-managed-energy-worker.md).
    name: Annotated[str, Field(min_length=1, max_length=256)]
    lease_seconds: Duration
    heartbeat_seconds: Duration
    retry_seconds: Duration
    poll_seconds: Duration
    routing_batch_size: Count
    drain_timeout_seconds: Duration
    ready_file: str
    expanded_job: ExpandedJobPolicy | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.name != self.name.strip() or not self.name:
            raise ValueError("worker name must be nonblank without surrounding space")
        if self.heartbeat_seconds >= self.lease_seconds:
            raise ValueError("heartbeat must be shorter than the lease")
        if not Path(self.ready_file).is_absolute():
            raise ValueError("readiness path must be absolute")
        return self

    @classmethod
    def from_environment(cls) -> Self:
        name = os.environ.get("LINKER_PLANNER_WORKER_CONFIG", "")
        if not name:
            raise ValueError("worker configuration is absent")
        return cls.model_validate_json(Path(name).read_bytes())
