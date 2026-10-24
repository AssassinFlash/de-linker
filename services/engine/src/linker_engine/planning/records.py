"""Value records shared by the private workspace and its execution worker."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .canonical import Object, decode_object, encode
from .errors import InvalidInput

type ActorKind = Literal["guest", "user", "team"]
type JobKind = Literal["evaluate", "render_report", "abort_weather"]
type JobState = Literal[
    "queued", "running", "retry_wait", "succeeded", "failed", "cancelled"
]


@dataclass(frozen=True)
class Actor:
    """A subject already verified by the server-side identity adapter.

    Constructing this value is not authentication. HTTP callers never choose
    this object or a project owner; the private gateway verifies them first.
    """

    kind: ActorKind
    subject: str

    def __post_init__(self) -> None:
        if self.kind not in ("guest", "user", "team") or not self.subject.strip():
            raise InvalidInput("verified subject required")

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.subject}"


@dataclass(frozen=True)
class Context:
    """Resolved dependencies; assets map names to existing content hashes."""

    code_sha256: str
    models: dict[str, str]
    assets: dict[str, str]
    parameters: Object

    def document(self) -> Object:
        if not re.fullmatch(r"[a-f0-9]{64}", self.code_sha256):
            raise InvalidInput("code SHA-256 required")
        if not self.models or any(
            not key.strip() or not value.strip() for key, value in self.models.items()
        ):
            raise InvalidInput("named model versions required")
        if any(
            not key.strip() or not re.fullmatch(r"[a-f0-9]{64}", value)
            for key, value in self.assets.items()
        ):
            raise InvalidInput("named pinned assets required")
        # Detach the document from mutable caller dictionaries before hashing.
        return decode_object(
            encode(
                {
                    "code_sha256": self.code_sha256,
                    "models": dict(self.models),
                    "assets": dict(self.assets),
                    "parameters": self.parameters,
                }
            )
        )


@dataclass(frozen=True)
class Project:
    id: str
    title: str
    revision: int
    input_sha256: str
    inputs: Object
    owner: str


@dataclass(frozen=True)
class Run:
    id: str
    project_id: str
    revision: int
    state: JobState
    manifest_sha256: str
    manifest: Object
    result_sha256: str | None
    result: Object | None
    error: Object | None
    is_current: bool


@dataclass(frozen=True)
class Lease:
    id: str
    run_id: str
    kind: JobKind
    attempt: int
    worker: str
    token: str
    until: float
    request: Object


@dataclass(frozen=True)
class Handoff:
    id: str
    project_id: str
    run_id: str
    revision: int
    candidate_id: str
    snapshot_sha256: str
    snapshot: Object
