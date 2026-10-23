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
import flatFixture from "../../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import poseReference from "../../../../fixtures/planning/geometry-pose-reference.json" with { type: "json" };
import geometryPolicy from "../contracts/geometry-policy.json" with { type: "json" };
import {
	moduleSummary,
	panelPoses,
	panelPositionRelative,
} from "./panelPoses.ts";
import { readGeometry } from "./validateGeometry.ts";

// Analytic geometry fixtures, with deliberately synthetic module dimensions.
const fixture = (): GeometryDocument =>
	readGeometry(structuredClone(flatFixture), geometryPolicy);

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

test("browser poses match frozen server poses across slope, rotation and tilted mounts", () => {
	for (const reference of poseReference.cases) {
		const document = fixture();
		const value = {
			...document,
			roofs: [
				{
					...document.roofs[0]!,
					v_axis_enu: reference.roof_v_axis_enu as unknown as Vec3,
				},
			],
			arrays: [
				{
					...document.arrays[0]!,
					rotation_deg: reference.rotation_deg,
					mount_tilt_deg: reference.mount_tilt_deg,
				},
			],
		};
		const poses = panelPoses(readGeometry(value, geometryPolicy));
		assert.equal(poses.length, reference.poses.length, reference.name);
		for (const [index, pose] of poses.entries()) {
			const expected = reference.poses[index]!;
			assert.equal(pose.id, expected.id);
			assert.equal(pose.array_id, expected.array_id);
			assert.equal(pose.included, expected.included);
			for (const property of [
				"centre_enu",
				"u_axis_enu",
				"v_axis_enu",
				"normal_enu",
			] as const) {
				pose[property].forEach((value, axis) =>
					close(value, expected[property][axis]!),
				);
			}
		}
	}
});

test("periodic angles normalise before trig and large origins retain a rebased local pose", () => {
	for (const angle of [
		360, -360, 6898968225049280, 9007199254740991, -9007199254740991,
	]) {
		const document = fixture();
		const run = (rotation_deg: number) =>
			panelPoses({
				...document,
				arrays: [{ ...document.arrays[0]!, rotation_deg }],
			});
		assert.deepEqual(run(angle), run(angle % 360));
	}
	const document = fixture();
	const roof = { ...document.roofs[0]!, origin_enu: [1e15, 0, 4] as Vec3 };
	const pose = panelPoses({ ...document, roofs: [roof] })[0]!;
	assert.deepEqual(
		panelPositionRelative(pose, roof, roof.origin_enu),
		[1.5, 3, 0.12000000000000001],
	);
});

test("source UTC semantics and duplicate excluded slots agree with the server", () => {
	const document = fixture();
	for (const acquired_at_utc of [
		"yesterday",
		"2024-02-30T00:00:00Z",
		"2024-01-01T00:00:00+01:00",
		"0000-01-01T00:00:00Z",
	]) {
		assert.throws(() =>
			readGeometry(
				{
					...document,
					sources: [{ ...document.sources[0]!, acquired_at_utc }],
				},
				geometryPolicy,
			),
		);
	}
	const accepted = {
		...document,
		sources: [
			{
				...document.sources[0]!,
				acquired_at_utc: "2024-02-29T23:30:00.123456+00:00",
			},
		],
	};
	assert.equal(readGeometry(accepted, geometryPolicy), accepted);
	assert.throws(() =>
		readGeometry(
			{
				...document,
				arrays: [{ ...document.arrays[0]!, excluded_slots: ["0:0", "0:0"] }],
			},
			geometryPolicy,
		),
	);
});

test("large UV charts are preserved as inputs but the render helper explicitly refuses lost precision", () => {
	for (const [width_m, length_m] of [
		[0.01, 0.02],
		[1.134, 2.278],
	]) {
		const document = fixture();
		const value = {
			...document,
			arrays: [
				{
					...document.arrays[0]!,
					rows: 1,
					columns: 1,
					excluded_slots: [],
					origin_uv: [1e15 + 1, 1e15 + 2] as const,
				},
			],
			module_specs: [
				{
					...document.module_specs[0]!,
					width_m: width_m!,
					length_m: length_m!,
				},
			],
		};
		const parsed = readGeometry(value, geometryPolicy);
		const pose = panelPoses(parsed)[0]!;
		assert.throws(
			() => panelPositionRelative(pose, parsed.roofs[0]!, [1e15, 1e15, 0]),
			{ name: "GeometryPrecisionError" },
		);
		assert.equal(parsed, value);
	}
});
