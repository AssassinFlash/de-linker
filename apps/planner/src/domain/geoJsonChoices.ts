import policy from "../contracts/geometry-policy.json" with { type: "json" };
import type { Vec2 } from "./geometry.ts";

export interface GeoJsonChoice {
	readonly featureIndex: number;
	readonly polygonIndex: number;
	readonly name: string | null;
	readonly firstPoint: Vec2;
	readonly openingCount: number;
	readonly vertexCount: number;
}

const object = (value: unknown): Record<string, unknown> | null =>
	value !== null && typeof value === "object" && !Array.isArray(value)
		? (value as Record<string, unknown>)
		: null;

// UI display/default-name resource policy, in Unicode code points. This does
// not alter source bytes, feature identity or any engineering precision.
const maxLabelCodePoints = 256;
function displayName(value: string): string {
	const points = Array.from(value.trim());
	return points.length <= maxLabelCodePoints
		? points.join("")
		: points.slice(0, maxLabelCodePoints - 1).join("") + "…";
}

/** File inspection offers choices, never repairs or rewrites original bytes.
 * The authoritative intake still validates the complete selected shape,
 * duplicate JSON members, projection, topology and numerical support. */
export function geoJsonChoices(content: string): readonly GeoJsonChoice[] {
	const bytes = Uint8Array.from(atob(content), (char) => char.charCodeAt(0)),
		root = object(
			JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)),
		);
	if (!root || "crs" in root) throw new Error("unsupported_geojson");
	const features = root.type === "FeatureCollection" ? root.features : [root];
	if (!Array.isArray(features)) throw new Error("unsupported_geojson");
	const choices: GeoJsonChoice[] = [];
	features.forEach((value, featureIndex) => {
		const feature = object(value);
		if (!feature || "crs" in feature) return;
		if (root.type === "FeatureCollection" && feature.type !== "Feature") return;
		const shape =
			feature.type === "Feature" ? object(feature.geometry) : feature;
		if (!shape || "crs" in shape) return;
		const polygons =
			shape.type === "Polygon"
				? [shape.coordinates]
				: shape.type === "MultiPolygon"
					? shape.coordinates
					: [];
		if (!Array.isArray(polygons)) return;
		const properties = object(feature.properties),
			name =
				typeof properties?.name === "string" && properties.name.trim()
					? displayName(properties.name)
					: typeof feature.id === "string"
						? displayName(feature.id)
						: null;
		polygons.forEach((rings, polygonIndex) => {
			if (!Array.isArray(rings) || !rings.length) return;
			let vertexCount = 0;
			for (const ring of rings) {
				if (!Array.isArray(ring) || ring.length < 4) return;
				vertexCount += ring.length;
				for (const point of ring)
					if (
						!Array.isArray(point) ||
						point.length !== 2 ||
						!point.every(
							(value) => typeof value === "number" && Number.isFinite(value),
						) ||
						Math.abs(point[0]) > 180 ||
						Math.abs(point[1]) > 90
					)
						return;
				if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1])
					return;
			}
			if (vertexCount > policy.max_vertices) return;
			choices.push({
				featureIndex,
				polygonIndex,
				name,
				firstPoint: [rings[0][0][0], rings[0][0][1]],
				openingCount: rings.length - 1,
				vertexCount,
			});
		});
	});
	if (!choices.length) throw new Error("no_supported_roof_polygon");
	return choices;
}
