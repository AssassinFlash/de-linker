/** Read-only map projection. GeoJSON is a display copy, never metric input. */
import type {
	Feature,
	FeatureCollection,
	MultiPolygon,
	Polygon,
} from "geojson";
import type {
	GeometryDocument,
	PanelPose,
	RoofFace,
	Vec2,
	Vec3,
} from "./geometry.ts";
import { GeographicBridge } from "./geographic.ts";
import { add, scale, vectorFromRoof } from "./coordinates.ts";
import { panelCornersUVN, panelPoses } from "./panelPoses.ts";
import { requireUvResolution } from "./geometryNumerics.ts";

// Pinned MapLibre GL 5.24.0 src/util/util.ts MAX_VALID_LATITUDE. Refuse rather
// than let its Mercator renderer clamp a real position to another latitude.
const MERCATOR_LATITUDE_LIMIT = 85.051129;

export interface MapObject {
	object_id: string;
	kind: "roof" | "module" | "obstacle" | "keepout";
	roof_id: string;
	source_id: string;
	included: boolean;
}
type MapFeature = Feature<Polygon | MultiPolygon, MapObject>;
export interface GeographicMapGeometry {
	collection: FeatureCollection<Polygon | MultiPolygon, MapObject>;
	/** Longitude may use the adjacent world, relative to the declared anchor. */
	bounds: readonly [Vec2, Vec2] | null;
	centre: Vec2;
}

/** One display frame for the complete document; never infer north from a map. */
export function geographicMapGeometry(
	document: GeometryDocument,
	poses: readonly PanelPose[] = panelPoses(document),
): GeographicMapGeometry {
	const coordinate = document.coordinate_system,
		anchor = coordinate.anchor;
	if (!anchor || coordinate.north_reference !== "true_north")
		throw new Error("map_geographic_reference_required");
	const bridge = new GeographicBridge({
		schema_version: 1,
		method: "wgs84_cart_topocentric_v1",
		longitude_deg: anchor.longitude_deg,
		latitude_deg: anchor.latitude_deg,
		ellipsoid_height_m: 0,
		height_basis: "zero_height_horizontal_convention",
	});
	let west = Infinity,
		east = -Infinity,
		south = Infinity,
		north = -Infinity;
	function position(enu: Vec3): [number, number] {
		// The geodetic boundary uses the same binary64 support policy as import
		// and layout rendering. This budget does not assert source accuracy.
		requireUvResolution(enu);
		const [longitude, latitude] = bridge.inverse(enu);
		if (Math.abs(latitude) > MERCATOR_LATITUDE_LIMIT)
			throw new Error("map_projection_latitude_unsupported");
		// A world-width display translation preserves the physical longitude.
		// It avoids drawing a short dateline-crossing roof around the globe.
		const unwrapped =
			longitude + 360 * Math.round((anchor!.longitude_deg - longitude) / 360);
		west = Math.min(west, unwrapped);
		east = Math.max(east, unwrapped);
		south = Math.min(south, latitude);
		north = Math.max(north, latitude);
		return [unwrapped, latitude];
	}
	function ring(points: readonly Vec3[]): number[][] {
		if (points.length < 3) throw new Error("map_geometry_ring_invalid");
		const result = points.map(position);
		// Close a new copy, leaving the authoritative open ring untouched.
		return [...result, [...result[0]!]];
	}
	const features: MapFeature[] = [],
		roofs = new Map(document.roofs.map((roof) => [roof.id, roof])),
		arrays = new Map(document.arrays.map((array) => [array.id, array]));
	function roofFor(id: string): RoofFace {
		const roof = roofs.get(id);
		if (!roof) throw new Error("map_geometry_reference_missing");
		return roof;
	}
	function onRoof(roof: RoofFace, uvn: Vec3): Vec3 {
		// Check before adding the origin: cancellation could otherwise hide an
		// unsupported local chart behind a small but already inaccurate ENU sum.
		requireUvResolution(uvn);
		return add(roof.origin_enu, vectorFromRoof(roof, uvn));
	}
	function put(properties: MapObject, surfaces: number[][][][]) {
		features.push({
			type: "Feature",
			// Renderer identity is opaque; consumers use the explicit properties.
			id: JSON.stringify([properties.kind, properties.object_id]),
			properties,
			geometry:
				surfaces.length === 1
					? { type: "Polygon", coordinates: surfaces[0]! }
					: { type: "MultiPolygon", coordinates: surfaces },
		});
	}
	for (const roof of document.roofs)
		put(
			{
				kind: "roof",
				object_id: roof.id,
				roof_id: roof.id,
				source_id: roof.source_id,
				included: true,
			},
			[
				[roof.boundary_uv, ...roof.holes_uv].map((uvs) =>
					ring(uvs.map((uv) => onRoof(roof, [...uv, 0]))),
				),
			],
		);
	for (const object of [...document.obstacles, ...document.keepouts]) {
		const roof = roofFor(object.roof_id),
			base = object.footprint_uv.map((uv) => onRoof(roof, [...uv, 0])),
			surfaces = [[ring(base)]];
		if ("height_m" in object) {
			const rise = scale(object.extrusion_axis_enu, object.height_m),
				top = base.map((point) => add(point, rise));
			surfaces.push([ring(top)]);
			for (let index = 0; index < base.length; index++) {
				const next = (index + 1) % base.length;
				surfaces.push([
					ring([base[index]!, base[next]!, top[next]!, top[index]!]),
				]);
			}
		}
		put(
			{
				kind: "height_m" in object ? "obstacle" : "keepout",
				object_id: object.id,
				roof_id: roof.id,
				source_id: object.source_id,
				included: true,
			},
			surfaces,
		);
	}
	for (const pose of poses) {
		const roof = roofFor(pose.roof_id),
			array = arrays.get(pose.array_id);
		if (!array || array.roof_id !== roof.id)
			throw new Error("map_geometry_reference_missing");
		const corners = panelCornersUVN(pose).map((point) => onRoof(roof, point));
		// Six faces of the same eight-corner cuboid used in 3D and fit review.
		// A vertical side can project to a zero-area face; no metric face is
		// deleted or used to infer engineering fit from this display geometry.
		const faces = [
			[0, 4, 6, 2],
			[1, 3, 7, 5],
			[0, 2, 3, 1],
			[4, 5, 7, 6],
			[0, 1, 5, 4],
			[2, 6, 7, 3],
		];
		put(
			{
				kind: "module",
				object_id: pose.id,
				roof_id: roof.id,
				source_id: array.source_id,
				included: pose.included,
			},
			faces.map((indices) => [ring(indices.map((index) => corners[index]!))]),
		);
	}
	// Validate even an empty frame; never let a renderer silently clamp origin.
	if (Math.abs(anchor.latitude_deg) > MERCATOR_LATITUDE_LIMIT)
		throw new Error("map_projection_latitude_unsupported");
	return {
		collection: { type: "FeatureCollection", features },
		centre: [anchor.longitude_deg, anchor.latitude_deg],
		bounds:
			features.length === 0
				? null
				: [
						[west, south],
						[east, north],
					],
	};
}
