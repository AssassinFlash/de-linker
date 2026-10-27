import assert from "node:assert/strict";
import { test } from "node:test";
import fixtureJson from "../../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import {
	applyGeometryCommand,
	emptyGeometry,
	roofDependents,
} from "./geometryCommands.ts";
import { manualSource, rectangularRoof, parseRing } from "./geometryEditing.ts";
import { cross, dot } from "./coordinates.ts";
import { newHistory, change, undo, redo } from "./history.ts";
import { moduleSummary } from "./panelPoses.ts";

test("grouped roof/source creation is atomic and has one undo boundary", () => {
	const doc = emptyGeometry();
	const source = manualSource(
		"measurement",
		"Synthetic test",
		"Synthetic permission",
	);
	const roof = rectangularRoof(
		{ id: "roof", name: "Synthetic roof", source_id: source.id },
		{ width: 10, slopeLength: 8, pitch: 30, bearing: 180, origin: [0, 0, 0] },
	);
	const next = applyGeometryCommand(doc, {
		type: "group",
		edits: [
			{ type: "put_source", before: null, value: source },
			{ type: "put_roof", before: null, value: roof },
		],
	});
	const history = change(newHistory(doc), next, 100);
	assert.deepEqual(undo(history).current, doc);
	assert.deepEqual(redo(undo(history)).current, next);
	assert.equal(doc.roofs.length, 0);
	assert.throws(() =>
		applyGeometryCommand(doc, { type: "put_roof", before: null, value: roof }),
	);
	assert.equal(doc.sources.length, 0);
});

test("stale properties and changed roof dependents cannot overwrite current work", () => {
	const doc = readGeometry(fixtureJson, policy),
		array = doc.arrays[0]!;
	const moved = applyGeometryCommand(doc, {
		type: "move_arrays",
		ids: [array.id],
		delta_uv: [1, 2],
	});
	assert.throws(() =>
		applyGeometryCommand(moved, {
			type: "put_array",
			before: array,
			value: { ...array, name: "Stale edit" },
		}),
	);
	assert.throws(() =>
		applyGeometryCommand(doc, {
			type: "delete_roof",
			id: array.roof_id,
			expected_dependents: [],
		}),
	);
	const removed = applyGeometryCommand(doc, {
		type: "delete_roof",
		id: array.roof_id,
		expected_dependents: roofDependents(doc, array.roof_id),
	});
	assert.equal(removed.arrays.length, 0);
	assert.equal(removed.layout_rules.length, 0);
	assert.throws(() =>
		applyGeometryCommand(doc, {
			type: "delete_object",
			id: array.module_spec_id,
		}),
	);
	assert.deepEqual(doc, fixtureJson);
});

test("excluded slots keep their identities and quantities derive from included poses", () => {
	const doc = readGeometry(fixtureJson, policy),
		array = doc.arrays[0]!;
	const next = applyGeometryCommand(doc, {
		type: "toggle_panel",
		array_id: array.id,
		row: 0,
		column: 0,
	});
	assert.equal(moduleSummary(next).count, 4);
	assert.deepEqual(
		applyGeometryCommand(next, {
			type: "toggle_panel",
			array_id: array.id,
			row: 0,
			column: 0,
		}),
		doc,
	);
	assert.throws(() =>
		applyGeometryCommand(doc, {
			type: "toggle_panel",
			array_id: array.id,
			row: array.rows,
			column: 0,
		}),
	);
	assert.throws(() =>
		applyGeometryCommand(doc, {
			type: "move_arrays",
			ids: [array.id, array.id],
			delta_uv: [0, 1],
		}),
	);
});

test("a completed gesture rejects any changed coordinate or geometry frame atomically", () => {
	const before = readGeometry(fixtureJson, policy),
		array = before.arrays[0]!;
	const command = {
		type: "group" as const,
		before,
		edits: [
			{
				type: "put_array" as const,
				before: array,
				value: { ...array, origin_uv: [4, 5] as const },
			},
		],
	};
	assert.deepEqual(
		applyGeometryCommand(before, command).arrays[0]!.origin_uv,
		[4, 5],
	);
	for (const changed of [
		{
			...before,
			roofs: before.roofs.map((roof) => ({ ...roof, origin_enu: [10, 0, 0] })),
		},
		{
			...before,
			module_specs: before.module_specs.map((module) => ({
				...module,
				length_m: 3,
			})),
		},
		{
			...before,
			coordinate_system: {
				...before.coordinate_system,
				north_reference: "user_declared",
				north_source_id: before.sources[0]!.id,
			},
		},
	]) {
		const current = readGeometry(changed, policy);
		assert.throws(
			() => applyGeometryCommand(current, command),
			/geometry_frame_changed/,
		);
		assert.deepEqual(current.arrays[0], array);
	}
});

test("manual roof frame has upward normal, declared pitch and clockwise bearing", () => {
	for (const pitch of [0, 30, 90])
		for (const bearing of [0, 90, 180, 270]) {
			const roof = rectangularRoof(
				{ id: "r", name: "r", source_id: "s" },
				{ width: 10, slopeLength: 8, pitch, bearing, origin: [0, 0, 0] },
			);
			const normal = cross(roof.u_axis_enu, roof.v_axis_enu);
			assert.ok(Math.abs(dot(roof.u_axis_enu, roof.v_axis_enu)) < 1e-12);
			assert.ok(
				Math.abs(normal[2] - Math.cos((pitch * Math.PI) / 180)) < 1e-12,
			);
			if (pitch > 0) {
				assert.ok(
					Math.abs(
						normal[0] -
							Math.sin((bearing * Math.PI) / 180) *
								Math.sin((pitch * Math.PI) / 180),
					) < 1e-12,
				);
				assert.ok(
					Math.abs(
						normal[1] -
							Math.cos((bearing * Math.PI) / 180) *
								Math.sin((pitch * Math.PI) / 180),
					) < 1e-12,
				);
			}
		}
	assert.deepEqual(parseRing("0 ; 0\n1,5 ; 0\n0 ; 2,5", "de-DE"), [
		[0, 0],
		[1.5, 0],
		[0, 2.5],
	]);
	assert.throws(() => parseRing("1,5,0\n0,1\n0,0", "de-DE"));
});
