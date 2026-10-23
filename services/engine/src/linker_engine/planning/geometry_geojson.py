"""Read one explicitly selected roof polygon, retaining every opening.

No provider fetch, CRS guessing, bounding-box substitution, geometry repair or
inferred height. Original bytes remain available to the owned intake.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import Field, ValidationError

from .canonical import Json, Object, encode
from .energy_inputs import Document
from .errors import InvalidInput
from .geometry import MAX_VERTICES
from .geometry_documents import Vec2
from .wire_numbers import check_wire_numbers


class HorizontalPolygon(Document):
    type: Literal["Polygon"]
    coordinates: Annotated[
        list[Annotated[list[Vec2], Field(min_length=4)]], Field(min_length=1)
    ]


def unique_object(pairs: list[tuple[str, Json]]) -> Object:
    result: Object = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("geometry file has duplicate JSON members")
        result[key] = value
    return result


def invalid_constant(_constant: str) -> Json:
    raise InvalidInput("geometry file has non-finite JSON numbers")


def selected_polygon(
    content: bytes, feature_index: int, polygon_index: int
) -> tuple[HorizontalPolygon, Json]:
    try:
        document: Json = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=invalid_constant,
        )
    except (UnicodeError, ValueError, RecursionError) as error:
        raise InvalidInput("geometry file must contain valid UTF-8 GeoJSON") from error
    if not isinstance(document, dict) or "crs" in document:
        raise InvalidInput("GeoJSON requires explicit WGS84 longitude/latitude")
    kind = document.get("type")
    if not isinstance(kind, str):
        raise InvalidInput("a typed GeoJSON geometry or feature is required")
    feature: Object
    if kind == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list) or not 0 <= feature_index < len(features):
            raise InvalidInput("selected GeoJSON feature is absent")
        raw_feature = features[feature_index]
        if not isinstance(raw_feature, dict) or raw_feature.get("type") != "Feature":
            raise InvalidInput("selected GeoJSON feature is invalid")
        feature = raw_feature
    elif kind == "Feature":
        if feature_index != 0:
            raise InvalidInput("selected GeoJSON feature is absent")
        feature = document
    elif kind in {"Polygon", "MultiPolygon"}:
        if feature_index != 0:
            raise InvalidInput("selected GeoJSON feature is absent")
        feature = {"geometry": document}
    else:
        raise InvalidInput("a Polygon or MultiPolygon roof feature is required")
    shape = feature.get("geometry")
    if not isinstance(shape, dict) or "crs" in shape or "crs" in feature:
        raise InvalidInput("selected roof geometry is absent or has an unsupported CRS")
    coordinates = shape.get("coordinates")
    if shape.get("type") == "MultiPolygon":
        if not isinstance(coordinates, list) or not 0 <= polygon_index < len(
            coordinates
        ):
            raise InvalidInput("selected roof polygon is absent")
        coordinates = coordinates[polygon_index]
    elif shape.get("type") != "Polygon" or polygon_index != 0:
        raise InvalidInput("selected roof polygon is absent")
    try:
        polygon = HorizontalPolygon.model_validate(
            {"type": "Polygon", "coordinates": coordinates}
        )
    except ValidationError as error:
        raise InvalidInput(
            "selected roof needs closed 2D longitude/latitude rings"
        ) from error
    if sum(map(len, polygon.coordinates)) > MAX_VERTICES:
        raise InvalidInput("geometry vertex resource limit exceeded")
    for ring in polygon.coordinates:
        if ring[0] != ring[-1] or any(
            not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90 for point in ring
        ):
            raise InvalidInput("roof rings must close in WGS84 longitude/latitude")
    feature_id = feature.get("id")
    if feature_id is not None and type(feature_id) not in {str, int, float}:
        raise InvalidInput("GeoJSON feature identifier is invalid")
    # IDs enter the public manifest too; reject non-finite/unsafe numbers or
    # escaped invalid Unicode before intake publishes any original bytes.
    try:
        check_wire_numbers(feature_id)
    except ValueError as error:
        raise InvalidInput(
            "GeoJSON feature identifier exceeds numeric support"
        ) from error
    encode(feature_id)
    return polygon, feature_id
