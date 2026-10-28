"""Bounded owned weather navigation; no provider acquisition or solar calculation."""

from __future__ import annotations

from typing import cast

from .access import project_row
from .assets import Asset, Assets
from .canonical import Json, Object, decode_object, digest, encode
from .direct_beam_inputs import DirectBeamTaskInputs
from .errors import InvalidInput
from .pv_parameters import PvGenerationLimits
from .pv_preparation import require_weather_source, selected_weather
from .pv_source import PvSource
from .records import Actor
from .weather_metadata import WEATHER_PURPOSE


def check_direct_beam(
    assets: Assets, actor: Actor, project_id: str | None, inputs: Object
) -> None:
    if "direct_beam_visibility" not in inputs:
        return
    selection = DirectBeamTaskInputs.read(inputs["direct_beam_visibility"])
    if project_id is None:
        raise InvalidInput("a new project cannot reference another project's weather")
    selected_weather(
        assets,
        actor,
        project_id,
        {
            **inputs,
            "pv_preparation": {
                "schema_version": 1,
                "weather_asset_id": selection.weather_asset_id,
            },
        },
    )


def _summary(asset: Asset) -> Object:
    require_weather_source(asset.purpose, asset.metadata)
    weather = asset.metadata.get("weather")
    interpretation = asset.metadata.get("weather_interpretation")
    provenance = asset.metadata.get("provenance")
    if (
        not isinstance(weather, dict)
        or not isinstance(interpretation, dict)
        or not isinstance(provenance, dict)
    ):
        raise InvalidInput("retained weather summary is missing")
    return {
        "asset_id": asset.id,
        "content_sha256": asset.content_sha256,
        "metadata_sha256": asset.metadata_sha256,
        "label": provenance.get("label"),
        "synthetic_year": interpretation.get("synthetic_energy_year"),
        "interval_count": weather.get("interval_count"),
    }


def weather_assets(
    assets: Assets, actor: Actor, project_id: str, *, offset: int, page_size: int
) -> Object:
    with assets.workspace.database.read() as connection:
        project_row(connection, actor, project_id)
        rows = connection.execute(
            "SELECT id FROM project_assets WHERE project_id=? AND purpose=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
            (project_id, WEATHER_PURPOSE, page_size + 1, offset),
        ).fetchall()
    items: list[Json] = [
        _summary(assets.get(actor, project_id, row["id"])) for row in rows[:page_size]
    ]
    return {
        "schema_version": 1,
        "project_id": project_id,
        "assets": items,
        "offset": offset,
        "next_offset": offset + page_size if len(rows) > page_size else None,
    }


def weather_preview(
    assets: Assets,
    actor: Actor,
    project_id: str,
    asset_id: str,
    limits: PvGenerationLimits,
    *,
    offset: int,
    page_size: int,
) -> Object:
    asset = assets.get(actor, project_id, asset_id)
    summary = _summary(asset)
    source = PvSource.read(assets.workspace.blobs, asset.content_sha256, asset.metadata)
    # Explicit preview parses the bounded retained original. It does not run at
    # admission, fetch the provider, or calculate PV/solar-position values.
    weather = source.weather(limits)
    details = decode_object(weather.source.details_json)
    rows: list[Json] = [
        {
            "source_row_index": index,
            "interval_start_utc": point.interval.start.isoformat(),
            "interval_end_utc": point.interval.end.isoformat(),
            "source_label_utc": point.source_label_utc.isoformat(),
            "irradiance_at_utc": point.irradiance_at_utc.isoformat(),
        }
        for index, point in enumerate(
            weather.points[offset : offset + page_size], start=offset
        )
    ]
    return {
        **summary,
        "schema_version": 1,
        "project_id": project_id,
        "weather_document_sha256": digest(encode(weather.document())),
        "source": {
            "start_year": source.request.start_year,
            "end_year": source.request.end_year,
            "radiation_database": source.request.expected_radiation_database,
            "meteo_database": source.request.expected_meteo_database,
            "irradiance_time_offset_hours": details["irradiance_time_offset_hours"],
            "months_selected": cast(list[Json], details["months_selected"]),
            "weather_kind": details["weather_kind"],
        },
        "offset": offset,
        "rows": rows,
        "next_offset": offset + page_size
        if offset + page_size < len(weather.points)
        else None,
    }
