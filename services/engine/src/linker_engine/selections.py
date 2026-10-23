"""Private confirmed results: later actions validate evidence, never reselect.

The existing native result receipts retain one day of retry data. This service
receipt uses that same boundary, stores no uploaded logo, and is not exposed by
an anonymous read route. A fingerprint alone never authorizes current use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from .models import CommercialResult, ResidentialResult
from .publication import digest


class Selections:
    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        self.path = directory / "selections.sqlite"
        with self.connect() as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS selections (fingerprint TEXT PRIMARY KEY, input_hash TEXT NOT NULL, kind TEXT NOT NULL, result TEXT NOT NULL, expires INTEGER NOT NULL)"
            )
        os.chmod(self.path, 0o600)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def remember(
        self, input_: dict[str, Any], result: ResidentialResult | CommercialResult
    ) -> None:
        with self.connect() as database:
            database.execute(
                "DELETE FROM selections WHERE expires < ?", (int(time.time()),)
            )
            database.execute(
                "INSERT OR REPLACE INTO selections VALUES (?, ?, ?, ?, ?)",
                (
                    result.selection_fingerprint,
                    digest(input_),
                    "residential"
                    if isinstance(result, ResidentialResult)
                    else "commercial",
                    result.model_dump_json(by_alias=True),
                    int(time.time()) + 24 * 60 * 60,
                ),
            )

    def read(
        self, input_: dict[str, Any], fingerprint: str, kind: str
    ) -> ResidentialResult | CommercialResult | None:
        with self.connect() as database:
            row = database.execute(
                "SELECT result FROM selections WHERE fingerprint=? AND input_hash=? AND kind=? AND expires>=?",
                (fingerprint, digest(input_), kind, int(time.time())),
            ).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return (
            ResidentialResult.model_validate(data)
            if kind == "residential"
            else CommercialResult.model_validate(data)
        )
