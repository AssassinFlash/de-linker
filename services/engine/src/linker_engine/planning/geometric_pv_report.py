"""Readable frozen geometric PV scenario, without numerical reproduction."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .frozen_documents import FrozenDocuments
from .geometric_pv_inputs import POLICY_V2
from .geometric_pv_profile import prepared_profile, reference_bundle
from .pv_profile_artifacts import _object
from .report_copy import text
from .report_numbers import number, span
from .report_pv_arrays import array_identities, placements_of
from .report_pv_components import pv_components
from .report_pvlib import PvReferenceParts, pvlib_rows
from .storage import Blobs

# Copy keys the geometric section states itself. The mature coefficient and
# source rows stay, but a second model identity, the unshaded period rows and
# the usage rows repeated per reference are not shown twice.
OWN_ROW_KEYS = frozenset(
    {
        "pvlib_model",
        "pvlib_weather_period",
        "pvgis_radiation_database",
        "pvlib_meteo_database",
        "pvlib_synthetic_year",
        "period",
        "intervals",
        "pvgis_ac_energy",
        "pvgis_source_run",
        "comparison_baseline",
        "comparison_candidate",
    }
)
# Witnesses saved before the scope existed name the electrical policy but do
# not say which stages it applied to. This marker records that absence. It is
# not the current independent-module interpretation.
NOT_RECORDED_ELECTRICAL_SCOPE: Object = {"status": "not_recorded"}
_RECORDED_FACT_KEYS = (
    "model_role",
    "diffuse_policy",
    "thermal_policy",
    "electrical_policy",
    "sampling",
    "work",
    "limits",
    "not_assessed",
    "temporal_policy",
)


def _saved_summary(reference: Object) -> Object:
    """The frozen period and energy, under either retained name.

    Reports saved before this reference called the object `profile_summary`
    keep it as `summary`. Either name is that saved object. A missing object
    is still a corrupt source.
    """
    saved = reference.get("profile_summary")
    if not isinstance(saved, dict):
        saved = reference.get("summary")
    return _object(saved)


def _model_facts(details: Object) -> Object:
    """Copy recorded witness facts. Do not invent a missing electrical scope.

    The scope stays beside the policy name, where a current witness already
    puts it. Only a witness that never recorded the scope gets the marker.
    """
    recorded = {key: details[key] for key in _RECORDED_FACT_KEYS}
    saved = details.get("electrical_policy_scope", NOT_RECORDED_ELECTRICAL_SCOPE)
    scope = _object(saved)
    if saved is NOT_RECORDED_ELECTRICAL_SCOPE:
        scope = dict(scope)
    return {
        "model_role": recorded["model_role"],
        "diffuse_policy": recorded["diffuse_policy"],
        "thermal_policy": recorded["thermal_policy"],
        "electrical_policy": recorded["electrical_policy"],
        "electrical_policy_scope": scope,
        "sampling": recorded["sampling"],
        "work": recorded["work"],
        "limits": recorded["limits"],
        "not_assessed": recorded["not_assessed"],
        "temporal_policy": recorded["temporal_policy"],
    }


def geometric_pv_reference(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    documents: FrozenDocuments | None = None,
) -> Object:
    """One verified bundle feeds the profile, rows and component list.

    Every consumer inside a report works from the same reader, so the retained
    witness is parsed once for that request instead of once per section.
    """
    documents = FrozenDocuments(blobs) if documents is None else documents
    bundle = reference_bundle(blobs, raw_sha256, metadata, documents)
    profile = prepared_profile(blobs, raw_sha256, metadata, documents, bundle=bundle)
    inputs, witness = _object(bundle["inputs"]), _object(bundle["witness"])
    details = _object(witness["inputs"])
    return {
        "model": witness["kind"],
        "geometry": inputs["geometry"],
        "parameters": inputs["parameters"],
        "model_facts": _model_facts(details),
        "profile_summary": {
            "start_utc": profile.intervals[0].start.isoformat(),
            "end_utc": profile.intervals[-1].end.isoformat(),
            "interval_count": len(profile.intervals),
            "energy_kwh": profile.total_kwh,
            "native_max_interval_seconds": profile.source.native_max_interval_seconds,
            "reconstructed_means": profile.reconstructed_means,
            "output_boundary": "pv_available_ac",
        },
        "weather_source": _object(inputs["weather"])["source"],
        "weather_metadata": bundle["weather_metadata"],
        "arrays": array_identities(
            cast(list[Json], witness["arrays"]),
            placements_of(_object(inputs["geometry"])),
        ),
        "converters": [
            {key: _object(item)[key] for key in ("id", "model_ac_cap_w")}
            for item in cast(list[Json], witness["converters"])
        ],
        "pv_components": pv_components(
            blobs, raw_sha256, metadata, documents=documents, geometric_bundle=bundle
        ),
        "dependencies": bundle["dependencies"],
    }


def _coefficient_rows(reference: Object, locale: str) -> list[ReportRow]:
    """The established readable coefficients, without the unshaded identity."""
    if not all(key in reference for key in ("arrays", "converters", "pv_components")):
        return []  # Historical report sources retain their original shape.
    parameters = _object(_object(reference["parameters"])["parameters"])
    return pvlib_rows(
        PvReferenceParts(
            parameters=parameters,
            weather=_object(_object(reference["weather_source"])["details"]),
            profile_summary=_saved_summary(reference),
            components=_object(reference["pv_components"]),
            arrays=cast(list[Object], reference["arrays"]),
            converters=cast(list[Object], reference["converters"]),
            used_by=cast(list[Object], reference["used_by"]),
            dependencies={},
        ),
        locale,
        skip=OWN_ROW_KEYS,
        note_key="geometric_pv_original_note",
    )


def _recorded_copy(facts: Object, retained: str, current: str) -> str:
    """Use the Perez wording only when that policy was actually recorded.

    A witness or report source saved before the field existed keeps the
    direct-only paragraph. The current policy is not filled in for it.
    """
    return current if facts.get("diffuse_policy") == POLICY_V2 else retained


def geometric_pv_sections(references: list[Json], locale: str) -> list[ReportSection]:
    result = []
    for index, raw in enumerate(references):
        reference = _object(raw)
        summary, facts = (
            _saved_summary(reference),
            _object(reference["model_facts"]),
        )
        metadata = _object(reference["weather_metadata"])
        request, interpretation = (
            _object(metadata["weather_request"]),
            _object(metadata["weather_interpretation"]),
        )
        sampling = _object(facts["sampling"])
        parameters = _object(_object(reference["parameters"])["parameters"])
        rows = [
            ReportRow(
                label=text("geometric_pv_model", locale),
                value=f"{reference['model']} / pvlib {parameters['pvlib_version']}",
            ),
            ReportRow(
                label=text("geometric_pv_period", locale),
                value=span(summary["start_utc"], summary["end_utc"], locale),
            ),
            ReportRow(
                label=text("geometric_pv_rows", locale),
                # An interval count is a quantity the report also shows in its
                # unshaded sections, so it reads the same way there.
                value=number(summary["interval_count"], locale),
            ),
            ReportRow(
                label=text("geometric_pv_energy", locale),
                value=number(summary["energy_kwh"], locale, "kWh"),
            ),
            ReportRow(
                label=text("geometric_pv_sampling", locale),
                value=f"{sampling['coarse_cells_per_edge']} / {sampling['fine_cells_per_edge']}",
            ),
            ReportRow(
                label=text("geometric_pv_weather", locale),
                value=f"{request['start_year']}–{request['end_year']} / {request['expected_radiation_database']} / {request['expected_meteo_database']}",
            ),
            ReportRow(
                label=text("geometric_pv_year", locale),
                value=str(interpretation["synthetic_energy_year"]),
            ),
        ]
        rows.extend(_coefficient_rows(reference, locale))
        rows.extend(
            ReportRow(label=name + " SHA-256", value=str(sha))
            for name, sha in _object(reference["dependencies"]).items()
        )
        rows.extend(
            ReportRow(
                label=text("geometric_pv_used_by", locale),
                value=f"{_object(usage)['run_id']} / {_object(usage)['revision']}",
            )
            for usage in cast(list[Json], reference["used_by"])
        )
        result.append(
            ReportSection(
                id=f"geometric-pv-reference-{index}",
                title=text(
                    _recorded_copy(
                        facts, "geometric_pv_title", "geometric_pv_title_perez"
                    ),
                    locale,
                ),
                paragraphs=[
                    text(
                        _recorded_copy(
                            facts, "geometric_pv_scope", "geometric_pv_scope_perez"
                        ),
                        locale,
                    ),
                    text("geometric_pv_axes", locale),
                    *(
                        [
                            text(
                                _recorded_copy(
                                    facts,
                                    "geometric_pv_notes_scope",
                                    "geometric_pv_notes_scope_perez",
                                ),
                                locale,
                            )
                        ]
                        if "arrays" in reference
                        else []
                    ),
                ],
                rows=rows,
            )
        )
    return result
