"""Present retained direct-beam samples without a PV or electrical calculation."""

from __future__ import annotations

from typing import Literal, cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object
from .direct_beam_read import direct_beam_facts
from .report_copy import text


def direct_beam_sections(
    reference: Object, locale: Literal["en", "de"]
) -> list[ReportSection]:
    witness = cast(Object, reference["witness"])
    facts = direct_beam_facts(witness)
    sampling = cast(Object, facts["sampling"])
    limits = cast(Object, facts["limits"])

    def row(key: str, value: object) -> ReportRow:
        return ReportRow(label=text(key, locale), value=str(value))

    def value(raw: object) -> str:
        if raw is None:
            return "—"
        shown = f"{raw:.6g}" if isinstance(raw, float) else str(raw)
        return shown.replace(".", ",") if locale == "de" else shown

    rows = [
        row("direct_beam_source", f"{reference['run_id']} / {reference['revision']}"),
        row(
            "direct_beam_method",
            f"{facts['method']} / {cast(Object, facts['solar_position'])['pvlib_version']}",
        ),
        row(
            "direct_beam_sampling",
            f"{sampling['coarse_cells_per_edge']} / {sampling['fine_cells_per_edge']}",
        ),
        row(
            "direct_beam_counters",
            f"{sampling['sample_count']} / {sampling['ray_face_checks']} / {sampling['bounds_checks']}",
        ),
        row(
            "direct_beam_limits",
            " / ".join(
                str(limits[key])
                for key in (
                    "max_selected_rows",
                    "max_samples",
                    "max_ray_face_checks",
                    "max_bounds_checks",
                    "index_leaf_size",
                )
            ),
        ),
        row("direct_beam_result_hash", reference["result_sha256"]),
        row("direct_beam_manifest_hash", reference["manifest_sha256"]),
    ]
    rows.extend(
        ReportRow(label=key + " SHA-256", value=str(sha))
        for key, sha in cast(Object, reference["dependencies"]).items()
    )
    return [
        ReportSection(
            id="direct-beam-0",
            title=text("direct_beam_title", locale),
            paragraphs=[
                text("direct_beam_scope", locale),
                text("direct_beam_axes", locale),
            ],
            rows=rows,
            table=ReportTable(
                columns=[
                    text(key, locale)
                    for key in (
                        "direct_beam_interval",
                        "direct_beam_source_time",
                        "direct_beam_irradiance_time",
                        "direct_beam_modules",
                        "direct_beam_range",
                        "direct_beam_delta",
                    )
                ],
                rows=[
                    [
                        f"{item['interval_start_utc']} – {item['interval_end_utc']}",
                        str(item["source_label_utc"]),
                        str(item["irradiance_at_utc"]),
                        " / ".join(
                            str(item[key])
                            for key in (
                                "module_count",
                                "sampled_module_count",
                                "night_module_count",
                                "back_facing_or_tangent_module_count",
                            )
                        ),
                        f"{value(item['fine_visible_fraction_min'])} – {value(item['fine_visible_fraction_max'])}",
                        value(item["observed_absolute_delta_max"]),
                    ]
                    for item in cast(list[Object], facts["rows"])
                ],
            ),
        )
    ]
