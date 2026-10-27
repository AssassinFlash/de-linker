"""A private, unit-labelled replay artifact independent of presentation locale."""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

from .canonical import Object, decode_object, encode
from .dispatch_frame import Flows


def flow_document(flow: Flows) -> Object:
    value = asdict(flow)
    value["frame"]["interval"] = {
        "start_utc": flow.frame.interval.start.isoformat(),
        "end_utc": flow.frame.interval.end.isoformat(),
    }
    # All other fields are declared numeric/unit-suffixed records. Canonical
    # encoding validates finite JSON and detaches nested dictionaries.
    return decode_object(encode(cast(Object, value)))
