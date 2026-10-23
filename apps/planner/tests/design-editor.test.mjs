import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState, useRef } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import {
	applyGeometryCommand,
	emptyGeometry,
} from "../src/domain/geometryCommands.ts";
import { moduleSummary } from "../src/domain/panelPoses.ts";

function button(text) {
	const result = [...document.querySelectorAll("button")].find(
		(element) => element.textContent.trim() === text,
	);
	assert.ok(result, `Missing ${text}`);
	return result;
}
async function click(text) {
	await act(async () => button(text).click());
}

async function mount(
	t,
	{
		initial = emptyGeometry(),
		geometryImports = { schema_version: 1, selected: {} },
		locale = "en-GB",
		query = async () => {
			throw new Error("No request expected");
		},
	} = {},
) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { DesignEditor } =
		await import("../src/components/design/DesignEditor.tsx");
	const root = createRoot(fixture.element);
	let current = initial,
		edits = 0,
		valid = true;
	function Harness() {
		const [geometry, setGeometry] = useState(initial),
			[allowed, setAllowed] = useState(true);
		valid = allowed;
		const latest = useRef(initial);
		return React.createElement(DesignEditor, {
			geometry,
			geometryImports,
			locale,
			projectId: "1".repeat(32),
			session: { query_scope: "2".repeat(64) },
			client: { query, isCurrentScope: () => true },
			recheck() {
				throw new Error("No recheck expected");
			},
			onValidity: setAllowed,
			commit(command) {
				try {
					current = applyGeometryCommand(latest.current, command);
					latest.current = current;
					edits++;
					setGeometry(current);
					return true;
				} catch {
					return false;
				}
			},
		});
	}
	t.after(() => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(React.StrictMode, null, React.createElement(Harness)),
		),
	);
	return {
		get current() {
			return current;
		},
		get edits() {
			return edits;
		},
		get valid() {
			return valid;
		},
	};
}

test("measured roof intake preserves decimal locale, explicit source and one command", async (t) => {
	const app = await mount(t, { locale: "de-DE" });
	await click("Add roof face");
	assert.equal(app.valid, false);
	for (const [name, value] of Object.entries({
		name: "Synthetic sloping roof",
		width: "12,5",
		length: "8",
		pitch: "30",
		bearing: "180",
		source: "Synthetic measured dimensions",
		rights_note: "Synthetic test permission",
	}))
		await enter(document.querySelector(`[name="${name}"]`), value);
	await act(async () => document.querySelector('[name="rights"]').click());
	await click("Apply properties");
	assert.equal(app.valid, true);
	assert.equal(app.edits, 1);
	assert.equal(app.current.roofs.length, 1);
	assert.deepEqual(app.current.roofs[0].boundary_uv, [
		[0, 0],
		[12.5, 0],
		[12.5, 8],
		[0, 8],
	]);
	assert.equal(app.current.sources[0].spatial_precision_m, null);
	assert.equal(app.current.coordinate_system.north_reference, "unreferenced");
	assert.equal(app.current.sources[0].permissions.export, "unknown");
});

test("invalid staged properties stay visible until corrected or cancelled", async (t) => {
	const app = await mount(t, { initial: flat });
	await click(flat.arrays[0].name);
	await click("Edit numeric properties");
	await enter(document.querySelector('[name="rows"]'), "2.5");
	await click("Apply properties");
	assert.equal(app.valid, false);
	assert.equal(app.edits, 0);
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
	assert.equal(
		document.querySelector('[name="rows"]').getAttribute("aria-invalid"),
		"true",
	);
	await click("Cancel properties");
	assert.equal(app.valid, true);
	assert.deepEqual(app.current, flat);
});

test("a bound original hash stays immutable while its source notes can be edited", async (t) => {
	const initial = structuredClone(flat),
		source = initial.sources[0];
	source.reference_sha256 = "a".repeat(64);
	const app = await mount(t, {
		initial,
		geometryImports: {
			schema_version: 1,
			selected: { [source.id]: "b".repeat(32) },
		},
	});
	await click(source.note);
	const hash = document.querySelector('[name="hash"]');
	assert.equal(hash.readOnly, true);
	await enter(document.querySelector('[name="note"]'), "Updated source notes");
	// Even an out-of-band DOM change cannot detach the bound hash on submission.
	await enter(hash, "0".repeat(64));
	await click("Apply properties");
	assert.equal(app.current.sources[0].note, "Updated source notes");
	assert.equal(
		app.current.sources[0].reference_sha256,
		source.reference_sha256,
	);
	assert.equal(app.valid, true);
});

test("module exclusion updates the same plan, object selection and derived quantity", async (t) => {
	const app = await mount(t, { initial: flat });
	await click(flat.arrays[0].name);
	await act(async () =>
		document.querySelector(".lp-module-table summary").click(),
	);
	const select = [...document.querySelectorAll("button")].find(
		(button) => button.textContent.trim() === "Select module",
	);
	await act(async () => select.click());
	await click("Exclude module");
	assert.equal(app.edits, 1);
	assert.equal(moduleSummary(app.current).count, 4);
	assert.equal(
		document.querySelectorAll('.lp-panel-shape[data-excluded="true"]').length,
		2,
	);
	await click("Restore module");
	assert.equal(moduleSummary(app.current).count, 5);
});

test("a late layout check is retained as previous output and cannot select current objects", async (t) => {
	const gate = deferred();
	let calls = 0;
	const report = {
		schema_version: 1,
		geometry_sha256: "a".repeat(64),
		runtime_sha256: "b".repeat(64),
		checker: "roof_plane_layout_v4",
		uv_resolution_m: 1e-15,
		libraries: { shapely: "2.2.0", geos: "3.14.1" },
		geometry_status: "no_conflicts_detected",
		engineering_status: "not_evaluated",
		review_complete: true,
		diagnostics_truncated: false,
		issue_count: 1,
		conflict_count: 0,
		candidate_checks: 0,
		module_count: 5,
		declared_stc_kwp: 2.5,
		limits: {
			max_diagnostics: 200,
			max_candidate_checks: 200000,
			max_uv_resolution_m: 1e-9,
		},
		issues: [
			{
				kind: "source_precision_unspecified",
				object_id: flat.sources[0].id,
				roof_id: null,
				related_id: null,
				category: "missing_input",
				required_m: null,
				actual_m: null,
			},
		],
	};
	await mount(t, {
		initial: flat,
		query: async (path, body) => {
			calls++;
			assert.equal(path, "geometry/review");
			assert.deepEqual(body.geometry, flat);
			return gate.promise;
		},
	});
	await click("Check layout");
	await click(flat.arrays[0].name);
	await click("Edit numeric properties");
	await enter(
		document.querySelector('[name="name"]'),
		"Changed while checking",
	);
	await click("Apply properties");
	await act(async () => gate.resolve(report));
	await until(() => document.body.textContent.includes("Previous check:"));
	assert.equal(calls, 1);
	assert.equal(
		button("Source measurement precision is unknown.").disabled,
		true,
	);
});

test("manual roof intake marks the unsupported vertical boundary at its field", async (t) => {
	const app = await mount(t);
	await click("Add roof face");
	for (const [name, value] of Object.entries({
		name: "Synthetic roof",
		width: "10",
		length: "8",
		pitch: "90",
		bearing: "180",
		source: "Synthetic dimensions",
		rights_note: "Synthetic test rights",
	}))
		await enter(document.querySelector(`[name="${name}"]`), value);
	await act(async () => document.querySelector('[name="rights"]').click());
	await click("Apply properties");
	assert.equal(app.edits, 0);
	assert.equal(
		document.querySelector('[name="pitch"]').getAttribute("aria-invalid"),
		"true",
	);
	assert.equal(document.querySelector('[name="pitch"]').value, "90");
	await enter(document.querySelector('[name="pitch"]'), "89.9");
	await click("Apply properties");
	assert.equal(app.edits, 1);
});
