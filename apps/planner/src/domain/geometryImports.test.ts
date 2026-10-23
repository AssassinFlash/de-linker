import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
	attachGeometryImport,
	readGeometryImportCommand,
	readGeometryImports,
	readPreparedGeometryImport,
} from "./geometryImports.ts";
import { emptyGeometry } from "./geometryCommands.ts";
import { beginDraft, editDraft, undoDraft, redoDraft } from "./draft.ts";
import { readObject } from "../data/readProtocol.ts";

const fixture = JSON.parse(
	readFileSync(
		new URL(
			"../../../../fixtures/planning/geometry-import-asset.json",
			import.meta.url,
		),
		"utf8",
	),
);

test("actual server import wire joins geometry/reference/source in one project history step", () => {
	const prepared = readPreparedGeometryImport(fixture, fixture.project_id),
		before = emptyGeometry(),
		inputs = attachGeometryImport(
			{ brief: { retained: true } },
			before,
			prepared,
		),
		geometry = readObject(inputs.geometry);
	assert.equal(prepared.geometry.roofs[0]!.holes_uv.length, 1);
	assert.deepEqual(
		geometry.coordinate_system,
		prepared.geometry.coordinate_system,
	);
	assert.deepEqual(inputs.brief, { retained: true });
	assert.equal(
		readGeometryImports(inputs.geometry_imports).selected[
			prepared.geometry.sources[0]!.id
		],
		prepared.id,
	);
	const project = {
			id: fixture.project_id,
			title: "Synthetic",
			revision: 1,
			input_sha256: "a".repeat(64),
			inputs: {},
		},
		initial = beginDraft(project),
		changed = editDraft(initial, inputs);
	assert.deepEqual(undoDraft(changed).history.current, {});
	assert.deepEqual(redoDraft(undoDraft(changed)).history.current, inputs);
});

test("a stale frame, unaligned existing roof and repeated attach are refused without mutation", () => {
	const prepared = readPreparedGeometryImport(fixture, fixture.project_id),
		before = emptyGeometry(),
		inputs = attachGeometryImport({}, before, prepared);
	assert.throws(() => attachGeometryImport(inputs, before, prepared));
	const existing = {
		...prepared.geometry,
		coordinate_system: {
			...prepared.geometry.coordinate_system,
			north_reference: "unreferenced" as const,
			north_source_id: null,
			anchor: null,
		},
		sources: prepared.geometry.sources.map((source) => ({
			...source,
			id: "existing_source",
		})),
		roofs: prepared.geometry.roofs.map((roof) => ({
			...roof,
			id: "existing_roof",
			source_id: "existing_source",
		})),
	};
	const snapshot = structuredClone(existing);
	assert.throws(
		() =>
			attachGeometryImport(
				{ geometry: readObject(existing) },
				existing,
				prepared,
			),
		/alignment_required/,
	);
	assert.deepEqual(existing, snapshot);
	const changed = {
		...before,
		sources: prepared.geometry.sources.map((source) => ({
			...source,
			id: "unrelated_source",
		})),
	};
	assert.throws(
		() =>
			attachGeometryImport({ geometry: readObject(changed) }, before, prepared),
		/geometry_frame_changed/,
	);
});

test("import wire rejects wrong owner/version/hash, permissive source claims and invalid base64", () => {
	assert.throws(() => readPreparedGeometryImport(fixture, "0".repeat(32)));
	const changed = structuredClone(fixture);
	changed.content_sha256 = "0".repeat(64);
	assert.throws(() => readPreparedGeometryImport(changed, fixture.project_id));
	const wrongFrame = structuredClone(fixture);
	wrongFrame.metadata.geometry_import.geometry.coordinate_system.anchor.longitude_deg += 1;
	assert.throws(() =>
		readPreparedGeometryImport(wrongFrame, fixture.project_id),
	);
	const command = {
		schema_version: 1,
		project_id: fixture.project_id,
		options: fixture.metadata.geometry_import_options,
		content_base64: "eA==",
		key: crypto.randomUUID(),
	};
	assert.equal(readGeometryImportCommand(command).key, command.key);
	for (const content_base64 of ["", "eA=", " eA==", "e===", "!==="])
		assert.throws(() =>
			readGeometryImportCommand({ ...command, content_base64 }),
		);
	assert.throws(() =>
		readGeometryImportCommand({
			...command,
			options: {
				...command.options,
				source: { ...command.options.source, rights_note: " " },
			},
		}),
	);
	assert.throws(() =>
		readGeometryImportCommand({ ...command, schema_version: true }),
	);
});
