"""Named provider failures; private response bodies never become user errors."""

from .errors import InvalidInput, PlanningError
from .worker import RetryableExecution


class WeatherProviderUnavailable(RetryableExecution):
    code = "weather_provider_unavailable"


class WeatherProviderRejected(PlanningError):
    code = "weather_provider_rejected"


class WeatherResponseInvalid(InvalidInput):
    code = "weather_response_invalid"


class WeatherResponseTooLarge(InvalidInput):
    code = "weather_response_too_large"


class WeatherRemoteFailed(PlanningError):
    code = "weather_remote_failed"


class WeatherPollingLimit(PlanningError):
    code = "weather_polling_limit"
