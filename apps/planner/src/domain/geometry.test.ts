import assert from "node:assert/strict";
import { test } from "node:test";
import {
	cross,
	dot,
	fromRender,
	pointOnRoof,
	roofCoordinates,
	toRender,
} from "./coordinates.ts";
import type { GeometryDocument, Vec3 } from "./geometry.ts";
import { moduleSummary, panelPoses } from "./panelPoses.ts";
import { readGeometry } from "./validateGeometry.ts";

// Analytic geometry fixtures, with deliberately synthetic module dimensions.
const fixture = (): GeometryDocument => ({
	schema_version: 1,
	coordinate_system: {
		kind: "local_enu",
		unit: "m",
		height_reference: "relative_to_project_origin",
		north_reference: "unreferenced",
		anchor: null,
	},
	source: {
		kind: "synthetic_fixture",
		note: "Analytic test only",
		rights_note: "Owned fixture",
	},
	roofs: [
		{
			id: "roof",
			name: "Fixture roof",
			origin_enu: [10, -20, 4],
			u_axis_enu: [1, 0, 0],
			v_axis_enu: [0, 1, 0],
			boundary_uv: [
				[0, 0],
				[20, 0],
				[20, 20],
				[0, 20],
			],
			holes_uv: [],
		},
	],
	module_specs: [
		{
			id: "module",
			model: "Synthetic 1 × 2 m",
			width_m: 1,
			length_m: 2,
			thickness_m: 0.04,
			stc_power_w: 500,
			source: {
				kind: "user_declared",
				note: "Synthetic fixture",
				document_sha256: null,
				url: null,
				page: null,
			},
		},
	],
	arrays: [
		{
			id: "array",
			name: "Fixture array",
			roof_id: "roof",
			module_spec_id: "module",
			origin_uv: [1, 2],
			rotation_deg: 0,
			mount_tilt_deg: 0,
			lower_edge_clearance_m: 0.1,
			rows: 2,
			columns: 3,
			column_gap_m: 0.2,
			row_gap_m: 0.4,
			excluded_slots: ["1:2"],
			mounting_note: "Synthetic dimensions, not a mounting-system release",
		},
	],
	obstacles: [],
});

function close(actual: number, expected: number): void {
	// Floating point comparison policy for these metre-scale analytic fixtures.
	assert.ok(Math.abs(actual - expected) < 1e-12, `${actual} != ${expected}`);
}

test("ENU/render mapping preserves handedness, lengths and exact round trip", () => {
	const points: Vec3[] = [
		[0, 0, 0],
		[1, 2, 3],
		[-120.5, 500, -4],
	];
	for (const point of points) {
		assert.deepEqual(fromRender(toRender(point)), point);
		close(dot(toRender(point), toRender(point)), dot(point, point));
	}
	const actualNormal = cross(toRender([1, 0, 0]), toRender([0, 1, 0]));
	const expectedNormal = toRender([0, 0, 1]);
	actualNormal.forEach((value, index) => close(value, expectedNormal[index]!));
});

test("face coordinates use slope length, independent of horizontal projection", () => {
	const roof = fixture().roofs[0]!;
	const tilted = {
		...roof,
		v_axis_enu: [0, Math.cos(Math.PI / 6), 0.5] as Vec3,
	};
	const point = pointOnRoof(tilted, [2, 8]);
	close(point[2], 8);
	const back = roofCoordinates(tilted, point);
	close(back[0], 2);
	close(back[1], 8);
});

test("shared panel poses provide stable IDs, metres and the exact active quantity", () => {
	const document = fixture();
	const poses = panelPoses(document);
	assert.equal(poses.length, 6);
	assert.equal(poses[0]!.id, "array:0:0");
	close(poses[0]!.centre_enu[0], 11.5);
	close(poses[0]!.centre_enu[1], -17);
	close(poses[0]!.centre_enu[2], 4.12);
	assert.equal(poses[5]!.included, false);
	assert.deepEqual(moduleSummary(document), { count: 5, stc_kwp: 2.5 });
});

test("tilted rows reset lower-edge height instead of becoming one rising plane", () => {
	const document = fixture();
	const array = { ...document.arrays[0]!, mount_tilt_deg: 30 };
	const poses = panelPoses({ ...document, arrays: [array] });
	close(poses[0]!.centre_enu[2], poses[3]!.centre_enu[2]);
	close(
		poses[3]!.centre_enu[1] - poses[0]!.centre_enu[1],
		2 * Math.cos(Math.PI / 6) + 0.4,
	);
	close(dot(poses[0]!.u_axis_enu, poses[0]!.v_axis_enu), 0);
	close(dot(poses[0]!.normal_enu, poses[0]!.normal_enu), 1);
});

test("array rotation changes positions and orientation around the same roof anchor", () => {
	const document = fixture();
	const poses = panelPoses({
		...document,
		arrays: [{ ...document.arrays[0]!, rotation_deg: 90 }],
	});
	close(poses[0]!.centre_enu[0], 10);
	close(poses[0]!.centre_enu[1], -17.5);
	close(poses[0]!.u_axis_enu[1], 1);
	close(poses[0]!.v_axis_enu[0], -1);
});

test("wire geometry rejects coercion, missing references, invalid units and runaway allocations", () => {
	const document = fixture();
	const limits = { max_panels: 100, max_vertices: 1000, max_objects: 100 };
	assert.equal(readGeometry(document, limits), document);
	const cases: unknown[] = [
		{ ...document, schema_version: true },
		{ ...document, engineering_approved: true },
		{ ...document, arrays: [{ ...document.arrays[0]!, rows: "2" }] },
		{ ...document, arrays: [{ ...document.arrays[0]!, rows: 1e9 }] },
		{ ...document, arrays: [{ ...document.arrays[0]!, roof_id: "missing" }] },
		{
			...document,
			arrays: [{ ...document.arrays[0]!, excluded_slots: ["01:0"] }],
		},
		{ ...document, roofs: [{ ...document.roofs[0]!, u_axis_enu: [2, 0, 0] }] },
		{
			...document,
			roofs: [{ ...document.roofs[0]!, v_axis_enu: [0.6, 0.8, 0] }],
		},
		{
			...document,
			module_specs: [{ ...document.module_specs[0]!, width_m: 0 }],
		},
		{
			...document,
			module_specs: [{ ...document.module_specs[0]!, width_m: Infinity }],
		},
		{
			...document,
			module_specs: [{ ...document.module_specs[0]!, id: "roof" }],
		},
	];
	for (const value of cases) assert.throws(() => readGeometry(value, limits));
});

test("module-source claims need complete references and safe URL schemes", () => {
	const document = fixture();
	const limits = { max_panels: 100, max_vertices: 1000, max_objects: 100 };
	const spec = document.module_specs[0]!;
	for (const source of [
		{ ...spec.source, kind: "datasheet" },
		{ ...spec.source, url: "javascript:alert(1)" },
		{
			...spec.source,
			url: "https://credential:secret@example.com/private.pdf",
		},
	]) {
		assert.throws(() =>
			readGeometry(
				{ ...document, module_specs: [{ ...spec, source }] },
				limits,
			),
		);
	}
});
