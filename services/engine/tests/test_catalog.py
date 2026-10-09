"""The feed fixture is in the shape #8 will deliver, and nothing else is accepted."""

import copy
import json
from pathlib import Path

import pytest

from linker_engine.catalog import Catalog, FeedError

FIXTURES = Path(__file__).parent / "fixtures"


def test_every_published_product_is_in_the_feed(catalog: Catalog) -> None:
    assert len(catalog.products) == 106
    assert {p.device_class for p in catalog.products} >= {
        "inverters",
        "home-storage",
        "battery-systems",
    }


def test_the_seven_selection_facts_follow_7(catalog: Catalog) -> None:
    h2 = catalog.by_id[4107]
    assert (h2.application, h2.phase, h2.ac_power_kw, h2.pv_input_kw) == (
        "home",
        3,
        10.0,
        20.0,
    )
    # The 2026-10-09 rulings: EcoFlow application and phase filled, CHS2 at 29 999 W.
    assert (catalog.by_id[6485].application, catalog.by_id[6485].phase) == ("home", 1)
    assert catalog.by_id[6481].phase == 3
    assert catalog.by_id[1959].ac_power_kw == 29.999
    # ESA battery modules carry no phase: unknown, never guessed.
    assert catalog.by_id[6519].phase is None


def test_engineering_figures_are_read_per_mppt(catalog: Catalog) -> None:
    esa = catalog.by_id[6518]  # GW30K-ETA-G20
    assert esa.n_mppt == 4
    assert esa.strings_per_mppt == [1, 1, 2, 2]
    assert esa.mppt_max_isc_a == [26.0, 26.0, 52.0, 52.0]
    assert esa.mppt_voltage_range_v == (120.0, 950.0)


def test_every_figure_cites_a_document_we_host(catalog: Catalog) -> None:
    for product in catalog.products:
        for figure in product.figures.values():
            assert figure.citation.url.startswith("https://de-linker.com/")


def test_a_feed_that_breaks_the_schema_is_refused() -> None:
    feed = json.loads((FIXTURES / "feed.json").read_text())
    broken = copy.deepcopy(feed)
    del broken["products"][0]["phase"]
    with pytest.raises(FeedError, match="phase"):
        Catalog.from_feed(broken)
    foreign = copy.deepcopy(feed)
    foreign["products"][0]["documents"].append(
        {
            "url": "https://example.com/x.pdf",
            "title": "x",
            "type": "datasheet",
            "lang": "en",
        }
    )
    with pytest.raises(FeedError):
        Catalog.from_feed(foreign)


def test_the_reference_module_comes_from_the_overlay(catalog: Catalog) -> None:
    module = catalog.module
    assert (module.model, module.pmax_w, module.isc_a, module.max_series_fuse_a) == (
        "TSM-460NEG9R.28",
        460.0,
        10.81,
        25.0,
    )
