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
	readMapPolygon,
} from "./mapDrawingGeometry.ts";
import { readGeometry } from "./validateGeometry.ts";
import { readObject } from "../data/readProtocol.ts";
import { parseDecimal } from "./decimal.ts";
import { sameJson } from "./draft.ts";
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
export interface MapRoofDraft {
	readonly schema_version: 1;
	readonly key: string;
	readonly project_id: string;
	readonly locale: string;
	readonly before: GeometryDocument;
	readonly phase: "collecting" | "staged";
	readonly vertices: readonly Vec2[];
	readonly height_reference_position: Vec2 | null;
	readonly fields: MapRoofFields;
	/** A prepared result protects the raw data across a crash between local
	 * application and persistence. It is not proof the project was saved. */
	readonly prepared_geometry: GeometryDocument | null;
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

const uuid =
	/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;

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
		row.schema_version !== 1 ||
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
	// Parsing retains the drawing's number convention across language changes.
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
	const reference =
		row.height_reference_position === null
			? null
			: quantizeMapPosition(row.height_reference_position);
	if (
		(vertices.length > 0 && reference === null) ||
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
				(fields[name] as string).length > 4096,
		) ||
		typeof fields.permission !== "boolean" ||
		!["unknown", "permitted", "prohibited"].includes(fields.export as string)
	)
		throw new Error("map_drawing_recovery_invalid");
	const before = readGeometry(row.before, policy);
	drawingBridge(before);
	const draft: MapRoofDraft = {
		schema_version: 1,
		key: row.key,
		project_id: row.project_id,
		locale: row.locale,
		before,
		phase: row.phase,
		vertices,
		height_reference_position: reference,
		fields: fields as unknown as MapRoofFields,
		prepared_geometry:
			row.prepared_geometry === null
				? null
				: readGeometry(row.prepared_geometry, policy),
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
	if (
		draft.phase !== "collecting" ||
		draft.vertices.length >= policy.max_vertices
	)
		throw new Error("map_drawing_vertex_limit");
	const point = quantizeMapPosition(value);
	if (
		draft.vertices.some(
			(existing) => existing[0] === point[0] && existing[1] === point[1],
		)
	)
		throw new Error("map_drawing_duplicate_vertex");
	return {
		...draft,
		vertices: [...draft.vertices, point],
		height_reference_position: draft.height_reference_position ?? point,
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
