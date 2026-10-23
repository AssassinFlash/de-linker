import type { GeometryDocument } from "./geometry.ts";
import type { MapRoofDraft } from "./mapRoofDraft.ts";
import type { MapRingDraft } from "./mapRingDraft.ts";
import type { MapRingTarget } from "./mapDrawingGeometry.ts";
import {
	startMapRoofDraft,
	readMapRoofDraft,
	mapRoofDraftCommand,
} from "./mapRoofDraft.ts";
import {
	startMapRingDraft,
	readMapRingDraft,
	mapRingDraftCommand,
	editMapRingDraft,
} from "./mapRingDraft.ts";
import { readObject } from "../data/readProtocol.ts";
import { readMapPolygon } from "./mapDrawingGeometry.ts";
import { reconcileMapVertex } from "./mapRingEdit.ts";
import type { MapVertexAction } from "./mapRingEdit.ts";

export type MapDrawingDraft = MapRoofDraft | MapRingDraft;
export type MapDrawingIntent =
	| { readonly kind: "new_roof" }
	| { readonly kind: "edit_ring"; readonly target: MapRingTarget };

/** Both operation formats share one grant/CAS journal; valid v1 bytes survive. */
export function readMapDrawingDraft(value: unknown): MapDrawingDraft {
	const row = readObject(value, 24);
	if (row.schema_version === 1) return readMapRoofDraft(row);
	if (row.schema_version === 2) return readMapRingDraft(row);
	throw new Error("map_drawing_recovery_invalid");
}
export function startMapDrawingDraft(
	projectId: string,
	before: GeometryDocument,
	locale: string,
	intent: MapDrawingIntent,
): MapDrawingDraft {
	return intent.kind === "new_roof"
		? startMapRoofDraft(projectId, before, locale)
		: startMapRingDraft(projectId, before, locale, intent.target);
}
export function mapDrawingDraftCommand(draft: MapDrawingDraft) {
	return draft.schema_version === 1
		? mapRoofDraftCommand(draft)
		: mapRingDraftCommand(draft);
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
	return { ...draft, vertices: ring.geographic, prepared_geometry: null };
}
