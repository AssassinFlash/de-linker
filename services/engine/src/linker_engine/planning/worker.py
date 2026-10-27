"""An explicit worker process executes leased jobs, independently of HTTP life."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping
from threading import Event, Thread

from .asset_publication import AssetResult
from .canonical import Object, encode
from .dependencies import verify_dependencies
from .errors import EvidenceMissing, InvalidInput, LeaseLost, PlanningError
from .execution_identity import EvaluationRouting
from .jobs import Jobs
from .records import JobKind, Lease

LOG = logging.getLogger(__name__)


class Control:
    """Long numerical loops use checkpoints to stop after cancellation/loss."""

    def __init__(self) -> None:
        self._lost = Event()

    def checkpoint(self) -> None:
        if self._lost.is_set():
            raise LeaseLost("execution no longer owns its publication lease")

    def revoke(self) -> None:
        self._lost.set()

    def wait(self, seconds: float) -> None:
        """Interrupt a provider polling wait when this execution loses authority."""
        if not math.isfinite(seconds) or seconds <= 0:
            raise InvalidInput("positive finite execution wait required")
        self.checkpoint()
        self._lost.wait(seconds)
        self.checkpoint()


type Executor = Callable[[Lease, Control], Object | AssetResult]


class RetryableExecution(PlanningError):
    """A known, explicitly classified transient source/transport failure."""

    code = "source_unavailable"


class Worker:
    """Registered handlers only; lifecycle policy is explicit deployment config."""

    def __init__(
        self,
        jobs: Jobs,
        name: str,
        handlers: Mapping[JobKind, Executor],
        *,
        lease_seconds: float,
        heartbeat_seconds: float,
        retry_seconds: float,
        routing: EvaluationRouting | None = None,
    ) -> None:
        if not name.strip() or not handlers:
            raise InvalidInput("worker identity and registered handlers required")
        if (
            any(
                not math.isfinite(value) or value <= 0
                for value in (lease_seconds, heartbeat_seconds, retry_seconds)
            )
            or heartbeat_seconds >= lease_seconds
        ):
            raise InvalidInput("positive heartbeat shorter than lease required")
        self.jobs = jobs
        self.name = name
        self.handlers = dict(handlers)
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.retry_seconds = retry_seconds
        self.routing = routing

    def _renew(self, lease: Lease, stop: Event, control: Control) -> None:
        while not stop.wait(self.heartbeat_seconds):
            try:
                self.jobs.heartbeat(lease, lease_seconds=self.lease_seconds)
            except Exception:
                # A database outage also makes ownership uncertain. Do not
                # continue publishing on a guessed or stale execution lease.
                control.revoke()
                LOG.exception("planning heartbeat lost for job %s", lease.id)
                return

    def run_once(self) -> bool:
        lease = self.jobs.claim(
            self.name,
            kinds=tuple(self.handlers),
            lease_seconds=self.lease_seconds,
            routing=self.routing,
        )
        if lease is None:
            return False
        stop = Event()
        control = Control()
        heartbeat = Thread(
            target=self._renew,
            args=(lease, stop, control),
            name=f"planning-lease-{lease.id}",
            daemon=True,
        )
        heartbeat.start()
        output: Object | None = None
        prepared: AssetResult | None = None
        failure: Object | None = None
        retry_after: float | None = None
        try:
            reply = self.handlers[lease.kind](lease, control)
            if isinstance(reply, AssetResult):
                prepared = reply
                output = reply.result
            else:
                output = reply
            if not isinstance(output, dict):
                raise InvalidInput("executor result must be a JSON object")
            encode(output)
            verify_dependencies(self.jobs.workspace.blobs, output)
            control.checkpoint()
        except LeaseLost:
            control.revoke()
        except RetryableExecution as error:
            failure = {"code": error.code, "retryable": True}
            retry_after = self.retry_seconds
        except PlanningError as error:
            failure = {"code": error.code, "retryable": False}
            if isinstance(error, EvidenceMissing) and error.public_details:
                # The error constructor admits only canonical public IDs.
                # Exception messages and operational details remain private.
                failure["details"] = {
                    key: value for key, value in error.public_details.items()
                }
        except Exception:
            # Traceback goes to private operational logs, not customer result
            # JSON. Unexpected programming errors do not become fake results.
            LOG.exception("planning execution failed for job %s", lease.id)
            failure = {"code": "execution_failed", "retryable": False}
        finally:
            stop.set()
            heartbeat.join()
        try:
            control.checkpoint()
            if failure is not None:
                self.jobs.fail(lease, failure, retry_after=retry_after)
            elif output is not None:
                self.jobs.complete(
                    lease,
                    output,
                    asset=prepared.asset if prepared is not None else None,
                    attachments=prepared.attachments if prepared is not None else None,
                )
        except LeaseLost:
            # Cancellation/another worker wins; no result or failure is written
            # over its state. A lost heartbeat leaves durable retry recovery.
            LOG.info("planning publication fenced for job %s", lease.id)
        except PlanningError as error:
            # A malformed prepared publication is a named task failure, not a
            # success or an unbounded lease-recovery loop. The same lease fence
            # still decides whether this attempt may publish that failure.
            try:
                self.jobs.fail(
                    lease, {"code": error.code, "retryable": False}, retry_after=None
                )
            except LeaseLost:
                LOG.info("planning publication failure fenced for job %s", lease.id)
        return True
