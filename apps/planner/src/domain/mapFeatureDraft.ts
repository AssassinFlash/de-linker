/** A new feature is drawn in its recorded parent plane; it cannot create a
 * second roof, infer a height or replace a source declaration. */
import type { GeometryDocument } from "./geometry.ts";
import type { MapDrawingBase } from "./mapDrawingBase.ts";
import { readMapDrawingBase } from "./mapDrawingBase.ts";
import { mapPolygon, newMapShapeCommand } from "./mapDrawingGeometry.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { cross } from "./coordinates.ts";
import { parseDecimal } from "./decimal.ts";
import { sameJson } from "./draft.ts";
import { readObject } from "../data/readProtocol.ts";

export interface MapFeatureTarget {
	readonly kind: "hole" | "obstacle" | "keepout";
	readonly roof_id: string;
}
export interface MapFeatureFields {
	readonly name: string;
	readonly height: string;
	readonly axis: "" | "normal" | "vertical";
	readonly reason: string;
	readonly source_id: string;
	readonly source_confirmed: boolean;
}
export interface MapFeatureDraft extends MapDrawingBase {
	readonly schema_version: 3;
	readonly target: MapFeatureTarget;
	/** Separate-copy changes the journal key, never this domain identity. */
	readonly object_id: string | null;
	readonly fields: MapFeatureFields;
}
export function mapFeatureRoof(
	draft: Pick<MapFeatureDraft, "before" | "target">,
) {
	const roof = draft.before.roofs.find(
		(value) => value.id === draft.target.roof_id,
	);
	if (!roof) throw new Error("map_drawing_target_missing");
	return roof;
}
export function mapFeatureSource(draft: MapFeatureDraft) {
	const source = draft.before.sources.find(
		(value) => value.id === draft.fields.source_id,
	);
	if (!source) throw new Error("map_drawing_recovery_invalid");
	return source;
}
export function startMapFeatureDraft(
	projectId: string,
	before: GeometryDocument,
	locale: string,
	target: MapFeatureTarget,
): MapFeatureDraft {
	const roof = mapFeatureRoof({ before, target });
	return readMapFeatureDraft({
		schema_version: 3,
		key: crypto.randomUUID(),
		project_id: projectId,
		locale,
		before: structuredClone(before),
		phase: "collecting",
		vertices: [],
		target: { ...target },
		object_id:
			target.kind === "hole"
				? null
				: target.kind + "_" + crypto.randomUUID().replaceAll("-", ""),
		fields: {
			name: "",
			height: "",
			axis: "",
			reason: "",
			source_id: roof.source_id,
			source_confirmed: false,
		},
		prepared_geometry: null,
	});
}
export function readMapFeatureDraft(value: unknown): MapFeatureDraft {
	const row = readObject(value, 24);
	if (
		row.schema_version !== 3 ||
		Object.keys(row).sort().join() !==
			[
				"schema_version",
				"key",
				"project_id",
				"locale",
				"before",
				"phase",
				"vertices",
				"target",
				"object_id",
				"fields",
				"prepared_geometry",
			]
				.sort()
				.join()
	)
		throw new Error("map_drawing_recovery_invalid");
	const base = readMapDrawingBase(row),
		target = readObject(row.target, 2),
		fields = readObject(row.fields, 6);
	if (
		Object.keys(target).sort().join() !== "kind,roof_id" ||
		!["hole", "obstacle", "keepout"].includes(target.kind as string) ||
		typeof target.roof_id !== "string" ||
		Object.keys(fields).sort().join() !==
			"axis,height,name,reason,source_confirmed,source_id" ||
		["name", "height", "reason", "source_id"].some(
			(name) =>
				typeof fields[name] !== "string" ||
				(fields[name] as string).length > 4096,
		) ||
		!["", "normal", "vertical"].includes(fields.axis as string) ||
		typeof fields.source_confirmed !== "boolean"
	)
		throw new Error("map_drawing_recovery_invalid");
	const draft: MapFeatureDraft = {
		...base,
		schema_version: 3,
		target: target as unknown as MapFeatureTarget,
		object_id: row.object_id as string | null,
		fields: fields as unknown as MapFeatureFields,
	};
	const roof = mapFeatureRoof(draft);
	mapFeatureSource(draft);
	if (
		(target.kind === "hole"
			? row.object_id !== null ||
				fields.name !== "" ||
				fields.height !== "" ||
				fields.axis !== "" ||
				fields.reason !== "" ||
				fields.source_id !== roof.source_id
			: typeof row.object_id !== "string" ||
				!new RegExp("^" + target.kind + "_[a-f0-9]{32}$").test(
					row.object_id,
				)) ||
		(target.kind === "keepout" &&
			(fields.height !== "" || fields.axis !== "")) ||
		(target.kind === "obstacle" && fields.reason !== "") ||
		(base.phase === "collecting" &&
			(fields.source_confirmed || base.prepared_geometry))
	)
		throw new Error("map_drawing_recovery_invalid");
	if (
		draft.prepared_geometry &&
		!sameJson(
			draft.prepared_geometry,
			applyGeometryCommand(draft.before, mapFeatureDraftCommand(draft)),
		)
	)
		throw new Error("map_drawing_recovery_invalid");
	return draft;
}
export function mapFeatureDraftCommand(draft: MapFeatureDraft) {
	const invalid = (field: keyof MapFeatureFields) =>
		Object.assign(new Error("map_drawing_fields_invalid"), { field });
	if (draft.phase !== "staged" || !draft.fields.source_confirmed)
		throw invalid("source_confirmed");
	const roof = mapFeatureRoof(draft),
		source = mapFeatureSource(draft),
		fields = draft.fields;
	if (draft.target.kind === "hole")
		return newMapShapeCommand(
			draft.before,
			{ kind: "hole", roof_id: roof.id },
			mapPolygon(draft.vertices),
		);
	const text = (key: "name" | "reason") => {
		const value = fields[key].trim();
		if (!value) throw invalid(key);
		return value;
	};
	const identity = {
		id: draft.object_id!,
		name: text("name"),
		roof_id: roof.id,
		source_id: source.id,
	};
	if (draft.target.kind === "keepout")
		return newMapShapeCommand(
			draft.before,
			{ kind: "keepout", value: { ...identity, reason: text("reason") } },
			mapPolygon(draft.vertices),
		);
	let height: number | null;
	try {
		height = parseDecimal(fields.height, draft.locale);
	} catch {
		throw invalid("height");
	}
	if (height === null || !Number.isFinite(height) || height <= 0)
		throw invalid("height");
	if (fields.axis !== "normal" && fields.axis !== "vertical")
		throw invalid("axis");
	return newMapShapeCommand(
		draft.before,
		{
			kind: "obstacle",
			value: {
				...identity,
				height_m: height,
				extrusion_axis_enu:
					fields.axis === "normal"
						? cross(roof.u_axis_enu, roof.v_axis_enu)
						: [0, 0, 1],
			},
		},
		mapPolygon(draft.vertices),
	);
}
