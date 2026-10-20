from __future__ import annotations

from redact import redact


def test_redact_strips_token_shapes() -> None:
    cleaned = redact(
        {
            "token": "abc",
            "note": "Bearer secret-value and " + "a" * 64,
            "turn_id": 12,
        }
    )
    assert cleaned["token"] == "[redacted]"
    assert "Bearer" not in cleaned["note"]
    assert "a" * 64 not in cleaned["note"]
    assert cleaned["turn_id"] == 12
