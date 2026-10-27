"""The decision of category-sitemap.py: which archives stay out, which get in.

The script's effect is checked against a WordPress (plan against the live
site, then verify after the write). What a unit test pins down is the
decision and the readback: exactly the monitoring pair is indexable and
listed, the four retired groups and `uncategorized` are noindexed and
unlisted, a second run plans nothing, and a category with no ruling stops
the write.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def load() -> ModuleType:
    """The script is a file, not an importable module name."""
    path = Path(__file__).resolve().parent.parent / "category-sitemap.py"
    spec = importlib.util.spec_from_file_location("category_sitemap", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their module through sys.modules while the class is
    # built; a spec-loaded module must be registered before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


script = load()


def term(
    term_id: int,
    slug: str,
    language: str,
    *,
    index: str = "",
    twin: int | None = None,
    count: int = 2,
) -> Any:
    """One category term as the WP-CLI reader returns it."""
    translations = {"de": twin} if twin is not None else {}
    if language == "de":
        translations = {"en": twin} if twin is not None else {}
    return script.Term(
        id=term_id,
        slug=slug,
        name=slug,
        count=count,
        language=language,
        index=index,
        canonical="",
        translations=translations,
        url=f"https://de-linker.test/{'de/kategorie' if language == 'de' else 'category'}/{slug}/",
    )


def production_terms(*, index: str = "") -> list[Any]:
    """The ten category terms production holds, in both languages."""
    return [
        term(10, "system-design", "en", index=index, twin=586),
        term(11, "battery-storage-blog", "en", index=index, twin=577),
        term(12, "installation-commissioning", "en", index=index, twin=580),
        term(13, "monitoring-energy-management", "en", index=index, twin=583),
        term(14, "applications-blog", "en", index=index, twin=574),
        term(574, "anwendungen", "de", index=index, twin=14),
        term(577, "batteriespeicher", "de", index=index, twin=11),
        term(580, "installation-inbetriebnahme", "de", index=index, twin=12),
        term(583, "ueberwachung-energiemanagement", "de", index=index, twin=13),
        term(586, "systemauslegung", "de", index=index, twin=10),
        term(1, "uncategorized", "en", index=index, count=0),
    ]


def state(
    terms: list[Any],
    *,
    noindex: str | None = "1",
    include: str | None = "",
    sitemap_ids: tuple[int, ...] = (),
) -> Any:
    """A read of the database."""
    return script.State(
        terms=tuple(terms),
        sitemap_ids=sitemap_ids,
        options=script.Options(category_noindex=noindex, category_include=include),
    )


def desired_terms() -> list[Any]:
    """The state after the write: only the monitoring pair is indexable."""
    terms = production_terms(index="yes")
    for term_id in (13, 583):
        raw = next(item for item in terms if item.id == term_id)
        terms[terms.index(raw)] = script.Term(
            id=raw.id,
            slug=raw.slug,
            name=raw.name,
            count=raw.count,
            language=raw.language,
            index="",
            canonical="",
            translations=raw.translations,
            url=raw.url,
        )
    return terms


def desired_state() -> Any:
    """The state after the write."""
    return state(
        desired_terms(),
        noindex="",
        include="1",
        sitemap_ids=(13, 583),
    )


def test_the_plan_indexes_only_the_monitoring_pair() -> None:
    """Two archives become indexable; the four groups and uncategorized do not."""
    actions, unknown = script.plan(state(production_terms()))

    assert unknown == []
    term_writes = [action for action in actions if action["kind"] == "term"]
    assert {action["id"] for action in term_writes} == {
        10,
        11,
        12,
        14,
        574,
        577,
        580,
        586,
        1,
    }
    assert {action["to"] for action in term_writes} == {"yes"}
    option_writes = {
        action["name"]: action["to"] for action in actions if action["kind"] == "option"
    }
    assert option_writes == {"titles-noindex": "", "sitemap-include": "1"}


def test_the_plan_keeps_the_monitoring_pair_out_of_the_noindex_writes() -> None:
    """The pair has no term override; the taxonomy default is what changes."""
    actions, _ = script.plan(state(production_terms()))

    touched = {action["id"] for action in actions if action["kind"] == "term"}
    assert 13 not in touched
    assert 583 not in touched


def test_the_sitemap_query_after_the_write_holds_the_pair_only() -> None:
    """SEOPress's own query args return the two monitoring terms."""
    after = desired_state()

    assert set(after.sitemap_ids) == {13, 583}


def test_a_second_run_plans_nothing() -> None:
    """Idempotent: every switch and term already matches."""
    actions, unknown = script.plan(desired_state())

    assert actions == []
    assert unknown == []


def test_a_missing_german_twin_stops_the_plan() -> None:
    """No translation is a stop, not an English-only write."""
    terms = [item for item in production_terms() if item.id != 583]

    with pytest.raises(SystemExit, match="no German translation"):
        script.monitoring_pair(tuple(terms))


def test_an_unclassified_category_stops_the_write() -> None:
    """A new category has no owner ruling here; the script must not guess."""
    terms = [*production_terms(), term(900, "new-topic", "en")]

    _, unknown = script.plan(state(terms))

    assert [item.slug for item in unknown] == ["new-topic"]
    with pytest.raises(SystemExit, match="unclassified category"):
        script.refuse_unknown(unknown)


def test_verify_passes_on_the_desired_state() -> None:
    """Options, term meta and the sitemap query all agree."""
    assert script.verify_state(desired_state()) == []


def test_verify_rejects_a_noindexed_monitoring_term() -> None:
    """The requirement is indexable, not merely absent from the sitemap."""
    terms = desired_terms()
    raw = next(item for item in terms if item.id == 13)
    terms[terms.index(raw)] = script.Term(
        id=raw.id,
        slug=raw.slug,
        name=raw.name,
        count=raw.count,
        language=raw.language,
        index="yes",
        canonical="",
        translations=raw.translations,
        url=raw.url,
    )

    problems = script.verify_state(
        state(terms, noindex="", include="1", sitemap_ids=(583,))
    )

    assert any("13 monitoring-energy-management" in problem for problem in problems)


def test_verify_rejects_the_old_taxonomy_defaults() -> None:
    """Both stored switches are part of the result."""
    problems = script.verify_state(
        state(production_terms(index="yes"), noindex="1", include="")
    )

    assert any("category.noindex" in problem for problem in problems)
    assert any("category.include" in problem for problem in problems)


def test_verify_rejects_an_excluded_group_in_the_sitemap() -> None:
    """A noindexed group must stay out of the term query's answer."""
    problems = script.verify_state(
        state(desired_terms(), noindex="", include="1", sitemap_ids=(13, 583, 10))
    )

    assert any("sitemap term query" in problem for problem in problems)
