/** Strict boundary between a geographic interaction buffer and metric project
 * edits. No renderer properties, helper IDs or camera state enter the model. */
import type {
	GeometryDocument,
	Keepout,
	Obstacle,
	PlaneFrame,
	RoofFace,
	Vec2,
} from "./geometry.ts";
import type { GeometryCommand, GeometryEdit } from "./geometryCommands.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { GeographicBridge, geographicOnRoof } from "./geographic.ts";
import { add, vectorFromRoof } from "./coordinates.ts";
import { requireUvResolution } from "./geometryNumerics.ts";
import { roofPlaneAtVertex } from "./geometryEditing.ts";
import type { MapRing, MapVertexAction } from "./mapRingEdit.ts";
import { reconcileMapVertex } from "./mapRingEdit.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };

// Pinned Terra Draw/adapter display precision, not source or survey accuracy.
export const MAP_HANDLE_DECIMALS = 9;
// Same pinned Mercator support boundary as geographicMapGeometry.
const MAX_LATITUDE = 85.051129;

export type MapRingTarget =
	| { readonly kind: "roof_boundary"; readonly roof_id: string }
	| {
			readonly kind: "roof_hole";
			readonly roof_id: string;
			readonly index: number;
	  }
	| { readonly kind: "obstacle"; readonly id: string }
	| { readonly kind: "keepout"; readonly id: string };

export interface MapRingBinding {
	readonly before: GeometryDocument;
	readonly target: MapRingTarget;
	readonly plane: PlaneFrame;
	readonly ring: MapRing;
}

export function drawingBridge(document: GeometryDocument): GeographicBridge {
	const frame = document.coordinate_system,
		anchor = frame.anchor;
	if (!anchor || frame.north_reference !== "true_north")
		throw new Error("map_geographic_reference_required");
	return new GeographicBridge({
		schema_version: 1,
		method: "wgs84_cart_topocentric_v1",
		longitude_deg: anchor.longitude_deg,
		latitude_deg: anchor.latitude_deg,
		ellipsoid_height_m: 0,
		height_basis: "zero_height_horizontal_convention",
	});
}

function position(value: unknown): Vec2 {
	if (
		!Array.isArray(value) ||
		value.length !== 2 ||
		!value.every((n: unknown) => typeof n === "number" && Number.isFinite(n)) ||
		Math.abs(value[0] as number) > 180 ||
		Math.abs(value[1] as number) > MAX_LATITUDE
	)
		throw new Error("map_drawing_position_invalid");
	return [value[0] as number, value[1] as number];
}

/** Pinned Terra limitPrecision implementation. This changes only the display
 * handle; matching the SDK's rounding is required for stable vertex identity. */
export function quantizeMapPosition(value: unknown): Vec2 {
	const point = position(value),
		factor = 10 ** MAP_HANDLE_DECIMALS;
	return [
		Math.round(point[0] * factor) / factor,
		Math.round(point[1] * factor) / factor,
	];
}

/** Only one explicitly bound ring is editable in Terra. Never pass roof holes,
 * extruded faces, modules or the complete map overlay to its polygon store. */
export function readMapPolygon(value: unknown): readonly Vec2[] {
	if (value === null || typeof value !== "object" || Array.isArray(value))
		throw new Error("map_drawing_polygon_invalid");
	const geometry = value as Record<string, unknown>,
		coordinates = geometry.coordinates;
	if (
		geometry.type !== "Polygon" ||
		!Array.isArray(coordinates) ||
		coordinates.length !== 1 ||
		!Array.isArray(coordinates[0]) ||
		coordinates[0].length < 4 ||
		coordinates[0].length > policy.max_vertices + 1
	)
		throw new Error("map_drawing_polygon_invalid");
	const closed = coordinates[0].map(position),
		first = closed[0]!,
		last = closed.at(-1)!;
	if (first[0] !== last[0] || first[1] !== last[1])
		throw new Error("map_drawing_ring_not_closed");
	const ring = closed.slice(0, -1);
	if (new Set(ring.map((point) => JSON.stringify(point))).size !== ring.length)
		throw new Error("map_vertex_identity_ambiguous");
	return ring;
}

export function mapPolygon(ring: readonly Vec2[]) {
	if (ring.length < 3 || ring.length > policy.max_vertices)
		throw new Error("map_drawing_polygon_invalid");
	return {
		type: "Polygon" as const,
		coordinates: [[...ring.map((point) => [...point]), [...ring[0]!]]],
	};
}

function targetObject(document: GeometryDocument, target: MapRingTarget) {
	if (target.kind === "obstacle" || target.kind === "keepout") {
		const items =
			target.kind === "obstacle" ? document.obstacles : document.keepouts;
		const object = items.find((item) => item.id === target.id),
			roof = document.roofs.find((item) => item.id === object?.roof_id);
		if (!object || !roof) throw new Error("map_drawing_target_missing");
		return { object, roof, ring: object.footprint_uv };
	}
	const roof = document.roofs.find((item) => item.id === target.roof_id);
	if (!roof) throw new Error("map_drawing_target_missing");
	const ring =
		target.kind === "roof_boundary"
			? roof.boundary_uv
			: Number.isSafeInteger(target.index) && target.index >= 0
				? roof.holes_uv[target.index]
				: undefined;
	if (!ring) throw new Error("map_drawing_target_missing");
	return { object: roof, roof, ring };
}

export function mapRingMetadata(
	document: GeometryDocument,
	target: MapRingTarget,
) {
	const { object, roof } = targetObject(document, target);
	return {
		name: object.name,
		roof_id: roof.id,
		source: document.sources.find((source) => source.id === object.source_id)!,
	};
}

/** Freeze the whole frame: a hole's array index is not a permanent object ID. */
export function bindMapRing(
	document: GeometryDocument,
	target: MapRingTarget,
): MapRingBinding {
	const before = structuredClone(document),
		{ roof, ring } = targetObject(before, target),
		bridge = drawingBridge(before);
	const geographic = ring.map((uv): Vec2 => {
		requireUvResolution(uv);
		const enu = add(roof.origin_enu, vectorFromRoof(roof, [...uv, 0]));
		requireUvResolution(enu);
		const [longitude, latitude] = bridge.inverse(enu);
		return quantizeMapPosition([longitude, latitude]);
	});
	// Quantised handles must not merge distinct original vertices. Refuse this
	// editing path and retain numeric entry; never snap the metric source.
	readMapPolygon(mapPolygon(geographic));
	return {
		before,
		target: { ...target },
		plane: roof,
		ring: { metric: ring, geographic },
	};
}

export function editMapVertex(
	binding: MapRingBinding,
	geometry: unknown,
	action: MapVertexAction,
): MapRingBinding {
	const bridge = drawingBridge(binding.before),
		ring = reconcileMapVertex(
			binding.ring,
			readMapPolygon(geometry),
			action,
			(point) => geographicOnRoof(bridge, binding.plane, point),
		);
	return ring === binding.ring ? binding : { ...binding, ring };
}

function checkedGroup(
	before: GeometryDocument,
	edit: GeometryEdit,
): GeometryCommand {
	const command: GeometryCommand = { type: "group", before, edits: [edit] };
	applyGeometryCommand(before, command);
	return command;
}

export function mapRingCommand(binding: MapRingBinding): GeometryCommand {
	const { before, target, ring } = binding,
		{ object, roof } = targetObject(before, target);
	if (target.kind === "roof_boundary" || target.kind === "roof_hole")
		return checkedGroup(before, {
			type: "put_roof",
			before: roof,
			value: {
				...roof,
				...(target.kind === "roof_boundary"
					? { boundary_uv: ring.metric }
					: {
							holes_uv: roof.holes_uv.map((hole, index) =>
								index === target.index ? ring.metric : hole,
							),
						}),
			},
		});
	if (target.kind === "obstacle")
		return checkedGroup(before, {
			type: "put_obstacle",
			before: object as Obstacle,
			value: { ...(object as Obstacle), footprint_uv: ring.metric },
		});
	return checkedGroup(before, {
		type: "put_keepout",
		before: object as Keepout,
		value: { ...(object as Keepout), footprint_uv: ring.metric },
	});
}

export type NewMapShape =
	| {
			readonly kind: "roof";
			readonly identity: Pick<RoofFace, "id" | "name" | "source_id">;
			readonly pitch_deg: number;
			readonly bearing_deg: number;
			/** Frozen geographic position at which relative height was supplied.
			 * It remains fixed when the SDK reorders or deletes boundary vertices. */
			readonly height_reference_position: Vec2;
			readonly reference_height_m: number;
	  }
	| { readonly kind: "hole"; readonly roof_id: string }
	| {
			readonly kind: "obstacle";
			readonly value: Omit<Obstacle, "footprint_uv">;
	  }
	| {
			readonly kind: "keepout";
			readonly value: Omit<Keepout, "footprint_uv">;
	  };

/** Required physical/source fields are supplied explicitly. A map never
 * supplies an assumed flat roof, zero height or obstacle extrusion direction. */
export function newMapShapeCommand(
	before: GeometryDocument,
	shape: NewMapShape,
	geometry: unknown,
): GeometryCommand {
	const ring = readMapPolygon(geometry),
		bridge = drawingBridge(before);
	if (shape.kind === "roof") {
		if (
			!Number.isFinite(shape.pitch_deg) ||
			shape.pitch_deg < 0 ||
			shape.pitch_deg >= 90 ||
			!Number.isFinite(shape.bearing_deg) ||
			shape.bearing_deg < 0 ||
			shape.bearing_deg >= 360 ||
			!Number.isFinite(shape.reference_height_m)
		)
			throw new Error("map_drawing_plane_invalid");
		const plane = roofPlaneAtVertex(
			bridge.reference,
			position(shape.height_reference_position),
			shape.pitch_deg,
			shape.bearing_deg,
			shape.reference_height_m,
		);
		return checkedGroup(before, {
			type: "put_roof",
			before: null,
			value: {
				...shape.identity,
				...plane,
				boundary_uv: ring.map((point) =>
					geographicOnRoof(bridge, plane, point),
				),
				holes_uv: [],
			},
		});
	}
	const roofId = shape.kind === "hole" ? shape.roof_id : shape.value.roof_id,
		roof = before.roofs.find((item) => item.id === roofId);
	if (!roof) throw new Error("map_drawing_target_missing");
	const footprint = ring.map((point) => geographicOnRoof(bridge, roof, point));
	if (shape.kind === "hole")
		return checkedGroup(before, {
			type: "put_roof",
			before: roof,
			value: { ...roof, holes_uv: [...roof.holes_uv, footprint] },
		});
	if (shape.kind === "obstacle")
		return checkedGroup(before, {
			type: "put_obstacle",
			before: null,
			value: { ...shape.value, footprint_uv: footprint },
		});
	return checkedGroup(before, {
		type: "put_keepout",
		before: null,
		value: { ...shape.value, footprint_uv: footprint },
	});
}
