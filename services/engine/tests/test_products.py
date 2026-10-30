"""The feed fixture is in the shape #8 will deliver, and nothing else is accepted."""

import copy
import json
import sys
from pathlib import Path

import pytest

from linker_engine.products import FeedError, Products

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE / "scripts"))

from build_fixtures import publication_envelope  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_every_published_product_is_in_the_feed(products: Products) -> None:
    assert len(products.products) == 106
    assert {p.device_class for p in products.products} >= {
        "inverters",
        "home-storage",
        "battery-systems",
    }


def test_the_seven_selection_facts_follow_7(products: Products) -> None:
    h2 = products.by_id[4107]
    assert (h2.application, h2.phase, h2.ac_power_kw, h2.pv_input_kw) == (
        "home",
        3,
        10.0,
        20.0,
    )
    # The 2026-10-09 rulings: EcoFlow application and phase filled, CHS2 at 29 999 W.
    assert (products.by_id[6485].application, products.by_id[6485].phase) == ("home", 1)
    assert products.by_id[6481].phase == 3
    assert products.by_id[1959].ac_power_kw == 29.999
    # ESA battery modules carry no phase: unknown, never guessed.
    assert products.by_id[6519].phase is None


def test_engineering_figures_are_read_per_mppt(products: Products) -> None:
    esa = products.by_id[6518]  # GW30K-ETA-G20
    assert esa.n_mppt == 4
    assert esa.strings_per_mppt == [1, 1, 2, 2]
    assert esa.mppt_max_isc_a == [26.0, 26.0, 52.0, 52.0]
    assert esa.mppt_voltage_range_v == (120.0, 950.0)


def test_every_figure_cites_a_document_we_host(products: Products) -> None:
    for product in products.products:
        for figure in product.figures.values():
            assert figure.citation.url.startswith("https://de-linker.com/")


def test_a_feed_that_breaks_the_schema_is_refused() -> None:
    feed = json.loads((FIXTURES / "feed.json").read_text())
    broken = copy.deepcopy(feed)
    del broken["products"][0]["phase"]
    with pytest.raises(FeedError, match="phase"):
        Products.from_feed(broken)
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
        Products.from_feed(foreign)


def test_a_feed_that_carries_the_compatibility_contract_is_accepted() -> None:
    """#493: the nightly sync reads the contract from the same feed."""
    feed = json.loads((FIXTURES / "feed.json").read_text())
    feed["compatibility"] = json.loads((FIXTURES / "compatibility.json").read_text())
    products = Products.from_feed(feed)
    assert len(products.products) == 106


def test_publication_envelope_is_idempotent() -> None:
    feed = json.loads((FIXTURES / "feed.json").read_text())
    contract = json.loads((FIXTURES / "compatibility.json").read_text())
    once = publication_envelope(feed, contract)
    assert publication_envelope(once, contract) == once
    Products.from_feed(once)


def test_qualified_figure_evidence_survives_strict_feed_loading() -> None:
    """A value cannot lose its scope and table-column meaning during loading."""
    feed = json.loads((FIXTURES / "feed.json").read_text())
    feed["figure_projection_version"] = 2
    raw = feed["products"][0]["figures"]
    key = next(iter(raw))
    raw[key]["qualifier"] = {"scope": "per_battery_port"}
    raw[key]["evidence_refs"] = ["reviewed-manual:p37"]
    raw[key]["columns"] = [{"module_count": 2, "value": 6144, "unit": "W"}]
    figure = Products.from_feed(feed).products[0].figures[key]
    assert figure.qualifier == {"scope": "per_battery_port"}
    assert figure.evidence_refs == ("reviewed-manual:p37",)
    assert figure.columns == ({"module_count": 2, "value": 6144, "unit": "W"},)


def test_the_reference_module_comes_from_the_overlay(products: Products) -> None:
    module = products.module
    assert (module.model, module.pmax_w, module.isc_a, module.max_series_fuse_a) == (
        "TSM-460NEG9R.28",
        460.0,
        10.81,
        25.0,
    )
