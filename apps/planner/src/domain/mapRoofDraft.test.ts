import assert from "node:assert/strict";
import test from "node:test";
import imported from "../../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import {
	appendMapRoofVertex,
	mapRoofDraftCommand,
	readMapRoofDraft,
	startMapRoofDraft,
} from "./mapRoofDraft.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { beginDraft, editDraft, redoDraft, undoDraft } from "./draft.ts";
import { readObject } from "../data/readProtocol.ts";
import { readGeometry } from "./validateGeometry.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };

const geometry = readGeometry(
	imported.metadata.geometry_import.geometry,
	policy,
);
const points = [
	[6.96, 50.94],
	[6.9601, 50.94],
	[6.9601, 50.9401],
	[6.96, 50.9401],
] as const;
function staged() {
	let draft = startMapRoofDraft(imported.project_id, geometry, "de-DE");
	for (const point of points) draft = appendMapRoofVertex(draft, point);
	return {
		...draft,
		phase: "staged" as const,
		fields: {
			...draft.fields,
			name: "Synthetic new roof",
			pitch: "36,86989764584402",
			bearing: "123",
			height: "8,125",
			source: "Synthetic supplied drawing and slope/height values",
			rights: "Synthetic fixture, test use permitted",
			calibration: "Synthetic coordinates; not a survey",
			precision: "",
			permission: true,
		},
	};
}
test("one/two/three-point recovery continues the exact prefix and retains invalid property text", () => {
	let draft = startMapRoofDraft(imported.project_id, geometry, "de-DE");
	for (const point of points) {
		const previous = draft.vertices;
		draft = readMapRoofDraft(
			JSON.parse(JSON.stringify(appendMapRoofVertex(draft, point))),
		);
		assert.deepEqual(draft.vertices.slice(0, -1), previous);
	}
	const raw = { ...draft, fields: { ...draft.fields, pitch: "7,5,broken" } };
	assert.equal(
		readMapRoofDraft(JSON.parse(JSON.stringify(raw))).fields.pitch,
		"7,5,broken",
	);
	assert.equal(draft.phase, "collecting");
	assert.deepEqual(draft.before, geometry);
});
test("a frozen height reference survives reversed or deleted first vertices", () => {
	const draft = staged();
	const roof = applyGeometryCommand(
		geometry,
		mapRoofDraftCommand(draft),
	).roofs.at(-1)!;
	for (const vertices of [
		[...draft.vertices].reverse(),
		draft.vertices.slice(1),
	]) {
		const next = applyGeometryCommand(
			geometry,
			mapRoofDraftCommand({ ...draft, vertices }),
		).roofs.at(-1)!;
		assert.deepEqual(next.origin_enu, roof.origin_enu);
		assert.deepEqual(next.u_axis_enu, roof.u_axis_enu);
		assert.deepEqual(next.v_axis_enu, roof.v_axis_enu);
	}
	assert.equal(roof.origin_enu[2], 8.125);
});
test("explicit source/plane confirmation creates one whole-frame command and common undo/redo", () => {
	const draft = staged(),
		command = mapRoofDraftCommand(draft),
		result = applyGeometryCommand(geometry, command);
	assert.equal(command.type, "group");
	assert.deepEqual(command.before, geometry);
	assert.equal(command.edits.length, 2);
	assert.deepEqual(result.roofs.slice(0, -1), geometry.roofs);
	assert.deepEqual(result.sources.slice(0, -1), geometry.sources);
	assert.equal(result.sources.at(-1)!.kind, "user_drawing");
	assert.equal(result.sources.at(-1)!.spatial_precision_m, null);
	assert.equal(result.sources.at(-1)!.permissions.export, "unknown");
	const inputs = {
			geometry: readObject(geometry),
			note: "other workspace value",
		},
		baseline = {
			id: imported.project_id,
			title: "Synthetic map draft",
			revision: 1,
			input_sha256: "a".repeat(64),
			inputs,
		};
	const next = editDraft(beginDraft(baseline), {
		...inputs,
		geometry: readObject(result),
	});
	assert.equal(next.history.past.length, 1);
	assert.deepEqual(undoDraft(next).history.current, inputs);
	assert.deepEqual(redoDraft(undoDraft(next)).history.current.geometry, result);
	assert.throws(
		() => applyGeometryCommand({ ...geometry, roofs: [] }, command),
		/frame_changed/,
	);
});
test("raw recovery rejects corrupt versions, duplicate or nonquantized points and forged prepared results", () => {
	const draft = staged();
	for (const bad of [
		{ ...draft, schema_version: 2 },
		{ ...draft, private_sdk: {} },
		{ ...draft, vertices: [...draft.vertices, draft.vertices[0]] },
		{
			...draft,
			vertices: [[6.96000000001, 50.94], ...draft.vertices.slice(1)],
		},
		{ ...draft, prepared_geometry: geometry },
	])
		assert.throws(() => readMapRoofDraft(bad));
	const result = applyGeometryCommand(geometry, mapRoofDraftCommand(draft));
	assert.deepEqual(
		readMapRoofDraft({ ...draft, prepared_geometry: result }).prepared_geometry,
		result,
	);
});
test("required physical values have no flat/zero fallback and field-specific errors retain the buffer", () => {
	const draft = staged();
	for (const [name, value] of [
		["pitch", ""],
		["pitch", "90"],
		["bearing", "360"],
		["height", "bad"],
		["precision", "-1"],
		["source", " "],
	] as const) {
		const bad = { ...draft, fields: { ...draft.fields, [name]: value } };
		assert.throws(
			() => mapRoofDraftCommand(bad),
			(cause: unknown) =>
				cause instanceof Error &&
				(cause as Error & { field: string }).field === name,
		);
		assert.equal(
			readMapRoofDraft(bad).fields[name as keyof typeof bad.fields],
			value,
		);
	}
	assert.throws(
		() =>
			mapRoofDraftCommand({
				...draft,
				fields: { ...draft.fields, permission: false },
			}),
		/confirmation_required/,
	);
	assert.throws(
		() =>
			appendMapRoofVertex({ ...draft, phase: "collecting" }, draft.vertices[0]),
		/duplicate_vertex/,
	);
});
