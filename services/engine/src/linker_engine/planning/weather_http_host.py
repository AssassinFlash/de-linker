"""Private HTTP child; no workspace, customer authentication or R&D account."""

from __future__ import annotations

import os
import sys
import time
from threading import Timer

from .canonical import decode_object, encode
from .errors import PlanningError
from .pvgis_http_transfer import PvgisHttpTransfer
from .weather_fetch_plan import WeatherFetchPlan
from .weather_journal import WeatherDeadlineExceeded


def main() -> int:
    plan = WeatherFetchPlan.from_document(decode_object(sys.argv[1].encode()))
    remaining = float(sys.argv[2])
    if not 0 < remaining <= plan.limits.max_elapsed_seconds:
        raise ValueError("bounded positive weather transfer time required")
    deadline = time.time() + remaining

    def guard() -> None:
        if time.time() >= deadline:
            raise WeatherDeadlineExceeded("weather transfer deadline has passed")

    # The parent supervises cancellation and the original deadline. This child
    # also exits at its own monotonic Timer bound if the parent dies mid-read.
    # os._exit is confined to this disposable HTTP process, never the worker.
    watchdog = Timer(remaining, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    transfer = PvgisHttpTransfer()
    try:
        try:
            result = transfer.download(
                plan, deadline=deadline, clock=time.time, guard=guard
            )
            header = encode(
                {
                    "schema_version": 1,
                    "capture": result.source.capture.document(),
                    "provenance": decode_object(result.source.provenance_json),
                }
            )
            if len(header) > plan.limits.max_metadata_bytes:
                raise ValueError("weather receipt exceeds metadata budget")
            sys.stdout.buffer.write(header + b"\n")
            sys.stdout.buffer.write(result.source.content)
        except PlanningError as error:
            sys.stdout.buffer.write(
                encode({"schema_version": 1, "error": error.code}) + b"\n"
            )
        sys.stdout.buffer.flush()
        return 0
    finally:
        transfer.close()
        watchdog.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
