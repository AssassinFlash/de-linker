/** Manual entry adapters. They do not supply surveying or installation defaults. */
import type { PlaneFrame, RoofFace, Source, Vec2, Vec3 } from "./geometry.ts";
import { sinCosDegrees } from "./coordinates.ts";
import { formatDecimal, parseDecimal } from "./decimal.ts";
import { GeographicBridge } from "./geographic.ts";
import type { GeographicReference } from "./geographic.ts";

export function manualSource(id: string, note: string, rights: string): Source {
	return {
		id,
		kind: "user_measurement",
		note,
		rights_note: rights,
		reference_url: null,
		reference_sha256: null,
		acquired_at_utc: null,
		spatial_precision_m: null,
		calibration_note: "Not recorded.",
		rights_basis: "user_attestation",
		permissions: {
			derive: "permitted",
			retain: "permitted",
			export: "unknown",
		},
	};
}

/** Bearing is the upward normal's horizontal direction, clockwise from project N.
 * V extends down-slope; the origin is the rectangle's high U/V corner. */
export function roofPlane(
	pitch: number,
	bearing: number,
	origin: Vec3,
): PlaneFrame {
	const [sa, ca] = sinCosDegrees(bearing),
		[sb, cb] = sinCosDegrees(pitch);
	return {
		origin_enu: origin,
		u_axis_enu: [ca, -sa, 0],
		v_axis_enu: [sa * cb, ca * cb, -sb],
	};
}

export function rectangularRoof(
	identity: Pick<RoofFace, "id" | "name" | "source_id">,
	dimensions: {
		width: number;
		slopeLength: number;
		pitch: number;
		bearing: number;
		origin: Vec3;
	},
): RoofFace {
	return {
		...identity,
		...roofPlane(dimensions.pitch, dimensions.bearing, dimensions.origin),
		boundary_uv: [
			[0, 0],
			[dimensions.width, 0],
			[dimensions.width, dimensions.slopeLength],
			[0, dimensions.slopeLength],
		],
		holes_uv: [],
	};
}

/** Locate the declared relative Up on the selected vertex's geodetic vertical.
 * Keeping its full E/N/Up avoids assigning ENU-vertical height to a different
 * geographic point away from the project origin. */
export function roofPlaneAtVertex(
	reference: GeographicReference,
	vertex: Vec2,
	pitch: number,
	bearing: number,
	height: number,
): PlaneFrame {
	const bridge = new GeographicBridge(reference),
		base = bridge.forward([...vertex, 0]),
		vertical = bridge.upAt(vertex);
	if (vertical[2] <= 0) throw new Error("unsupported_height_reference");
	const t = (height - base[2]) / vertical[2];
	return roofPlane(pitch, bearing, [
		base[0] + t * vertical[0],
		base[1] + t * vertical[1],
		height,
	]);
}

/** Semicolon separates U/V, so the decimal separator never has two meanings. */
export function parseRing(text: string, locale: string): readonly Vec2[] {
	const lines = text.trim().split(/\r?\n/);
	if (lines.length < 3) throw new Error("geometry_ring_points_required");
	return lines.map((line) => {
		const parts = line.split(";");
		if (parts.length !== 2) throw new Error("geometry_ring_pair_required");
		const u = parseDecimal(parts[0]!, locale),
			v = parseDecimal(parts[1]!, locale);
		if (u === null || v === null)
			throw new Error("geometry_ring_pair_required");
		return [u, v] as const;
	});
}

export const formatRing = (ring: readonly Vec2[], locale: string): string =>
	ring
		.map(
			([u, v]) => `${formatDecimal(u, locale)} ; ${formatDecimal(v, locale)}`,
		)
		.join("\n");

export function parseHoles(
	text: string,
	locale: string,
): readonly (readonly Vec2[])[] {
	return text.trim()
		? text
				.trim()
				.split(/\r?\n\s*\r?\n/)
				.map((ring) => parseRing(ring, locale))
		: [];
}
