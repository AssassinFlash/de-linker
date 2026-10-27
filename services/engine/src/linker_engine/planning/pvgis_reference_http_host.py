"""IPC-only entry point; its parent enforces DNS/TLS/body absolute deadlines."""

import sys
import time

from .canonical import decode_object, encode
from .errors import PlanningError
from .pvgis_reference_http import PvgisReferenceHttp
from .pvgis_request import PvgisRequest
from .weather_fetch_plan import WeatherFetchLimits


def main() -> None:
    document = decode_object(sys.argv[1].encode())
    request = PvgisRequest.read(document.get("request"))
    limits = WeatherFetchLimits.read(document.get("limits"))
    deadline = time.time() + min(float(sys.argv[2]), limits.max_elapsed_seconds)
    transfer = PvgisReferenceHttp()
    try:
        result = transfer.download(
            request, limits, deadline=deadline, clock=time.time, guard=lambda: None
        )
        header = encode({"schema_version": 1, "capture": result.capture.document()})
        sys.stdout.buffer.write(header + b"\n" + result.content)
        sys.stdout.buffer.flush()
    except PlanningError as error:
        sys.stdout.buffer.write(
            encode({"schema_version": 1, "error": error.code}) + b"\n"
        )
        sys.stdout.buffer.flush()
    finally:
        transfer.close()


if __name__ == "__main__":
    main()
