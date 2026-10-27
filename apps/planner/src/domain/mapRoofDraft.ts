/** An unfinished manual drawing is local working data, never project geometry.
 * Only explicit source/plane confirmation produces one metric project command. */
import type { GeometryDocument, Vec2 } from "./geometry.ts";
import type { GeometryCommand } from "./geometryCommands.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { manualSource } from "./geometryEditing.ts";
import {
	drawingBridge,
	mapPolygon,
	newMapShapeCommand,
	quantizeMapPosition,
} from "./mapDrawingGeometry.ts";
import { readGeometry } from "./validateGeometry.ts";
import { readObject } from "../data/readProtocol.ts";
import { parseDecimal } from "./decimal.ts";
import { sameJson } from "./draft.ts";
import {
	appendMapPrefix,
	mapDrawingTextLimit,
	readMapDrawingBase,
} from "./mapDrawingBase.ts";
import type { MapDrawingBase } from "./mapDrawingBase.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };

export interface MapRoofFields {
	readonly name: string;
	readonly pitch: string;
	readonly bearing: string;
	readonly height: string;
	readonly source: string;
	readonly rights: string;
	readonly precision: string;
	readonly calibration: string;
	readonly export: "unknown" | "permitted" | "prohibited";
	readonly permission: boolean;
}
export interface MapRoofDraft extends MapDrawingBase {
	readonly schema_version: 1;
	readonly height_reference_position: Vec2 | null;
	readonly fields: MapRoofFields;
}

export function startMapRoofDraft(
	projectId: string,
	before: GeometryDocument,
	locale: string,
): MapRoofDraft {
	drawingBridge(before);
	return readMapRoofDraft({
		schema_version: 1,
		key: crypto.randomUUID(),
		project_id: projectId,
		locale,
		before: structuredClone(before),
		phase: "collecting",
		vertices: [],
		height_reference_position: null,
		fields: {
			name: "",
			pitch: "",
			bearing: "",
			height: "",
			source: "",
			rights: "",
			precision: "",
			calibration: "",
			export: "unknown",
			permission: false,
		},
		prepared_geometry: null,
	});
}

/** Browser storage is untrusted. No coercion, SDK snapshots or unknown fields. */
export function readMapRoofDraft(value: unknown): MapRoofDraft {
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
				"vertices",
				"height_reference_position",
				"fields",
				"prepared_geometry",
			]
				.sort()
				.join() ||
		row.schema_version !== 1
	)
		throw new Error("map_drawing_recovery_invalid");
	const base = readMapDrawingBase(row);
	const reference =
		row.height_reference_position === null
			? null
			: quantizeMapPosition(row.height_reference_position);
	if (
		(base.vertices.length > 0 && reference === null) ||
		(reference !== null &&
			JSON.stringify(reference) !==
				JSON.stringify(row.height_reference_position))
	)
		throw new Error("map_drawing_recovery_invalid");
	const fields = readObject(row.fields);
	const names = [
		"name",
		"pitch",
		"bearing",
		"height",
		"source",
		"rights",
		"precision",
		"calibration",
	] as const;
	if (
		Object.keys(fields).sort().join() !==
			[...names, "export", "permission"].sort().join() ||
		names.some(
			(name) =>
				typeof fields[name] !== "string" ||
				(fields[name] as string).length > mapDrawingTextLimit,
		) ||
		typeof fields.permission !== "boolean" ||
		!["unknown", "permitted", "prohibited"].includes(fields.export as string)
	)
		throw new Error("map_drawing_recovery_invalid");
	const draft: MapRoofDraft = {
		...base,
		schema_version: 1,
		height_reference_position: reference,
		fields: fields as unknown as MapRoofFields,
	};
	if (
		draft.prepared_geometry &&
		!sameJson(
			draft.prepared_geometry,
			applyGeometryCommand(draft.before, mapRoofDraftCommand(draft)),
		)
	)
		throw new Error("map_drawing_recovery_invalid");
	return draft;
}

export function appendMapRoofVertex(
	draft: MapRoofDraft,
	value: unknown,
): MapRoofDraft {
	const vertices = appendMapPrefix(draft, value);
	return {
		...draft,
		vertices,
		height_reference_position:
			draft.height_reference_position ?? vertices.at(-1)!,
		prepared_geometry: null,
	};
}

export function mapRoofDraftCommand(draft: MapRoofDraft): GeometryCommand {
	if (
		draft.phase !== "staged" ||
		!draft.height_reference_position ||
		!draft.fields.permission
	)
		throw new Error("map_drawing_confirmation_required");
	const fields = draft.fields;
	const invalid = (field: keyof MapRoofFields) =>
		Object.assign(new Error("map_drawing_fields_invalid"), { field });
	function text(name: "name" | "source" | "rights" | "calibration") {
		const value = fields[name].trim();
		if (!value) throw invalid(name);
		return value;
	}
	function number(
		name: "pitch" | "bearing" | "height" | "precision",
		optional = false,
	) {
		let value: number | null;
		try {
			value = parseDecimal(fields[name], draft.locale);
		} catch {
			throw invalid(name);
		}
		if (value === null && !optional) throw invalid(name);
		if (
			value !== null &&
			((name === "pitch" && (value < 0 || value >= 90)) ||
				(name === "bearing" && (value < 0 || value >= 360)) ||
				(name === "precision" && value < 0))
		)
			throw invalid(name);
		return value;
	}
	const id = draft.key.replaceAll("-", ""),
		source = {
			...manualSource("source_" + id, text("source"), text("rights")),
			kind: "user_drawing" as const,
			spatial_precision_m: number("precision", true),
			calibration_note: text("calibration"),
			permissions: {
				derive: "permitted" as const,
				retain: "permitted" as const,
				export: fields.export,
			},
		},
		withSource = readGeometry(
			{ ...draft.before, sources: [...draft.before.sources, source] },
			policy,
		),
		shape = newMapShapeCommand(
			withSource,
			{
				kind: "roof",
				identity: {
					id: "roof_" + id,
					name: text("name"),
					source_id: source.id,
				},
				pitch_deg: number("pitch")!,
				bearing_deg: number("bearing")!,
				height_reference_position: draft.height_reference_position,
				reference_height_m: number("height")!,
			},
			mapPolygon(draft.vertices),
		);
	if (shape.type !== "group") throw new Error("map_drawing_command_invalid");
	const command: GeometryCommand = {
		type: "group",
		before: draft.before,
		edits: [
			{ type: "put_source", before: null, value: source },
			...shape.edits,
		],
	};
	applyGeometryCommand(draft.before, command);
	return command;
}
