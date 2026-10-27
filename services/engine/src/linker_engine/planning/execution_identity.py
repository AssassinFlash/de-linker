"""A worker identity excludes customer assets but includes executable settings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .access import positive_integer
from .canonical import Object, digest, encode
from .errors import InvalidInput, VersionUnavailable


def storage_binding(database_path: Path) -> str:
    """Operational agreement on one live store; not an input/model identity."""
    return digest(str(database_path.resolve(strict=True)).encode("utf-8"))


def execution_key(context: Object) -> str:
    code = context.get("code_sha256")
    models = context.get("models")
    parameters = context.get("parameters")
    if (
        not isinstance(code, str)
        or re.fullmatch(r"[a-f0-9]{64}", code) is None
        or not isinstance(models, dict)
        or not models
        or any(
            not key.strip() or not isinstance(value, str) or not value.strip()
            for key, value in models.items()
        )
        or not isinstance(parameters, dict)
    ):
        raise VersionUnavailable("evaluation execution identity is unavailable")
    return digest(
        encode(
            {
                "code_sha256": code,
                "models": models,
                "parameters": parameters,
            }
        )
    )


@dataclass(frozen=True)
class EvaluationRouting:
    key: str
    batch_size: int
    compatible_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str)
            or re.fullmatch(r"[a-f0-9]{64}", self.key) is None
        ):
            raise InvalidInput("evaluation execution key required")
        positive_integer(self.batch_size, "routing batch size")
        try:
            object.__setattr__(self, "compatible_keys", tuple(self.compatible_keys))
        except TypeError as error:
            raise InvalidInput("compatible execution hashes required") from error
        if any(
            not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None
            for value in self.compatible_keys
        ) or len(set(self.compatible_keys)) != len(self.compatible_keys):
            raise InvalidInput("unique compatible execution hashes required")

    @property
    def execution_keys(self) -> tuple[str, ...]:
        return self.compatible_keys or (self.key,)


def request_execution_key(
    request: Object, manifest: Object, expected_manifest: str
) -> str:
    if request.get("manifest_sha256") != expected_manifest:
        raise VersionUnavailable("job and run reference different manifests")
    context = manifest.get("context")
    if not isinstance(context, dict):
        raise VersionUnavailable("evaluation manifest has no execution context")
    return execution_key(context)
