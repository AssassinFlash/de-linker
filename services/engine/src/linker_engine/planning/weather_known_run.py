"""Read, stop or capture one acknowledged run; this module cannot start one."""

from __future__ import annotations

from .apify_run import TERMINAL, ApifyRun
from .apify_weather_client import ApifyWeatherClient
from .canonical import encode
from .errors import VersionUnavailable
from .pv_source import PvSource
from .weather_fetch_errors import (
    WeatherPollingLimit,
    WeatherProviderRejected,
    WeatherRemoteFailed,
)
from .weather_intent import WeatherIntent
from .weather_journal import WeatherJournal, WeatherStartUnknown
from .weather_task import WeatherTask


class KnownWeatherRun:
    def __init__(
        self,
        journal: WeatherJournal,
        client: ApifyWeatherClient,
        task: WeatherTask,
        intent: WeatherIntent,
    ) -> None:
        self.journal, self.client, self.task = journal, client, task
        self.intent = journal.current(intent)
        self.plan = journal.plan(self.intent)
        if encode(self.plan.limits.model_dump(mode="json")) != encode(
            client.transport.limits.model_dump(mode="json")
        ):
            raise VersionUnavailable("transport differs from the frozen weather limits")

    def current(self) -> ApifyRun:
        observed = self.journal.observation(self.intent)
        if observed is None:
            raise WeatherStartUnknown("issued start needs a verified provider identity")
        return observed

    def refresh(self) -> ApifyRun:
        self.task.check()
        observed = self.client.read(self.current().id, self.task.check)
        self.journal.observe(self.intent, observed)
        # An older HTTP response cannot erase an already retained terminal fact.
        return self.current()

    def terminal(self) -> ApifyRun:
        observed = self.current()
        polls = 0
        while observed.status not in TERMINAL:
            self.task.check()
            if polls >= self.plan.limits.max_polls:
                raise WeatherPollingLimit("weather polling budget exhausted")
            observed = self.refresh()
            polls += 1
            if observed.status not in TERMINAL:
                self.task.wait(self.plan.limits.poll_seconds)
        self.task.check()
        return observed

    def stop(self) -> ApifyRun:
        observed = self.current()
        if observed.status not in TERMINAL:
            observed = self.refresh()
            current = self.journal.current(self.intent)
            if observed.status not in TERMINAL and current.abort_sha256 is None:
                try:
                    # A late actual abort response remains evidence after lease loss.
                    reply = self.client.abort(observed.id, self.task.elapsed)
                    self.journal.abort_reply(self.intent, reply)
                except WeatherProviderRejected:
                    if self.refresh().status not in TERMINAL:
                        raise
        return self.terminal()

    def capture(self) -> PvSource:
        self.task.check()
        captured = self.journal.captured_source(self.intent)
        if captured is not None:
            return captured
        observed = self.terminal()
        if observed.status != "SUCCEEDED":
            raise WeatherRemoteFailed("the acknowledged weather run did not succeed")
        downloaded = self.client.download(
            observed, self.plan, self.intent.nonce, self.task.check
        )
        self.intent = self.journal.retain_capture(
            self.intent,
            downloaded.source,
            downloaded.retain_evidence(self.journal.workspace.blobs),
        )
        self.task.check()
        captured = self.journal.captured_source(self.intent)
        assert captured is not None
        return captured
