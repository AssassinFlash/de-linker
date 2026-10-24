"""Private weather launch uses explicit policy and never inherits model secrets."""

import pytest

from linker_local.planner_provider import NETWORK_NAMES, weather_environment
from linker_local.processes import ProcessError


def test_provider_and_network_policy_are_only_given_to_enabled_weather() -> None:
    environment = {
        "APIFY_TOKEN": "synthetic-weather-credential",
        "GENIE_SERVICE_TOKEN": "synthetic-service-credential",
        "DEEPSEEK_API_KEY": "synthetic-model-credential",
        "OPENROUTER_API_KEY": "synthetic-other-model-credential",
        **{name: "synthetic-network-setting" for name in NETWORK_NAMES},
    }
    for policy in ({}, {"weather_acquisition": None}):
        assert weather_environment(policy, environment) == {}
    selected = weather_environment({"weather_acquisition": {}}, environment)
    assert selected == {
        "APIFY_TOKEN": environment["APIFY_TOKEN"],
        **{name: environment[name] for name in NETWORK_NAMES},
    }
    assert environment["GENIE_SERVICE_TOKEN"] == "synthetic-service-credential"


@pytest.mark.parametrize("token", ["", "two words", "trailing\n", "\tleading"])
def test_bad_enabled_provider_credentials_fail_without_echoing_them(token: str) -> None:
    with pytest.raises(ProcessError, match="requires APIFY_TOKEN") as failure:
        weather_environment({"weather_acquisition": {}}, {"APIFY_TOKEN": token})
    if token:
        assert token not in str(failure.value)


@pytest.mark.parametrize("policy", [True, False, "enabled", []])
def test_malformed_weather_policy_is_not_an_enabled_executor(policy: object) -> None:
    with pytest.raises(ProcessError, match="policy is invalid"):
        weather_environment(
            {"weather_acquisition": policy}, {"APIFY_TOKEN": "synthetic-token"}
        )
