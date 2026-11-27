"""Evaluate the manufacturer's golden questions against current Woo sale permissions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from index.eval.goldset import Question
from linker_genie.knowledge import KnowledgeSearch
from linker_genie.publication import PublicationChanged, PublicationClient, Snapshot
from linker_genie.retrieval import DocumentIndex


@dataclass
class Case:
    id: str
    model: str
    model_status: str
    withdrawn_models: list[str]
    refused: bool | None = None


def require_same_source(index: DocumentIndex, snapshot: Snapshot) -> None:
    if (
        not snapshot.source_revision
        or not snapshot.model_identity_revision
        or snapshot.source_revision != index.source_revision
        or snapshot.model_identity_revision != index.model_identity_revision
    ):
        raise PublicationChanged("evaluated index and current Woo publication differ")


def publication_cases(
    questions: Sequence[Question],
    authority: PublicationClient,
    snapshot: Snapshot,
    search: KnowledgeSearch,
) -> list[Case]:
    """Classify via Woo and submit the original wording for every required refusal."""
    labels = list(dict.fromkeys(q.model for q in questions))
    states = authority.identify(labels)
    cases = []
    for question in questions:
        state = states.get(question.model.casefold())
        if state not in ("published", "unavailable", "unknown"):
            raise ValueError(f"Woo did not classify golden model {question.model!r}")
        withdrawn = []
        if state == "unavailable":
            withdrawn.append(question.model)
        elif state == "unknown":
            # Historical labels can contain editorial qualifiers. The customer's
            # actual sentence may still name a Woo product that has been withdrawn.
            matches = authority.identify_text(
                question.question, expected_revision=snapshot.model_identity_revision
            )
            withdrawn = [
                label for label, status in matches.items() if status == "unavailable"
            ]
        case = Case(question.id, question.model, state, withdrawn)
        if withdrawn:
            try:
                search.search(
                    {"query": question.question, "lang": question.lang}, snapshot
                )
            except PublicationChanged as error:
                if str(error) != "supplied model is no longer published":
                    raise
                case.refused = True
            else:
                case.refused = False
        cases.append(case)
    return cases


def coverage_failures(
    cases: Sequence[Case], snapshot: Snapshot, indexed: dict[str, list[int]]
) -> list[str]:
    """A missing sale model must not silently disappear from the positive gate."""
    published = {
        case.model.casefold() for case in cases if case.model_status == "published"
    }
    woo: dict[str, set[int]] = {}
    for pid, row in snapshot.products.items():
        woo.setdefault(str(row["model"]).casefold(), set()).add(pid)
    failures = []
    for label in sorted(published):
        if not woo.get(label) or woo[label] != set(indexed.get(label, [])):
            failures.append(
                f"published model {label!r} has inconsistent Woo / index product IDs"
            )
    failures.extend(
        f"{case.id}: withdrawn model request was not refused"
        for case in cases
        if case.refused is False
    )
    return failures
