/** Draft-07 wire shape; Ajv's default draft matches this instance. */
const text = { type: "string", minLength: 1, maxLength: 4096 };
const id = { type: "string", pattern: "^[A-Za-z][A-Za-z0-9_-]{0,63}$" };
const number = { type: "number" };
const nonnegative = { type: "number", minimum: 0 };
const positive = { type: "number", exclusiveMinimum: 0 };
const integer = {
	type: "integer",
	minimum: 1,
	maximum: Number.MAX_SAFE_INTEGER,
};
const nullable = (schema: object): object => ({
	anyOf: [schema, { type: "null" }],
});
const object = (properties: Record<string, object>): object => ({
	type: "object",
	properties,
	required: Object.keys(properties),
	additionalProperties: false,
});
const vector = (length: number): object => ({
	type: "array",
	items: Array.from({ length }, () => number),
	minItems: length,
	maxItems: length,
	additionalItems: false,
});
const ring = { type: "array", minItems: 3, items: vector(2) };
const list = (items: object): object => ({ type: "array", items });

export const geometrySchema = {
	$schema: "http://json-schema.org/draft-07/schema#",
	...object({
		schema_version: { type: "integer", const: 1 },
		coordinate_system: object({
			kind: { const: "local_enu" },
			unit: { const: "m" },
			height_reference: { const: "relative_to_project_origin" },
			north_reference: {
				enum: ["true_north", "user_declared", "unreferenced"],
			},
			anchor: nullable(
				object({
					latitude_deg: { type: "number", minimum: -90, maximum: 90 },
					longitude_deg: { type: "number", minimum: -180, maximum: 180 },
				}),
			),
		}),
		source: object({
			kind: {
				enum: ["user_measurement", "licensed_dataset", "synthetic_fixture"],
			},
			note: text,
			rights_note: text,
		}),
		roofs: list(
			object({
				id,
				name: text,
				origin_enu: vector(3),
				u_axis_enu: vector(3),
				v_axis_enu: vector(3),
				boundary_uv: ring,
				holes_uv: list(ring),
			}),
		),
		module_specs: list(
			object({
				id,
				model: text,
				width_m: positive,
				length_m: positive,
				thickness_m: positive,
				stc_power_w: positive,
				source: object({
					kind: { enum: ["datasheet", "user_declared"] },
					note: text,
					document_sha256: nullable({
						type: "string",
						pattern: "^[a-f0-9]{64}$",
					}),
					url: nullable(text),
					page: nullable(integer),
				}),
			}),
		),
		arrays: list(
			object({
				id,
				name: text,
				roof_id: id,
				module_spec_id: id,
				origin_uv: vector(2),
				rotation_deg: number,
				mount_tilt_deg: { type: "number", minimum: 0, maximum: 90 },
				lower_edge_clearance_m: nonnegative,
				rows: integer,
				columns: integer,
				column_gap_m: nonnegative,
				row_gap_m: nonnegative,
				excluded_slots: {
					type: "array",
					uniqueItems: true,
					items: { type: "string", pattern: "^\\d+:\\d+$" },
				},
				mounting_note: text,
			}),
		),
		obstacles: list(
			object({
				id,
				name: text,
				roof_id: id,
				footprint_uv: ring,
				extrusion_axis_enu: vector(3),
				height_m: positive,
			}),
		),
	}),
};
