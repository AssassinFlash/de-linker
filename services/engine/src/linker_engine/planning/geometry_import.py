"""Owned immutable source + explicit conversion manifest + reviewable candidate.

Preparing an import never saves or overwrites project geometry. The application
applies its candidate through the same guarded document/history command path.
"""

from __future__ import annotations

import base64
import binascii
import math

from shapely.geometry import Polygon

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .errors import InvalidInput
from .geographic import GeographicBridge, horizontal_on_roof
from .geometry import read_geometry, unit
from .geometry_documents import GeometrySource, RoofFace, SourcePermissions
from .geometry_geojson import selected_polygon
from .geometry_import_documents import GeometryImportOptions
from .records import Actor

# Initial file intake policy, below the native request window; not roof capacity.
MAX_GEOMETRY_FILE_BYTES = 4 * 1024 * 1024
PURPOSE = "geometry_import_v1"
MEDIA_TYPE = "application/geo+json"


class GeometryImport:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets

    @staticmethod
    def decode(content_base64: str) -> bytes:
        try:
            content = base64.b64decode(content_base64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise InvalidInput("geometry file must be valid base64") from error
        if not content or len(content) > MAX_GEOMETRY_FILE_BYTES:
            raise InvalidInput("geometry file exceeds the intake resource policy")
        return content

    @staticmethod
    def logical(options: GeometryImportOptions) -> Object:
        return {
            "schema_version": 1,
            "retention": "permanent",
            "provenance": {
                "label": options.source.label,
                "basis": "user_owned_geometry_file_declaration",
                "rights_basis": options.source.rights_note,
            },
            "geometry_import_options": options.model_dump(mode="json"),
        }

    @classmethod
    def command(cls, content: bytes, options: GeometryImportOptions) -> Object:
        if not content or len(content) > MAX_GEOMETRY_FILE_BYTES:
            raise InvalidInput("geometry file exceeds the intake resource policy")
        return {
            "content_sha256": digest(content),
            "media_type": MEDIA_TYPE,
            "purpose": PURPOSE,
            "metadata": cls.logical(options),
        }

    def previous(
        self,
        actor: Actor,
        project_id: str,
        content: bytes,
        options: GeometryImportOptions,
        *,
        key: str,
    ) -> Asset | None:
        return self.assets.receipt(
            actor, project_id, key, self.command(content, options)
        )

    def prepare(
        self,
        actor: Actor,
        project_id: str,
        content: bytes,
        options: GeometryImportOptions,
        *,
        key: str,
    ) -> Asset:
        self.assets.check_write(actor, project_id)
        previous = self.previous(actor, project_id, content, options, key=key)
        if previous is not None:
            return previous
        polygon, feature_id = selected_polygon(
            content, options.feature_index, options.polygon_index
        )
        # Stable within this project/declared conversion; retries never mint IDs.
        identity = digest(
            encode(
                {"project_id": project_id, "command": self.command(content, options)}
            )
        )[:32]
        source = GeometrySource(
            id=f"source_{identity}",
            kind="user_drawing",
            note=options.source.label,
            rights_note=options.source.rights_note,
            reference_url=None,
            reference_sha256=digest(content),
            acquired_at_utc=None,
            spatial_precision_m=options.source.spatial_precision_m,
            calibration_note=options.plane.basis_note,
            rights_basis="user_attestation",
            permissions=SourcePermissions(
                derive="permitted",
                retain="permitted",
                export=options.source.export_permission,
            ),
        )
        plane = options.plane
        unit(plane.u_axis_enu)
        unit(plane.v_axis_enu)
        bridge = GeographicBridge(options.reference)
        rings = []
        for ring in polygon.coordinates:
            points = []
            for longitude, latitude in ring[:-1]:
                east, north, _curvature_up = bridge.forward(longitude, latitude, 0)
                points.append(list(horizontal_on_roof(plane, east, north)))
            rings.append(points)
        roof = RoofFace(
            id=f"roof_{identity}",
            name=options.roof_name,
            source_id=source.id,
            origin_enu=plane.origin_enu,
            u_axis_enu=plane.u_axis_enu,
            v_axis_enu=plane.v_axis_enu,
            boundary_uv=rings[0],
            holes_uv=rings[1:],
        )
        geometry: Object = {
            "schema_version": 1,
            "coordinate_system": {
                "kind": "local_enu",
                "unit": "m",
                "height_reference": "relative_to_project_origin",
                "north_reference": "true_north",
                "north_source_id": source.id,
                "anchor": {
                    "latitude_deg": options.reference.latitude_deg,
                    "longitude_deg": options.reference.longitude_deg,
                    "source_id": source.id,
                    "datum": "EPSG:4326",
                },
            },
            "sources": [source.model_dump(mode="json")],
            "roofs": [roof.model_dump(mode="json")],
            "module_specs": [],
            "arrays": [],
            "obstacles": [],
            "keepouts": [],
            "layout_rules": [],
        }
        read_geometry(geometry)
        shape = Polygon(roof.boundary_uv, roof.holes_uv)
        if (
            not shape.is_valid
            or shape.is_empty
            or not math.isfinite(shape.area)
            or shape.area <= 0
        ):
            raise InvalidInput(
                "imported roof boundary/openings are not a valid polygon"
            )
        metadata: Object = {
            **self.logical(options),
            "geometry_import": {
                "schema_version": 1,
                "original_content_sha256": digest(content),
                "source_feature_id": feature_id,
                "projection": bridge.manifest(),
                "geometry": geometry,
                "geometry_sha256": digest(encode(geometry)),
                "area_roof_plane_m2": shape.area,
                "elevation_basis": "user_declared_plane_relative_to_project_origin",
                "engineering_status": "not_evaluated",
            },
        }
        return self.assets.add(
            actor,
            project_id,
            content,
            MEDIA_TYPE,
            PURPOSE,
            metadata,
            key=key,
            logical_metadata=self.logical(options),
        )
