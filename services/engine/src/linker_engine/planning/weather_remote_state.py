"""Last verified remote facts, read in the same snapshot as local queue state."""

from __future__ import annotations

import sqlite3

from .apify_run import TERMINAL, ApifyRun
from .errors import VersionUnavailable
from .storage import Blobs


def remote_weather_state(
    connection: sqlite3.Connection, blobs: Blobs
) -> dict[str, int]:
    counts = {"unknown": 0, "active": 0, "terminal": 0}
    for row in connection.execute(
        "SELECT remote_run_id,observation_sha256 FROM weather_acquisitions WHERE post_claimed=1"
    ):
        if row["observation_sha256"] is None:
            counts["unknown"] += 1
        else:
            observed = ApifyRun.read(blobs.object(row["observation_sha256"]))
            if observed.id != row["remote_run_id"]:
                raise VersionUnavailable(
                    "weather observation differs from its acknowledged identity"
                )
            counts["terminal" if observed.status in TERMINAL else "active"] += 1
    return {**counts, "unresolved": counts["unknown"] + counts["active"]}
