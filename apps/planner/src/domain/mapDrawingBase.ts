import type { GeometryDocument, Vec2 } from "./geometry.ts";
import { readGeometry } from "./validateGeometry.ts";
import {
	drawingBridge,
	mapPolygon,
	quantizeMapPosition,
	readMapPolygon,
} from "./mapDrawingGeometry.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };

/** Shared local working data, admitted only by the native project/scope grant. */
export interface MapDrawingBase {
	readonly key: string;
	readonly project_id: string;
	readonly locale: string;
	readonly before: GeometryDocument;
	readonly phase: "collecting" | "staged";
	readonly vertices: readonly Vec2[];
	readonly prepared_geometry: GeometryDocument | null;
}
const uuid =
	/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;

/** Each operation separately checks its exact keys and prepared-result proof. */
export function readMapDrawingBase(
	row: Record<string, unknown>,
): MapDrawingBase {
	if (
		typeof row.key !== "string" ||
		!uuid.test(row.key) ||
		typeof row.project_id !== "string" ||
		!/^[a-f0-9]{32}$/.test(row.project_id) ||
		typeof row.locale !== "string" ||
		row.locale.length > 64 ||
		(row.phase !== "collecting" && row.phase !== "staged") ||
		!Array.isArray(row.vertices) ||
		row.vertices.length > policy.max_vertices
	)
		throw new Error("map_drawing_recovery_invalid");
	new Intl.NumberFormat(row.locale);
	const vertices = row.vertices.map((point) => {
		const rounded = quantizeMapPosition(point);
		if (JSON.stringify(rounded) !== JSON.stringify(point))
			throw new Error("map_drawing_recovery_invalid");
		return rounded;
	});
	if (
		new Set(vertices.map((point) => JSON.stringify(point))).size !==
		vertices.length
	)
		throw new Error("map_drawing_recovery_invalid");
	if (row.phase === "staged") readMapPolygon(mapPolygon(vertices));
	const before = readGeometry(row.before, policy);
	drawingBridge(before);
	return {
		key: row.key,
		project_id: row.project_id,
		locale: row.locale,
		before,
		phase: row.phase,
		vertices,
		prepared_geometry:
			row.prepared_geometry === null
				? null
				: readGeometry(row.prepared_geometry, policy),
	};
}
