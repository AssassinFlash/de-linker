import type { GeometryDocument } from "./geometry.ts";
import type { MapRoofDraft } from "./mapRoofDraft.ts";
import type { MapRingDraft } from "./mapRingDraft.ts";
import type { MapFeatureDraft, MapFeatureTarget } from "./mapFeatureDraft.ts";
import {
	startMapFeatureDraft,
	readMapFeatureDraft,
	mapFeatureDraftCommand,
} from "./mapFeatureDraft.ts";
import { appendMapPrefix } from "./mapDrawingBase.ts";
import type { MapRingTarget } from "./mapDrawingGeometry.ts";
import {
	startMapRoofDraft,
	readMapRoofDraft,
	mapRoofDraftCommand,
	appendMapRoofVertex,
} from "./mapRoofDraft.ts";
import {
	startMapRingDraft,
	readMapRingDraft,
	mapRingDraftCommand,
	editMapRingDraft,
} from "./mapRingDraft.ts";
import { readObject } from "../data/readProtocol.ts";
import { readMapPolygon, mapRingMetadata } from "./mapDrawingGeometry.ts";
import { reconcileMapVertex } from "./mapRingEdit.ts";
import type { MapVertexAction } from "./mapRingEdit.ts";

export type MapDrawingDraft = MapRoofDraft | MapRingDraft | MapFeatureDraft;
export type MapDrawingIntent =
	| { readonly kind: "new_roof" }
	| { readonly kind: "new_feature"; readonly target: MapFeatureTarget }
	| { readonly kind: "edit_ring"; readonly target: MapRingTarget };

/** All operation formats share one grant/CAS journal; valid v1/v2 bytes survive. */
export function readMapDrawingDraft(value: unknown): MapDrawingDraft {
	const row = readObject(value, 24);
	if (row.schema_version === 1) return readMapRoofDraft(row);
	if (row.schema_version === 2) return readMapRingDraft(row);
	if (row.schema_version === 3) return readMapFeatureDraft(row);
	throw new Error("map_drawing_recovery_invalid");
}
export function startMapDrawingDraft(
	projectId: string,
	before: GeometryDocument,
	locale: string,
	intent: MapDrawingIntent,
): MapDrawingDraft {
	if (intent.kind === "new_roof")
		return startMapRoofDraft(projectId, before, locale);
	if (intent.kind === "new_feature")
		return startMapFeatureDraft(projectId, before, locale, intent.target);
	return startMapRingDraft(projectId, before, locale, intent.target);
}
export function mapDrawingDraftCommand(draft: MapDrawingDraft) {
	return draft.schema_version === 1
		? mapRoofDraftCommand(draft)
		: draft.schema_version === 2
			? mapRingDraftCommand(draft)
			: mapFeatureDraftCommand(draft);
}
export function mapDrawingReviewTarget(draft: MapDrawingDraft) {
	if (draft.schema_version === 1) {
		const id = "roof_" + draft.key.replaceAll("-", "");
		return { id, roof: id, invalid: "invalid_roof_polygon" };
	}
	const invalid =
		draft.target.kind === "obstacle"
			? "invalid_obstacle_polygon"
			: draft.target.kind === "keepout"
				? "invalid_keepout_polygon"
				: "invalid_roof_polygon";
	if (draft.schema_version === 3)
		return {
			id:
				draft.target.kind === "hole" ? draft.target.roof_id : draft.object_id!,
			roof: draft.target.roof_id,
			invalid,
		};
	return {
		id: "roof_id" in draft.target ? draft.target.roof_id : draft.target.id,
		roof: mapRingMetadata(draft.before, draft.target).roof_id,
		invalid,
	};
}
export function mapDrawingVertices(
	draft: MapRoofDraft | MapFeatureDraft,
	vertices: MapDrawingDraft["vertices"],
): MapRoofDraft | MapFeatureDraft {
	return draft.schema_version === 1
		? { ...draft, vertices, prepared_geometry: null }
		: {
				...draft,
				vertices,
				fields: { ...draft.fields, source_confirmed: false },
				prepared_geometry: null,
			};
}
export function appendMapDrawingVertex(draft: MapDrawingDraft, point: unknown) {
	if (draft.schema_version === 1) return appendMapRoofVertex(draft, point);
	if (draft.schema_version === 2) throw new Error("unexpected_append");
	return mapDrawingVertices(draft, appendMapPrefix(draft, point));
}
export function editMapDrawingVertex(
	draft: MapDrawingDraft,
	geometry: unknown,
	action: MapVertexAction,
): MapDrawingDraft {
	if (draft.schema_version === 2)
		return editMapRingDraft(draft, geometry, action);
	const ring = reconcileMapVertex(
		{ geographic: draft.vertices, metric: draft.vertices },
		readMapPolygon(geometry),
		action,
		(point) => point,
	);
	return mapDrawingVertices(draft, ring.geographic);
}
