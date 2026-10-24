"""Selected, credential-free provider facts from a pinned Actor run."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Json, Object
from .energy_inputs import Document
from .errors import InvalidInput
from .interval import utc
from .weather_fetch_plan import ACTOR_ID, BUILD_ID, BUILD_NUMBER

type ProviderId = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9]+$")]
type RemoteStatus = Literal[
    "READY",
    "RUNNING",
    "TIMING-OUT",
    "ABORTING",
    "SUCCEEDED",
    "FAILED",
    "TIMED-OUT",
    "ABORTED",
]
TERMINAL = frozenset(("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"))


class ApifyRun(Document):
    id: ProviderId
    actor_id: ProviderId
    build_id: ProviderId
    build_number: str
    status: RemoteStatus
    dataset_id: ProviderId
    store_id: ProviderId
    started_at: str
    finished_at: str | None

    @classmethod
    def from_provider(cls, value: Json) -> ApifyRun:
        if not isinstance(value, dict):
            raise InvalidInput("provider run response must be an object")
        names = {
            "id": "id",
            "actor_id": "actId",
            "build_id": "buildId",
            "build_number": "buildNumber",
            "status": "status",
            "dataset_id": "defaultDatasetId",
            "store_id": "defaultKeyValueStoreId",
            "started_at": "startedAt",
            "finished_at": "finishedAt",
        }
        # Ignore account, billing and temporary access data; retain no secret.
        return cls.read({name: value.get(key) for name, key in names.items()})

    @model_validator(mode="after")
    def pinned(self) -> Self:
        if (self.actor_id, self.build_id, self.build_number) != (
            ACTOR_ID,
            BUILD_ID,
            BUILD_NUMBER,
        ):
            raise ValueError("provider run does not match the pinned Actor build")
        start = utc(datetime.fromisoformat(self.started_at))
        if (
            self.finished_at is not None
            and utc(datetime.fromisoformat(self.finished_at)) < start
        ):
            raise ValueError("provider run finish precedes its start")
        if self.status in TERMINAL and self.finished_at is None:
            raise ValueError("terminal provider run requires its finish time")
        return self

    def identity(self) -> tuple[str, ...]:
        return (
            self.id,
            self.actor_id,
            self.build_id,
            self.build_number,
            self.dataset_id,
            self.store_id,
        )

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}
