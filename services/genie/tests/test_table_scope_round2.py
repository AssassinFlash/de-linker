"""Round-2 fixes: alias resolution and the word-evidence grid rebuild."""

from __future__ import annotations

from typing import Any

import index.extract as extract_module
from index.extract import _rebuild_external_grid
from linker_genie.model_aliases import woo_model
from linker_genie.table_projection import SourceSpan


def test_alias_table_resolves_only_the_documented_writings() -> None:
    assert woo_model("CH2-30K-T4") == "chs2-30k-t4-x"
    assert woo_model("HS3-5-12K-T2-W/G-P3") == "hs3-8k-t2-w/g-px"
    assert woo_model("HS3-12K-T2-W-P") == "hs3-12k-t2-w/g-px"
    # Unknown labels stay unresolved; nothing else moves.
    assert woo_model("CH2-31K-T4") == "ch2-31k-t4"
    assert woo_model("GW10K-ET-G10") == "gw10k-et-g10"


def _span(text: str, x0: float, x1: float, index: int) -> SourceSpan:
    return SourceSpan(
        text=text,
        bbox=(x0, 50.0, x1, 60.0),
        char_start=index,
        char_end=index + len(text),
        page=3,
        source_sha256="a" * 64,
        page_size=(600.0, 800.0),
    )


def test_rebuild_places_per_model_values_and_merges_shared_ink(
    monkeypatch: Any,
) -> None:
    """The ETR p.3 shape: per-model columns plus centered shared values."""
    axis = [
        _span("GW80K-ETR-G10", 220.0, 250.0, 0),
        _span("GW99.99K-ETR-G10", 280.0, 310.0, 20),
        _span("GW100K-ETR-G10", 340.0, 370.0, 40),
        _span("GW110K-ETR-G10", 400.0, 430.0, 60),
    ]
    words: list[tuple[str, tuple[float, float, float, float]]] = [
        # Section row.
        ("Efficiency", (52.0, 100.0, 96.0, 108.0)),
        # Shared row: label plus one centered value across the middle bands.
        ("Max.", (52.0, 120.0, 66.0, 128.0)),
        ("Efficiency", (69.0, 120.0, 99.0, 128.0)),
        ("98.1%", (368.0, 120.0, 392.0, 128.0)),
        # Per-model row: one value in each of the four columns.
        ("Weight", (52.0, 140.0, 73.0, 148.0)),
        ("(kg)", (76.0, 140.0, 88.0, 148.0)),
        ("82", (228.0, 140.0, 235.0, 148.0)),
        ("96", (288.0, 140.0, 295.0, 148.0)),
        ("96", (348.0, 140.0, 355.0, 148.0)),
        ("98", (408.0, 140.0, 415.0, 148.0)),
    ]
    monkeypatch.setattr(
        extract_module, "_page_words_in_box", lambda *_args, **_kw: list(words)
    )
    cells = _rebuild_external_grid(object(), 3, (40.0, 90.0, 560.0, 160.0), axis)
    assert cells is not None
    grid: dict[tuple[int, int], str] = {
        (cell["row_start"], cell["col_start"]): cell["text"] for cell in cells
    }
    assert grid[(0, 0)] == "Efficiency"
    shared = next(c for c in cells if c["row_start"] == 1 and c["col_start"] > 0)
    # '98.1%' [325,344] overlaps the third band's right edge and the fourth
    # band's left edge: one merged cell serving both models.
    assert (shared["col_start"], shared["col_end"]) == (3, 5)
    assert shared["text"] == "98.1%"
    weights = sorted(
        (c["col_start"], c["text"]) for c in cells if c["row_start"] == 2 and c["col_start"] > 0
    )
    assert weights == [(1, "82"), (2, "96"), (3, "96"), (4, "98")]
    assert max(cell["col_end"] for cell in cells) == 5


def test_rebuild_rejects_ambiguous_grids(monkeypatch: Any) -> None:
    axis = [
        _span("GW80K-ETR-G10", 220.0, 250.0, 0),
        _span("GW99.99K-ETR-G10", 280.0, 310.0, 20),
    ]
    # A label word straddling the label boundary aborts the repair.
    words = [
        ("OddLabel", (52.0, 100.0, 255.0, 108.0)),
        ("Value", (285.0, 100.0, 305.0, 108.0)),
    ]
    monkeypatch.setattr(
        extract_module, "_page_words_in_box", lambda *_args, **_kw: list(words)
    )
    assert _rebuild_external_grid(object(), 3, (40.0, 90.0, 560.0, 160.0), axis) is None
