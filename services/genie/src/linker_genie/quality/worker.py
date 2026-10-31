"""The quality worker: `python -m linker_genie.quality.worker`.

Each cycle takes the turns the service logged since the last one (and the
failed turns due for a retry), judges each with the Jev -> deepseek-flash
cascade, checks its citations, keeps the verdict, and hands everything
WordPress has not stored yet to the site. It runs as its own systemd unit
beside the service (services/genie/ops/linker-genie-judge.service) and
never touches the answer path.

Every failure is loud: a judge call that failed after its retries is logged
at ERROR, recorded on the turn as `failed`, retried on later cycles, and
reported to the site, which shows it in the admin and the daily digest. A
failed Jev call is never handed to deepseek-flash instead (AGENTS.md §5).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linker_judges.cascade import Cascade, run_cascade
from linker_judges.http import HttpError, deepseek_credentials, openrouter_credentials
from linker_judges.judges import Judge
from linker_judges.registry import JUDGES
from linker_judges.turns import TURN_THRESHOLDS, turns_questions

from linker_genie.quality import citations
from linker_genie.quality.item import Skip, build
from linker_genie.quality.store import Status, Store
from linker_genie.quality.turns import LoggedTurn, TurnSource
from linker_genie.quality.wordpress import PushError, WordPress
from linker_genie.retention import judgments_path

log = logging.getLogger("linker_genie.quality")

# Seconds between cycles. The ticket's bar is a verdict "within minutes" of a
# new turn: a 30 s poll plus one cascade (Jev 3-6 s, measured in
# docs/specs/33-judge-bakeoff.md; an escalation adds deepseek-flash's reply)
# puts it well inside that.
POLL_SECONDS = 30.0
# Turns taken from the log per cycle: twenty cascades at the worst case of
# ~20 s each stays under the ten minutes a heartbeat may lag (below).
BATCH = 20
# Attempts per turn before it is given up and stays `failed`: the judges'
# own HTTP layer already retries each call three times (linker_judges.http,
# MAX_ATTEMPTS, after the JEV-as-a-Judge protocol); three cycles of that,
# RETRY_AFTER apart, ride out a provider outage of half an hour.
MAX_ATTEMPTS = 3
RETRY_AFTER_SECONDS = 600.0
# Seconds between status reports when no verdict is due. The site reads a
# report older than three of these as a stopped worker (Genie/Quality.php,
# STALE_AFTER), so a dead worker is visible within half an hour.
HEARTBEAT_SECONDS = 600.0
# Verdicts per push: a handful of KB each, so one request stays small.
PUSH_BATCH = 50
# Characters of question and answer the site keeps beside a verdict; the
# whole thread is on the conversation itself.
QUESTION_CHARS = 1000
ANSWER_CHARS = 4000

FIRST = JUDGES["jev"]
ESCALATION = JUDGES["deepseek"]


@dataclass
class Worker:
    source: TurnSource
    store: Store
    site: WordPress
    first: Judge = FIRST
    escalation: Judge = ESCALATION
    last_report: float = 0.0

    def cycle(self, now: float) -> int:
        """One pass over the queue; returns how many turns it judged or skipped."""
        start = self.store.cursor()
        if start is None:
            start = self.source.latest_id()
            self.store.set_cursor(start)
        due = self.source.by_ids(
            self.store.retryable(MAX_ATTEMPTS, now - RETRY_AFTER_SECONDS)
        )
        fresh = self.source.after(start, BATCH)
        for turn in due:
            self._judge(turn, now)
        for turn in fresh:
            self._judge(turn, now)
            # Advanced per turn, so a restart mid-batch takes up where it was.
            self.store.set_cursor(turn.id)
        self._push(now, force=bool(due or fresh))
        return len(due) + len(fresh)

    def _judge(self, turn: LoggedTurn, now: float) -> None:
        attempts = self.store.attempts(turn.id) + 1
        status, record = judge_turn(turn, self.first, self.escalation)
        record["attempts"] = attempts
        if status == "failed":
            log.error(
                "turn %d (conversation %s) not judged, attempt %d of %d: %s",
                turn.id,
                turn.conversation_id,
                attempts,
                MAX_ATTEMPTS,
                record["error"],
            )
        elif status == "skipped":
            log.info("turn %d skipped: %s", turn.id, record["skip_reason"])
        else:
            if record["escalated"]:
                log.info(
                    "turn %d escalated to %s: %s",
                    turn.id,
                    self.escalation.model,
                    "; ".join(record["escalation"]),
                )
            log.info(
                "turn %d judged %s%s",
                turn.id,
                record["labels"],
                " FLAGGED " + ",".join(record["flags"]) if record["flagged"] else "",
            )
        self.store.save(turn.id, turn.conversation_id, status, attempts, record, now)

    def _push(self, now: float, force: bool) -> None:
        pending = self.store.unpushed(PUSH_BATCH)
        if not pending and not force and now - self.last_report < HEARTBEAT_SECONDS:
            return
        try:
            stored = self.site.push(pending, self.status(now))
        except PushError as error:
            # The verdicts stay unpushed and go again next cycle.
            log.error(
                "could not hand %d verdict(s) to the site: %s", len(pending), error
            )
            return
        self.store.mark_pushed(stored)
        self.last_report = now
        missing = {int(row["turn_id"]) for row in pending} - set(stored)
        if missing:
            log.error("the site refused verdict(s) for turn(s) %s", sorted(missing))

    def status(self, now: float) -> dict[str, Any]:
        counts = self.store.counts(MAX_ATTEMPTS)
        failure = self.store.last_failure()
        return {
            "at": _iso(now),
            "judge": f"{self.first.model} (OpenRouter)",
            "escalation": f"{self.escalation.model} (api.deepseek.com)",
            "retrying": counts["retrying"],
            "gave_up": counts["gave_up"],
            "last_error": failure[0] if failure else None,
            "last_error_at": _iso(failure[1]) if failure else None,
        }


def judge_turn(
    turn: LoggedTurn, first: Judge, escalation: Judge
) -> tuple[Status, dict[str, Any]]:
    """One turn's verdict and the record the site stores."""
    record: dict[str, Any] = {
        "turn_id": turn.id,
        "conversation_id": turn.conversation_id,
        "turn_at": turn.created_at,
        "judged_at": _iso(time.time()),
        "locale": turn.locale,
        "question": (turn.question or "")[:QUESTION_CHARS],
        "fallback": turn.fallback,
        "error": None,
        "skip_reason": None,
    }
    try:
        item = build(turn)
    except Skip as skip:
        record.update(status="skipped", skip_reason=str(skip), flagged=False, flags=[])
        return "skipped", record

    failures = citations.verify(turn)
    questions = turns_questions(item.swap is not None)
    cascade = run_cascade(item.state, first, escalation, questions)
    record.update(
        answer=item.answer[:ANSWER_CHARS],
        cards=item.cards,
        page_product=item.page_product,
        swap=list(item.swap) if item.swap else None,
        labels=cascade.labels,
        sources=cascade.sources,
        confidence={
            name: answer.confidence for name, answer in cascade.first.answers.items()
        },
        escalated=cascade.escalated,
        escalation=_shortfalls(cascade),
        reasons={
            first.name: cascade.first.reason,
            escalation.name: cascade.fallback.reason if cascade.fallback else None,
        },
        citations=citations.summary(failures),
        cost_usd=round(
            cascade.first.cost_usd
            + (cascade.fallback.cost_usd if cascade.fallback else 0.0),
            6,
        ),
    )
    if cascade.error:
        provider = "OpenRouter" if cascade.first.error else "api.deepseek.com"
        record.update(
            status="failed",
            error=f"{provider}: {cascade.error}",
            flagged=False,
            flags=[],
        )
        return "failed", record
    flags = flags_for(cascade.labels, failures)
    record.update(status="judged", flags=flags, flagged=bool(flags))
    return "judged", record


def flags_for(
    labels: Mapping[str, str | None], citation_failures: list[str]
) -> list[str]:
    """Why a judged turn needs a person's look; empty when it does not.

    The three rubric questions (linker_judges.rubric) and the citation check:
    an answer is fine when it is supported (`grounded` 2), within the remit,
    not beaten by the wrong pick, and cites nothing its tools did not return.
    """
    flags: list[str] = []
    grounded = labels.get("grounded")
    if grounded == "0":
        flags.append("contradicted")
    elif grounded == "1":
        flags.append("unverifiable")
    if labels.get("appropriate") == "no":
        flags.append("out_of_remit")
    if labels.get("better_pick") == "B":
        flags.append("worse_pick")
    if citation_failures:
        flags.append("citation")
    if any(label is None for label in labels.values()):
        flags.append("unresolved")
    return flags


def _shortfalls(cascade: Cascade) -> list[str]:
    """`grounded 0.42 < 0.6`: why each question went to the escalation judge."""
    lines = []
    for name in cascade.short:
        confidence = cascade.first.answers[name].confidence
        shown = "none" if confidence is None else f"{confidence:.2f}"
        lines.append(f"{name} {shown} < {TURN_THRESHOLDS[name]}")
    return lines


def _iso(stamp: float) -> str:
    return datetime.fromtimestamp(stamp, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_log() -> Path:
    # The service's own default (linker_genie.app._log_path), so both read
    # GENIE_LOG the same way.
    return Path(
        os.environ.get(
            "GENIE_LOG", str(Path.home() / ".cache" / "linker-genie" / "turns.sqlite")
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="judge live Genie turns")
    parser.add_argument("--log", type=Path, default=_default_log(), help="turn log")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="the worker's store (GENIE_JUDGMENTS or judgments.sqlite beside the log)",
    )
    parser.add_argument("--wp", default=os.environ.get("GENIE_WP_URL", ""))
    parser.add_argument("--once", action="store_true", help="one cycle, then exit")
    parser.add_argument(
        "--backfill",
        type=int,
        default=0,
        help="on the very first start, also judge this many turns already logged",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    # httpx logs every request at INFO: a heartbeat every ten minutes would
    # bury the worker's own lines in the journal. Its warnings still show.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    token = os.environ.get("GENIE_JUDGE_TOKEN", "")
    if not args.wp or not token:
        log.error("GENIE_WP_URL and GENIE_JUDGE_TOKEN must be set; not starting")
        return 2
    try:
        openrouter_credentials()
        deepseek_credentials()
    except HttpError as error:
        log.error("judge credentials missing; not starting: %s", error)
        return 2

    store = Store(args.db or judgments_path(args.log))
    source = TurnSource(args.log)
    if store.cursor() is None:
        store.set_cursor(max(source.latest_id() - max(args.backfill, 0), 0))
    worker = Worker(source, store, WordPress(args.wp, token))
    log.info(
        "judging %s from turn %d: %s first, %s on escalation",
        args.log,
        store.cursor() or 0,
        worker.first.model,
        worker.escalation.model,
    )
    while True:
        worker.cycle(time.time())
        if args.once:
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
