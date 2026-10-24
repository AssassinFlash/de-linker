"""Allow only the weather executor's explicitly enabled provider environment."""

from __future__ import annotations

import os
from collections.abc import Mapping

from .processes import ProcessError

# requests.Session.merge_environment_settings, used by ApifyTransport, reads
# these proxy and CA variables. They are network policy, never source/model
# facts. No service/model credential belongs in this allowlist.
NETWORK_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
)


def weather_environment(
    policy: Mapping[str, object], environ: Mapping[str, str] = os.environ
) -> dict[str, str]:
    if policy.get("weather_acquisition") is None:
        return {}
    if not isinstance(policy["weather_acquisition"], dict):
        raise ProcessError("local weather acquisition policy is invalid")
    token = environ.get("APIFY_TOKEN", "")
    # Same credential-shape contract as planning.apify_transport; never print
    # the supplied value or place it in command arguments/policy files.
    if not token or any(character.isspace() for character in token):
        raise ProcessError("enabled local weather execution requires APIFY_TOKEN")
    return {
        "APIFY_TOKEN": token,
        **{name: environ[name] for name in NETWORK_NAMES if name in environ},
    }
