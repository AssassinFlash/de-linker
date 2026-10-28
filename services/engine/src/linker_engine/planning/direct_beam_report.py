"""Present retained direct-beam samples without a PV or electrical calculation."""

from __future__ import annotations

from typing import Literal, cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .direct_beam_read import direct_beam_facts
from .report_copy import text
from .report_numbers import number, significant, span


def direct_beam_sections(
    reference: Object, locale: Literal["en", "de"]
) -> list[ReportSection]:
    witness = cast(Object, reference["witness"])
    facts = direct_beam_facts(witness)
    sampling = cast(Object, facts["sampling"])
    limits = cast(Object, facts["limits"])

    def row(key: str, value: object) -> ReportRow:
        return ReportRow(label=text(key, locale), value=str(value))

    def value(raw: Json) -> str:
        return "—" if raw is None else significant(raw, locale)

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
            " / ".join(
                number(sampling[key], locale)
                for key in ("sample_count", "ray_face_checks", "bounds_checks")
            ),
        ),
        row(
            "direct_beam_limits",
            " / ".join(
                number(limits[key], locale)
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
    sections = [
        ReportSection(
            id="direct-beam-0",
            title=text("direct_beam_title", locale),
            paragraphs=[
                text("direct_beam_scope", locale),
                text("direct_beam_axes", locale),
            ],
            rows=rows,
        )
    ]
    # Long UTC timestamps and German labels need the report's established
    # two-column fact layout, rather than six narrow A4 columns. Every selected
    # source row stays identifiable without shrinking the normal report type.
    for item, aggregate in zip(
        cast(list[Object], witness["rows"]),
        cast(list[Object], facts["rows"]),
        strict=True,
    ):
        sections.append(
            ReportSection(
                id=f"direct-beam-row-{item['source_row_index']}",
                title=f"{text('direct_beam_row', locale)} {item['source_row_index']}",
                rows=[
                    row(
                        "direct_beam_interval",
                        span(
                            aggregate["interval_start_utc"],
                            aggregate["interval_end_utc"],
                            locale,
                        ),
                    ),
                    row("direct_beam_source_time", aggregate["source_label_utc"]),
                    row("direct_beam_irradiance_time", aggregate["irradiance_at_utc"]),
                    row(
                        "direct_beam_modules",
                        " / ".join(
                            str(aggregate[key])
                            for key in (
                                "module_count",
                                "sampled_module_count",
                                "night_module_count",
                                "back_facing_or_tangent_module_count",
                            )
                        ),
                    ),
                    row(
                        "direct_beam_range",
                        span(
                            aggregate["fine_visible_fraction_min"],
                            aggregate["fine_visible_fraction_max"],
                            locale,
                        ),
                    ),
                    row(
                        "direct_beam_delta",
                        value(aggregate["observed_absolute_delta_max"]),
                    ),
                ],
            )
        )
    return sections
