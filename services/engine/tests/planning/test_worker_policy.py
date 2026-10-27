"""Worker policy is explicit and strict at the operator boundary."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from linker_engine.planning.worker_policy import WorkerPolicy


def policy(tmp_path: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "synthetic-operator",
        "lease_seconds": 30,
        "heartbeat_seconds": 5,
        "retry_seconds": 2,
        "poll_seconds": 0.5,
        "routing_batch_size": 128,
        "drain_timeout_seconds": 30,
        "ready_file": str(tmp_path / "ready.json"),
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("name", " "),
        ("name", " padded "),
        ("lease_seconds", 0),
        ("heartbeat_seconds", 30),
        ("retry_seconds", "2"),
        ("poll_seconds", True),
        ("routing_batch_size", 1.5),
        ("routing_batch_size", False),
        ("drain_timeout_seconds", float("inf")),
        ("ready_file", "relative.json"),
        ("unknown", "rejected"),
    ],
)
def test_invalid_operator_policy_is_refused(
    tmp_path: Path, field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        WorkerPolicy.model_validate({**policy(tmp_path), field: value})


def test_no_policy_default_is_inferred(tmp_path: Path) -> None:
    values = policy(tmp_path)
    for field in values:
        with pytest.raises(ValidationError):
            WorkerPolicy.model_validate({k: v for k, v in values.items() if k != field})
    assert WorkerPolicy.model_validate(values).name == "synthetic-operator"
