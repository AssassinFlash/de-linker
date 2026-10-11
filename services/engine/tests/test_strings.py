"""String layout per MPPT and the string fuses it decides (compliance case 3 of the ticket)."""

import dataclasses

from linker_engine import strings
from linker_engine.products import Products


def test_fuses_follow_the_reverse_current_test_per_mppt(products: Products) -> None:
    module = products.module  # Isc 10.81 A, maximum series fuse 25 A
    # (N - 1) x 1.25 x Isc must exceed 1.35 x 25 A = 33.75 A before fuses are needed.
    assert [strings.fuses_needed(n, module) for n in (1, 2, 3, 4, 5)] == [
        0,
        0,
        0,
        8,
        10,
    ]


def test_two_strings_per_mppt_need_no_fuses_even_with_twenty_strings(
    products: Products,
) -> None:
    # The old engine counted strings per inverter and fused 3+; ETR has 10 MPPTs x 2 strings.
    etr = products.by_id[6509]  # GW100K-ETR-G10
    result = strings.layout(etr, [100.0], products.module)
    assert result.layout is not None
    assert result.layout.total_strings > 3
    assert max(group.strings for group in result.layout.strings) <= 2
    assert result.layout.fuses == 0


def test_an_mppt_with_four_strings_gets_eight_fuses(products: Products) -> None:
    h2 = products.by_id[
        4108
    ]  # H2-12K-T3: 3 MPPTs, 2 strings each, 40 A / 50 A per MPPT
    figure = h2.figures["strings_per_mppt"]
    wide = dataclasses.replace(
        h2,
        figures={
            **h2.figures,
            "n_mppt": dataclasses.replace(figure, value="1"),
            "strings_per_mppt": dataclasses.replace(figure, value="4"),
            "mppt_max_current_a": dataclasses.replace(figure, value="60"),
            "mppt_max_isc_a": dataclasses.replace(figure, value="60"),
        },
    )
    # 60 modules: four strings of 15 on the single MPPT.
    result = strings.layout(wide, [27.6], products.module)
    assert result.layout is not None
    (group,) = result.layout.strings
    assert (group.strings, group.fuses) == (4, 8)


def test_ten_kwp_on_a_ten_kw_inverter(products: Products) -> None:
    result = strings.layout(products.by_id[4107], [10.0], products.module)  # H2-10K-T3
    assert result.layout is not None
    assert result.layout.module_count == 22
    assert result.layout.array_kwp == 10.12
    # 22 x 460 Wp as 2 x 11: Voc at -10 °C is 58.3 V, 11 modules give 641 V < 1000 V.
    assert [g.strings for g in result.layout.strings if g.strings] == [1, 1]


def test_missing_datasheet_values_stop_the_layout(products: Products) -> None:
    ecoflow = products.by_id[
        6480
    ]  # figures without a hosted citation are not in the feed
    assert strings.layout(ecoflow, [5.0], products.module).reason == "engineering_data"


def test_planes_keep_their_own_mppts(products: Products) -> None:
    esa = products.by_id[3584]  # GW12K-ETA-G20: 4 MPPTs with one string each
    result = strings.layout(esa, [6.0, 6.0], products.module)
    assert result.layout is not None
    planes = {g.plane for g in result.layout.strings if g.strings}
    assert planes == {0, 1}
