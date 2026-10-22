import Ajv from "ajv";
import { cross, dot } from "./coordinates.ts";
import type { GeometryDocument, Vec3 } from "./geometry.ts";
import { geometrySchema } from "./geometrySchema.ts";
import { panelPoses } from "./panelPoses.ts";

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
	];
	if (objects.length > limits.max_objects)
		throw new GeometryInputError("geometry_object_limit");
	if (new Set(objects.map((item) => item.id)).size !== objects.length)
		throw new GeometryInputError("duplicate_geometry_id");
	const roofs = new Set(value.roofs.map((roof) => roof.id));
	const specs = new Set(value.module_specs.map((spec) => spec.id));
	for (const spec of value.module_specs) {
		const source = spec.source;
		if (
			source.kind === "datasheet" &&
			(source.document_sha256 === null ||
				source.url === null ||
				source.page === null)
		) {
			throw new GeometryInputError("incomplete_module_reference", spec.id);
		}
		if (source.url !== null) {
			let url: URL;
			try {
				url = new URL(source.url);
			} catch {
				throw new GeometryInputError("invalid_source_url", spec.id);
			}
			if (
				!["https:", "http:"].includes(url.protocol) ||
				url.username ||
				url.password
			) {
				throw new GeometryInputError("invalid_source_url", spec.id);
			}
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
		value.obstacles.reduce(
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
	}
	let total = 0;
	for (const array of value.arrays) {
		if (!roofs.has(array.roof_id) || !specs.has(array.module_spec_id))
			throw new GeometryInputError("geometry_reference_missing", array.id);
		const count = array.rows * array.columns;
		total += count;
		if (!Number.isSafeInteger(total) || total > limits.max_panels)
			throw new GeometryInputError("geometry_panel_limit");
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
	}
	for (const pose of panelPoses(value)) {
		if (!pose.centre_enu.every(Number.isFinite))
			throw new GeometryInputError("unrepresentable_geometry", pose.id);
	}
	return value;
}

function unit(axis: Vec3): void {
	if (Math.abs(dot(axis, axis) - 1) > 1e-9)
		throw new GeometryInputError("invalid_unit_axis");
}
