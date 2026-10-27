/** A prepared import joins the same document/history; it never owns another scene. */
import Ajv2020 from "ajv/dist/2020.js";
import commandSchema from "../contracts/geometry-import-command.schema.json" with { type: "json" };
import optionsSchema from "../contracts/geometry-import-options.schema.json" with { type: "json" };
import selectionsSchema from "../contracts/geometry-import-selections.schema.json" with { type: "json" };
import policy from "../contracts/geometry-import-policy.json" with { type: "json" };
import geometryPolicy from "../contracts/geometry-policy.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { inspectJson } from "../data/inspectJson.ts";
import type { GeometryDocument, PlaneFrame } from "./geometry.ts";
import type { GeographicReference } from "./geographic.ts";
import { applyGeometryCommand, emptyGeometry } from "./geometryCommands.ts";
import type { GeometryEdit } from "./geometryCommands.ts";
import { sameJson } from "./draft.ts";
import { readGeometry } from "./validateGeometry.ts";

export interface GeometryImportOptions {
	schema_version: 1;
	format: "geojson_wgs84_horizontal_v1";
	plane_intersection_method?: "geodetic_vertical_line_v1" | null;
	feature_index: number;
	polygon_index: number;
	roof_name: string;
	reference: GeographicReference;
	plane: PlaneFrame & { basis_note: string };
	source: {
		label: string;
		rights_note: string;
		spatial_precision_m: number | null;
		export_permission: "permitted" | "unknown" | "prohibited";
	};
}
export interface GeometryImportCommand {
	schema_version: 1;
	project_id: string;
	content_base64: string;
	options: GeometryImportOptions;
	key: string;
}
export interface GeometryImportSelections {
	schema_version: 1;
	selected: Readonly<Record<string, string>>;
}
export interface PreparedGeometryImport {
	id: string;
	projectId: string;
	contentHash: string;
	metadataHash: string;
	geometryHash: string;
	geometry: GeometryDocument;
	options: GeometryImportOptions;
	areaM2: number;
	projection: JsonObject;
}
const ajv = new Ajv2020({ strict: true, strictNumbers: true }),
	checkCommand = ajv.compile<GeometryImportCommand>(commandSchema),
	checkOptions = ajv.compile<GeometryImportOptions>(optionsSchema),
	checkSelections = ajv.compile<GeometryImportSelections>(selectionsSchema),
	hash = (value: unknown): value is string =>
		typeof value === "string" && /^[a-f0-9]{64}$/.test(value),
	id = (value: unknown): value is string =>
		typeof value === "string" && /^[a-f0-9]{32}$/.test(value);

export function readGeometryImportCommand(
	value: unknown,
): GeometryImportCommand {
	inspectJson(value, 20);
	if (!checkCommand(value)) throw new Error("invalid_geometry_import_command");
	readGeometryImportOptions(value.options);
	const content = value.content_base64;
	if (
		!content ||
		content.length > 4 * Math.ceil(policy.max_file_bytes / 3) ||
		content.length % 4 !== 0 ||
		/[^A-Za-z0-9+/=]/.test(content)
	)
		throw new Error("invalid_geometry_import_file");
	try {
		if (atob(content).length > policy.max_file_bytes) throw new Error("size");
	} catch {
		throw new Error("invalid_geometry_import_file");
	}
	return value;
}

export function readGeometryImportOptions(
	value: unknown,
): GeometryImportOptions {
	inspectJson(value, 16);
	if (
		!checkOptions(value) ||
		value.reference.height_basis !== "zero_height_horizontal_convention" ||
		value.reference.ellipsoid_height_m !== 0 ||
		![
			value.roof_name,
			value.plane.basis_note,
			value.source.label,
			value.source.rights_note,
		].every((note) => note.trim())
	)
		throw new Error("invalid_geometry_import_options");
	return value;
}
export function readGeometryImports(value: unknown): GeometryImportSelections {
	if (value === undefined) return { schema_version: 1, selected: {} };
	inspectJson(value, 8);
	if (!checkSelections(value))
		throw new Error("invalid_geometry_import_selections");
	return value;
}

export function readPreparedGeometryImport(
	value: unknown,
	projectId: string,
): PreparedGeometryImport {
	const asset = readObject(value),
		metadata = readObject(asset.metadata),
		prepared = readObject(metadata.geometry_import),
		geometry = readGeometry(prepared.geometry, geometryPolicy),
		options = metadata.geometry_import_options;
	const checked = readGeometryImportOptions(options);
	const projection = readObject(prepared.projection),
		source = geometry.sources[0],
		roof = geometry.roofs[0];
	if (
		!id(asset.id) ||
		asset.project_id !== projectId ||
		asset.purpose !== "geometry_import_v1" ||
		asset.media_type !== "application/geo+json" ||
		!hash(asset.content_sha256) ||
		!hash(asset.metadata_sha256) ||
		!hash(prepared.geometry_sha256) ||
		prepared.original_content_sha256 !== asset.content_sha256 ||
		prepared.engineering_status !== "not_evaluated" ||
		prepared.elevation_basis !==
			"user_declared_plane_relative_to_project_origin" ||
		prepared.schema_version !== 1 ||
		checked.plane_intersection_method !== "geodetic_vertical_line_v1" ||
		prepared.plane_intersection_method !== checked.plane_intersection_method ||
		!source ||
		!roof ||
		geometry.sources.length !== 1 ||
		geometry.roofs.length !== 1 ||
		geometry.arrays.length ||
		geometry.module_specs.length ||
		geometry.obstacles.length ||
		geometry.keepouts.length ||
		geometry.layout_rules.length ||
		metadata.retention !== "permanent" ||
		geometry.coordinate_system.north_reference !== "true_north" ||
		geometry.coordinate_system.north_source_id !== source.id ||
		geometry.coordinate_system.anchor?.source_id !== source.id ||
		geometry.coordinate_system.anchor?.latitude_deg !==
			checked.reference.latitude_deg ||
		geometry.coordinate_system.anchor?.longitude_deg !==
			checked.reference.longitude_deg ||
		source.kind !== "user_drawing" ||
		source.rights_basis !== "user_attestation" ||
		source.note !== checked.source.label ||
		source.rights_note !== checked.source.rights_note ||
		source.spatial_precision_m !== checked.source.spatial_precision_m ||
		source.permissions.export !== checked.source.export_permission ||
		source.calibration_note !== checked.plane.basis_note ||
		source.reference_sha256 !== asset.content_sha256 ||
		roof.name !== checked.roof_name ||
		roof.source_id !== source.id ||
		!sameJson(projection.reference, checked.reference) ||
		!sameJson(roof.origin_enu, checked.plane.origin_enu) ||
		!sameJson(roof.u_axis_enu, checked.plane.u_axis_enu) ||
		!sameJson(roof.v_axis_enu, checked.plane.v_axis_enu) ||
		typeof prepared.area_roof_plane_m2 !== "number" ||
		!Number.isFinite(prepared.area_roof_plane_m2) ||
		prepared.area_roof_plane_m2 <= 0
	)
		throw new Error("invalid_geometry_import_reply");
	return {
		id: asset.id,
		projectId,
		contentHash: asset.content_sha256,
		metadataHash: asset.metadata_sha256,
		geometryHash: prepared.geometry_sha256,
		geometry,
		options: checked,
		areaM2: prepared.area_roof_plane_m2,
		projection,
	};
}

export function attachGeometryImport(
	inputs: JsonObject,
	before: GeometryDocument,
	asset: PreparedGeometryImport,
): JsonObject {
	const current =
			inputs.geometry === undefined
				? emptyGeometry()
				: readGeometry(inputs.geometry, geometryPolicy),
		source = asset.geometry.sources[0]!,
		roof = asset.geometry.roofs[0]!,
		coordinate = current.coordinate_system,
		anchor = asset.geometry.coordinate_system.anchor!;
	if (
		current.sources.some((value) => value.id === source.id) ||
		current.roofs.some((value) => value.id === roof.id)
	)
		throw new Error("geometry_import_already_attached");
	const emptyFrame =
		!current.roofs.length &&
		!current.arrays.length &&
		!current.obstacles.length &&
		!current.keepouts.length &&
		coordinate.anchor === null &&
		coordinate.north_reference === "unreferenced";
	if (
		!emptyFrame &&
		(coordinate.north_reference !== "true_north" ||
			coordinate.anchor?.latitude_deg !== anchor.latitude_deg ||
			coordinate.anchor?.longitude_deg !== anchor.longitude_deg)
	)
		throw new Error("geometry_import_frame_alignment_required");
	const edits: GeometryEdit[] = [
		{ type: "put_source", before: null, value: source },
		{ type: "put_roof", before: null, value: roof },
	];
	if (emptyFrame)
		edits.push({
			type: "set_coordinate_system",
			before: coordinate,
			value: asset.geometry.coordinate_system,
		});
	const geometry = applyGeometryCommand(current, {
			type: "group",
			before,
			edits,
		}),
		imports = readGeometryImports(inputs.geometry_imports);
	return {
		...inputs,
		geometry: readObject(geometry),
		geometry_imports: {
			schema_version: 1,
			selected: { ...imports.selected, [source.id]: asset.id },
		},
	};
}
