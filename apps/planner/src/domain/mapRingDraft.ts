import type { GeometryDocument, Vec2 } from "./geometry.ts";
import type { MapDrawingBase } from "./mapDrawingBase.ts";
import { readMapDrawingBase } from "./mapDrawingBase.ts";
import {
	bindMapRing,
	drawingBridge,
	editMapVertex,
	mapRingCommand,
} from "./mapDrawingGeometry.ts";
import type { MapRingBinding, MapRingTarget } from "./mapDrawingGeometry.ts";
import type { MapVertexAction } from "./mapRingEdit.ts";
import { geographicOnRoof } from "./geographic.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { sameJson } from "./draft.ts";
import { readObject } from "../data/readProtocol.ts";

/** An existing ring retains its metric pairs; the map is only an edit handle. */
export interface MapRingDraft extends MapDrawingBase {
	readonly schema_version: 2;
	readonly phase: "staged";
	readonly target: MapRingTarget;
	readonly metric_vertices: readonly Vec2[];
	readonly source_confirmed: boolean;
}

function readTarget(value: unknown): MapRingTarget {
	const row = readObject(value, 4),
		keys = Object.keys(row).sort().join();
	if (
		(row.kind === "obstacle" || row.kind === "keepout") &&
		keys === "id,kind" &&
		typeof row.id === "string"
	)
		return { kind: row.kind, id: row.id };
	if (typeof row.roof_id === "string") {
		if (row.kind === "roof_boundary" && keys === "kind,roof_id")
			return { kind: row.kind, roof_id: row.roof_id };
		if (
			row.kind === "roof_hole" &&
			keys === "index,kind,roof_id" &&
			typeof row.index === "number" &&
			Number.isSafeInteger(row.index) &&
			row.index >= 0
		)
			return { kind: row.kind, roof_id: row.roof_id, index: row.index };
	}
	throw new Error("map_drawing_recovery_invalid");
}
function binding(draft: MapRingDraft): MapRingBinding {
	return {
		...bindMapRing(draft.before, draft.target),
		ring: { geographic: draft.vertices, metric: draft.metric_vertices },
	};
}
export function startMapRingDraft(
	projectId: string,
	before: GeometryDocument,
	locale: string,
	target: MapRingTarget,
): MapRingDraft {
	const initial = bindMapRing(before, target);
	return readMapRingDraft({
		schema_version: 2,
		key: crypto.randomUUID(),
		project_id: projectId,
		locale,
		before: initial.before,
		phase: "staged",
		target: initial.target,
		vertices: initial.ring.geographic,
		metric_vertices: initial.ring.metric,
		source_confirmed: false,
		prepared_geometry: null,
	});
}
export function readMapRingDraft(value: unknown): MapRingDraft {
	const row = readObject(value, 24);
	if (
		Object.keys(row).sort().join() !==
			[
				"schema_version",
				"key",
				"project_id",
				"locale",
				"before",
				"phase",
				"target",
				"vertices",
				"metric_vertices",
				"source_confirmed",
				"prepared_geometry",
			]
				.sort()
				.join() ||
		row.schema_version !== 2 ||
		row.phase !== "staged" ||
		typeof row.source_confirmed !== "boolean"
	)
		throw new Error("map_drawing_recovery_invalid");
	const base = readMapDrawingBase(row),
		target = readTarget(row.target),
		initial = bindMapRing(base.before, target),
		original = new Map(
			initial.ring.geographic.map((point, index) => [
				JSON.stringify(point),
				initial.ring.metric[index]!,
			]),
		),
		bridge = drawingBridge(base.before);
	if (
		!Array.isArray(row.metric_vertices) ||
		row.metric_vertices.length !== base.vertices.length
	)
		throw new Error("map_drawing_recovery_invalid");
	const metric = row.metric_vertices.map((point: unknown, index): Vec2 => {
		if (
			!Array.isArray(point) ||
			point.length !== 2 ||
			!point.every((n: unknown) => typeof n === "number" && Number.isFinite(n))
		)
			throw new Error("map_drawing_recovery_invalid");
		const geographic = base.vertices[index]!,
			untouched = original.get(JSON.stringify(geographic));
		// An original display handle keeps its exact input UV. A changed/new pair
		// must be the accepted projection; raw storage cannot supply unrelated UV.
		if (
			!sameJson(point, untouched) &&
			!sameJson(point, geographicOnRoof(bridge, initial.plane, geographic))
		)
			throw new Error("map_drawing_recovery_invalid");
		return [point[0] as number, point[1] as number];
	});
	const draft: MapRingDraft = {
		...base,
		schema_version: 2,
		phase: "staged",
		target,
		metric_vertices: metric,
		source_confirmed: row.source_confirmed,
	};
	// Run the existing coordinate/resource/reference validator even before the
	// user confirms the source. This is not a polygon topology review.
	const command = mapRingCommand(binding(draft));
	if (
		draft.prepared_geometry &&
		(!draft.source_confirmed ||
			!sameJson(
				draft.prepared_geometry,
				applyGeometryCommand(draft.before, command),
			))
	)
		throw new Error("map_drawing_recovery_invalid");
	return draft;
}
export function editMapRingDraft(
	draft: MapRingDraft,
	geometry: unknown,
	action: MapVertexAction,
): MapRingDraft {
	const next = editMapVertex(binding(draft), geometry, action);
	if (
		sameJson(next.ring, {
			metric: draft.metric_vertices,
			geographic: draft.vertices,
		})
	)
		return draft;
	return {
		...draft,
		vertices: next.ring.geographic,
		metric_vertices: next.ring.metric,
		source_confirmed: false,
		prepared_geometry: null,
	};
}
export function mapRingDraftCommand(draft: MapRingDraft) {
	if (!draft.source_confirmed)
		throw Object.assign(new Error("map_drawing_confirmation_required"), {
			field: "source_confirmed",
		});
	return mapRingCommand(binding(draft));
}

/** Selection determines the available rings; module/array selection is separate. */
export function mapRingTargets(
	document: GeometryDocument,
	selected: string | null,
): readonly MapRingTarget[] {
	const roof = document.roofs.find((value) => value.id === selected);
	if (roof)
		return [
			{ kind: "roof_boundary", roof_id: roof.id },
			...roof.holes_uv.map((_, index): MapRingTarget => ({
				kind: "roof_hole",
				roof_id: roof.id,
				index,
			})),
		];
	if (document.obstacles.some((value) => value.id === selected))
		return [{ kind: "obstacle", id: selected! }];
	if (document.keepouts.some((value) => value.id === selected))
		return [{ kind: "keepout", id: selected! }];
	return [];
}
