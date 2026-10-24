"""Release verdicts combine every matching document; a pair nobody documents is unknown."""

import hashlib
import json
import re

import pytest
from conftest import SHIPPED_COMPATIBILITY

from linker_engine.compatibility import Compatibility, DocumentRef

H2_MANUAL = (
    "https://de-linker.com/wp-content/uploads/2026/10/"
    "SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf"
)
HS2_MANUAL = (
    "https://de-linker.com/wp-content/uploads/2026/10/"
    "SAJ_HS2-AS2_5-10K-T2_User-Manual_DE_V0.3.pdf"
)
B2_DATASHEET = (
    "https://de-linker.com/wp-content/uploads/2026/09/"
    "B2-5-25K-HV1HV5-datasheet-EN-BEU.pdf"
)

# The cells #481 and #489 decide, and the only cells the two files are compared
# on: an answer for them that changes in one file only must fail here.
REVIEWED_PAIRS = [
    ("H2-10K-T3", "B2-5.0-HV1"),
    ("H2-10K-T3", "B2-5.0-HV5"),
    ("H2-10K-T3", "BU2-5.0-HV1"),
    ("H2-10K-T3", "BU2-5.0-HV5"),
    ("HS2-5K-T2-X", "BU2-5.0-HV1"),
    ("HS2-5K-T2-X", "BU2-5.0-HV5"),
    ("HS2-10K-T2-X", "BU2-5.0-HV1"),
    ("HS2-10K-T2-X", "BU2-5.0-HV5"),
]


def test_the_shipped_contract_version_is_its_content_hash() -> None:
    """The feed publishes this version, so a contract edit must bump it."""
    contract = json.loads(SHIPPED_COMPATIBILITY.read_text())
    stored = contract.pop("version")
    canonical = json.dumps(
        contract, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    assert stored == hashlib.sha256(canonical.encode()).hexdigest()


def test_a_documented_release(compatibility: Compatibility) -> None:
    pair = compatibility.pair("GW10K-ETA-G20", "GW6.0-BAT-D-G20")
    assert pair.verdict == "released"
    assert all(d.url.startswith("https://de-linker.com/") for d in pair.documents)


def test_a_narrower_document_overrules_the_family_release(
    compatibility: Compatibility,
) -> None:
    # The H2 T3 family is released with B2, but the one-module B2-5.0 runs below its battery window.
    assert compatibility.pair("H2-10K-T3", "B2-10.0-HV1").verdict == "released"
    assert compatibility.pair("H2-10K-T3", "B2-5.0-HV1").verdict == "not_released"


def test_module_ranges_intersect(compatibility: Compatibility) -> None:
    assert compatibility.pair("HS2-10K-T2-X", "BU2-5.0-HV1").modules == (2, 5)


def test_an_accessory_named_by_the_release(compatibility: Compatibility) -> None:
    pair = compatibility.pair("EF HD-P3-10K0-S2", "EF BD-8-S2")
    assert pair.verdict == "released_with_accessory"
    assert [a.model for a in pair.accessories] == ["^OCEAN 2 LFP Battery Base$"]


def test_no_document_means_unknown(compatibility: Compatibility) -> None:
    assert (
        compatibility.pair("GW10K-ETA-G20", "Some Other Battery").verdict == "unknown"
    )


def test_meters_in_and_beside_the_box(
    compatibility: Compatibility, shipping_compatibility: Compatibility
) -> None:
    # #482: the lock runs on the contract the plugin ships, not only on the
    # fixture. The H2 T3 has exactly one meter requirement, and it is included:
    # the manual's Unpacking section (PDF p. 36 EN / p. 7 DE) names the smart
    # meter, three current transformers and the 10 m cable as delivered.
    for contract in (compatibility, shipping_compatibility):
        meters = contract.requirements("H2-10K-T3", "meter")
        assert [r.included for r in meters] == [True]
        assert meters[0].documents[0].page == 36
    assert shipping_compatibility.requirements("GW10K-ETA-G20", "meter")[0].included
    beside = shipping_compatibility.requirements("HS2-10K-T2-X", "meter")
    assert [(r.included, [a.model for a in r.accessories]) for r in beside] == [
        (False, ["^DTSU666$"])
    ]


def test_parallel_limits_come_from_the_controller_documents(
    compatibility: Compatibility,
) -> None:
    assert [
        r.max_units
        for r in compatibility.requirements("GW100K-ETR-G10", "parallel_controller")
    ] == [15]
    assert [
        r.max_units
        for r in compatibility.requirements("CHS2-30K-T4-X", "parallel_controller")
    ] == [10]


def test_the_shipped_contract_keeps_the_one_module_b2_off_the_h2(
    shipped_compatibility: Compatibility,
) -> None:
    # B2 datasheet p2: the one-module B2-5.0 runs at 89.6 to 115.2 V, under the
    # 180 to 800 V H2 battery range (H2 manual p37).
    for variant in ("HV1", "HV5"):
        pair = shipped_compatibility.pair("H2-10K-T3", f"B2-5.0-{variant}")
        assert pair.verdict == "not_released"
        assert not pair.released
        assert pair.conditions, "the answer states why"
        assert pair.accessories == (), "a pair that is not released names no accessory"
        assert DocumentRef(H2_MANUAL, 37) in pair.documents
        assert DocumentRef(B2_DATASHEET, 2) in pair.documents


def test_the_shipped_contract_starts_the_saj_module_at_two(
    shipped_compatibility: Compatibility,
) -> None:
    # HS2/AS2 manual V0.3 p12: two to five BU2-5.0 modules; the one-module
    # voltage misses both the 180-600 V HS2 and the 180-800 V H2 windows.
    h2 = shipped_compatibility.pair("H2-10K-T3", "BU2-5.0-HV1")
    assert (h2.verdict, h2.modules) == ("released_with_accessory", (2, 5))
    assert [a.model for a in h2.accessories] == ["^BC2-HV1$"]
    assert DocumentRef(H2_MANUAL, 37) in h2.documents
    assert DocumentRef(B2_DATASHEET, 2) in h2.documents
    for model in ("HS2-5K-T2-X", "HS2-10K-T2-X"):
        hs2 = shipped_compatibility.pair(model, "BU2-5.0-HV1")
        assert (hs2.verdict, hs2.modules) == ("released", (2, 5))
        assert DocumentRef(HS2_MANUAL, 12) in hs2.documents
        assert DocumentRef(B2_DATASHEET, 2) in hs2.documents


@pytest.mark.parametrize(("inverter", "battery"), REVIEWED_PAIRS)
def test_the_shipped_contract_and_the_fixture_agree_on_the_reviewed_cells(
    compatibility: Compatibility,
    shipped_compatibility: Compatibility,
    inverter: str,
    battery: str,
) -> None:
    """The fixture and the file production reads answer #481/#489 alike.

    Verdict, module range and accessory model and quantity are the decision.
    The two files word conditions separately and state the BC2 attachment per
    system and per stack respectively (these batteries allow one stack), so
    `per` is not compared.
    """
    shipped = shipped_compatibility.pair(inverter, battery)
    fixture = compatibility.pair(inverter, battery)
    assert shipped.verdict != "unknown" and fixture.verdict != "unknown"
    assert shipped.verdict == fixture.verdict
    assert shipped.modules == fixture.modules
    assert [(a.model, a.quantity) for a in shipped.accessories] == [
        (a.model, a.quantity) for a in fixture.accessories
    ]


def test_canonical_ids_prevent_same_model_products_from_borrowing_claims() -> None:
    raw = json.loads(SHIPPED_COMPATIBILITY.read_text())
    raw["pairs"] = [
        p
        for p in raw["pairs"]
        if re.search(p["inverter"], "H2-10K-T3")
        and re.search(p["battery"], "BU2-5.0-HV1")
    ]
    raw["requirements"] = [
        r for r in raw["requirements"] if re.search(r["inverter"], "H2-10K-T3")
    ]
    for pair in raw["pairs"]:
        pair.update(inverter_product_id=4107, battery_product_id=2090)
        for accessory in pair.get("accessories", []):
            accessory["product_id"] = 2092
    for row in raw["requirements"]:
        row["inverter_product_id"] = 4107
    contract = Compatibility(raw)
    matched = contract.pair(
        "H2-10K-T3", "BU2-5.0-HV1", inverter_id=4107, battery_id=2090
    )
    assert matched.released and matched.accessories[0].product_id == 2092
    assert (
        contract.pair(
            "H2-10K-T3", "BU2-5.0-HV1", inverter_id=4108, battery_id=2090
        ).verdict
        == "unknown"
    )
    assert contract.pair("H2-10K-T3", "BU2-5.0-HV1").verdict == "unknown"
    assert contract.requirements("H2-10K-T3", "meter", inverter_id=4107)
    assert not contract.requirements("H2-10K-T3", "meter", inverter_id=4108)
