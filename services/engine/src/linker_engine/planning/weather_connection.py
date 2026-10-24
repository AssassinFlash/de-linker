"""Private provider credential binding, separate from numerical executors."""

from __future__ import annotations

import os

from .apify_transport import ApifyTransport
from .weather_fetch_plan import WeatherFetchLimits


def apify_credential() -> str:
    # Deployment injects this value. It never enters a frozen policy or source.
    return os.environ.get("APIFY_TOKEN", "")


def weather_connection(limits: WeatherFetchLimits) -> ApifyTransport:
    return ApifyTransport(apify_credential, limits)
