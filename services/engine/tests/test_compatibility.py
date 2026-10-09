"""Release verdicts combine every matching document; a pair nobody documents is unknown."""

from linker_engine.compatibility import Compatibility


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


def test_meters_in_and_beside_the_box(compatibility: Compatibility) -> None:
    assert [r.included for r in compatibility.requirements("H2-10K-T3", "meter")] == [
        True
    ]
    beside = compatibility.requirements("HS2-10K-T2-X", "meter")
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
