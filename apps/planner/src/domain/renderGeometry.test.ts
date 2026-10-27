import assert from "node:assert/strict";
import { test } from "node:test";
import flat from "../../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import {
	centredRings,
	panelBatches,
	renderBoundsPoints,
	requireRenderCoordinates,
} from "./renderGeometry.ts";
import { panelPoses } from "./panelPoses.ts";

test("Float32 roof buffers retain centimetre openings inside large supported UV charts", () => {
	const uv = 1e6;
	const result = centredRings(
		[
			[uv, uv],
			[uv + 10, uv],
			[uv + 10, uv + 10],
			[uv, uv + 10],
		],
		[
			[
				[uv + 1, uv + 1],
				[uv + 1.01, uv + 1],
				[uv + 1.01, uv + 1.01],
				[uv + 1, uv + 1.01],
			],
		],
	);
	assert.equal(
		new Set(result.holes[0]!.map((point) => point.map(Math.fround).join(",")))
			.size,
		4,
	);
	assert.ok(
		Math.abs(result.holes[0]![1]![0] - result.holes[0]![0]![0] - 0.01) < 1e-9,
	);
	assert.throws(() => requireRenderCoordinates([1e6 + 0.01]));
});

test("scene framing includes all actual obstacle top vertices", () => {
	const doc = readGeometry(structuredClone(flat), policy);
	const roof = doc.roofs[0]!;
	const object = {
		id: "tall",
		name: "Synthetic tall obstacle",
		source_id: roof.source_id,
		roof_id: roof.id,
		footprint_uv: [
			[0, 0],
			[1, 0],
			[1, 1],
			[0, 1],
		] as const,
		height_m: 30,
		extrusion_axis_enu: [0, 0, 1] as const,
	};
	const points = renderBoundsPoints(
		{ ...doc, obstacles: [object] },
		panelPoses(doc),
		roof.origin_enu,
	);
	assert.equal(Math.max(...points.map((point) => point[1])), 30);
});

test("large arrays batch relative to local pivots without dropping stable IDs", () => {
	const doc = readGeometry(structuredClone(flat), policy);
	const array = {
		...doc.arrays[0]!,
		origin_uv: [1e6 + 0.01, 1e6 + 0.02] as const,
		rows: 1,
		columns: 5000,
		excluded_slots: [],
	};
	const poses = panelPoses({ ...doc, arrays: [array] });
	const batches = panelBatches(poses);
	assert.equal(batches.flatMap((batch) => batch.poses).length, 5000);
	assert.ok(batches.length > 1 && batches.length < 100);
	for (const batch of batches)
		for (const pose of batch.poses)
			assert.ok(
				pose.centre_uvn.every(
					(value, index) => Math.abs(value - batch.pivot[index]!) <= 64,
				),
			);
});
