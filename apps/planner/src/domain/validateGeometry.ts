import Ajv from "ajv/dist/2020.js";
import { add, cross, dot, pointOnRoof, scale } from "./coordinates.ts";
import { inspectJson } from "../data/inspectJson.ts";
import type { GeometryDocument, Vec3 } from "./geometry.ts";
import { geometrySchema } from "./geometrySchema.ts";
import { panelCorners, panelPoses } from "./panelPoses.ts";

// Strict number checking rejects parsed 1e400/Infinity; defaults/coercion/removal
// are disabled so source values cannot silently turn into usable inputs.
const check = new Ajv({
	strict: true,
	strictNumbers: true,
	allErrors: false,
}).compile<GeometryDocument>(geometrySchema);

export interface GeometryLimits {
	max_panels: number;
	max_vertices: number;
	max_objects: number;
}

export class GeometryInputError extends Error {
	readonly code: string;
	readonly path: string;
	constructor(code: string, path = "") {
		super(code);
		this.name = "GeometryInputError";
		this.code = code;
		this.path = path;
	}
}

/** Wire/coordinate/resource validation, not polygon fit or engineering release. */
export function readGeometry(
	value: unknown,
	limits: GeometryLimits,
): GeometryDocument {
	inspectJson(value, 16);
	for (const limit of Object.values(limits)) {
		if (!Number.isSafeInteger(limit) || limit <= 0)
			throw new Error("invalid_geometry_resource_policy");
	}
	if (!check(value)) {
		throw new GeometryInputError(
			"invalid_geometry_document",
			check.errors?.[0]?.instancePath ?? "",
		);
	}
	const objects = [
		...value.roofs,
		...value.module_specs,
		...value.arrays,
		...value.obstacles,
		...value.keepouts,
		...value.sources,
	];
	if (objects.length + value.layout_rules.length > limits.max_objects)
		throw new GeometryInputError("geometry_object_limit");
	if (new Set(objects.map((item) => item.id)).size !== objects.length)
		throw new GeometryInputError("duplicate_geometry_id");
	const roofs = new Set(value.roofs.map((roof) => roof.id));
	const specs = new Set(value.module_specs.map((spec) => spec.id));
	const sources = new Set(value.sources.map((source) => source.id));
	for (const item of [
		...value.roofs,
		...value.arrays,
		...value.obstacles,
		...value.keepouts,
		...value.layout_rules,
	]) {
		if (!sources.has(item.source_id))
			throw new GeometryInputError("geometry_source_missing", item.source_id);
	}
	const coordinates = value.coordinate_system;
	if (coordinates.anchor && !sources.has(coordinates.anchor.source_id))
		throw new GeometryInputError("geometry_source_missing");
	if (
		(coordinates.north_reference === "unreferenced") !==
			(coordinates.north_source_id === null) ||
		(coordinates.north_source_id !== null &&
			!sources.has(coordinates.north_source_id))
	)
		throw new GeometryInputError("geometry_north_source_missing");
	if (
		new Set(value.layout_rules.map((rule) => rule.roof_id)).size !==
		value.layout_rules.length
	)
		throw new GeometryInputError("duplicate_layout_rules");
	for (const source of value.sources) {
		checkUrl(source.reference_url, source.id);
		if (source.acquired_at_utc !== null) {
			const stamp = source.acquired_at_utc;
			const date = new Date(stamp);
			if (
				Number(stamp.slice(0, 4)) < 1 ||
				!Number.isFinite(date.getTime()) ||
				date.toISOString().slice(0, 19) !== stamp.slice(0, 19)
			)
				throw new GeometryInputError("invalid_acquisition_time", source.id);
		}
		if (
			source.permissions.retain !== "permitted" ||
			source.permissions.derive !== "permitted"
		)
			throw new GeometryInputError("geometry_rights_unspecified", source.id);
		if (
			source.kind === "licensed_dataset" &&
			(source.rights_basis !== "referenced_licence" ||
				!source.reference_url ||
				!source.reference_sha256)
		)
			throw new GeometryInputError("geometry_licence_missing", source.id);
		if (
			(source.kind === "synthetic_fixture") !==
			(source.rights_basis === "synthetic")
		)
			throw new GeometryInputError("geometry_source_basis", source.id);
	}
	for (const spec of value.module_specs) {
		const source = spec.source;
		if (source.woo && source.kind !== "datasheet")
			throw new GeometryInputError("incomplete_module_reference", spec.id);
		if (
			source.kind === "datasheet" &&
			(source.document_sha256 === null ||
				source.url === null ||
				source.page === null)
		) {
			throw new GeometryInputError("incomplete_module_reference", spec.id);
		}
		if (source.url !== null) {
			checkUrl(source.url, spec.id);
		}
	}
	const vertexCount =
		value.roofs.reduce(
			(n, face) =>
				n +
				face.boundary_uv.length +
				face.holes_uv.reduce((m, hole) => m + hole.length, 0),
			0,
		) +
		[...value.obstacles, ...value.keepouts].reduce(
			(n, obstacle) => n + obstacle.footprint_uv.length,
			0,
		);
	if (vertexCount > limits.max_vertices)
		throw new GeometryInputError("geometry_vertex_limit");
	for (const roof of value.roofs) {
		unit(roof.u_axis_enu);
		unit(roof.v_axis_enu);
		// Numerical orthonormal-basis tolerance, not measurement precision or a
		// roof pitch, fire, structure or installation acceptance threshold.
		if (
			Math.abs(dot(roof.u_axis_enu, roof.v_axis_enu)) > 1e-9 ||
			cross(roof.u_axis_enu, roof.v_axis_enu)[2] <= 0
		) {
			throw new GeometryInputError("invalid_roof_basis", roof.id);
		}
		for (const ring of [roof.boundary_uv, ...roof.holes_uv]) {
			for (const uv of ring) representable(pointOnRoof(roof, uv));
		}
	}
	let total = 0;
	for (const array of value.arrays) {
		if (!roofs.has(array.roof_id) || !specs.has(array.module_spec_id))
			throw new GeometryInputError("geometry_reference_missing", array.id);
		const count = array.rows * array.columns;
		total += count;
		if (!Number.isSafeInteger(total) || total > limits.max_panels)
			throw new GeometryInputError("geometry_panel_limit");
		if (new Set(array.excluded_slots).size !== array.excluded_slots.length)
			throw new GeometryInputError("duplicate_excluded_slot", array.id);
		for (const slot of array.excluded_slots) {
			const [row, column] = slot.split(":").map(Number);
			if (
				row === undefined ||
				column === undefined ||
				row >= array.rows ||
				column >= array.columns ||
				slot !== `${row}:${column}`
			) {
				throw new GeometryInputError("invalid_excluded_slot", array.id);
			}
		}
	}
	for (const obstacle of value.obstacles) {
		if (!roofs.has(obstacle.roof_id))
			throw new GeometryInputError("geometry_reference_missing", obstacle.id);
		unit(obstacle.extrusion_axis_enu);
		const roof = value.roofs.find((r) => r.id === obstacle.roof_id)!;
		for (const uv of obstacle.footprint_uv)
			representable(
				add(
					pointOnRoof(roof, uv),
					scale(obstacle.extrusion_axis_enu, obstacle.height_m),
				),
			);
	}
	for (const item of [...value.keepouts, ...value.layout_rules]) {
		if (!roofs.has(item.roof_id))
			throw new GeometryInputError("geometry_reference_missing", item.roof_id);
	}
	const poses = panelPoses(value);
	if (
		poses
			.filter((pose) => pose.included)
			.reduce((sum, pose) => sum + pose.stc_power_w / 1000, 0) >
		Number.MAX_SAFE_INTEGER
	)
		throw new GeometryInputError("unrepresentable_module_rating");
	for (const pose of poses) {
		representable(pose.centre_enu);
		panelCorners(pose).forEach(representable);
	}
	return value;
}

function representable(point: Vec3): void {
	if (
		!point.every(
			(value) =>
				Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER,
		)
	)
		throw new GeometryInputError("unrepresentable_geometry");
}

function checkUrl(value: string | null, id: string): void {
	if (value === null) return;
	let url: URL;
	try {
		url = new URL(value);
	} catch {
		throw new GeometryInputError("invalid_source_url", id);
	}
	if (
		/[\u0000-\u001f]/.test(value) ||
		value !== value.trim() ||
		!["https:", "http:"].includes(url.protocol) ||
		url.username ||
		url.password
	)
		throw new GeometryInputError("invalid_source_url", id);
}

function unit(axis: Vec3): void {
	if (Math.abs(dot(axis, axis) - 1) > 1e-9)
		throw new GeometryInputError("invalid_unit_axis");
}
