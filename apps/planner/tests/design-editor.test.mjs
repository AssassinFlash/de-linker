import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { IDBFactory } from "fake-indexeddb";
import React, { act, useState, useRef } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import {
	applyGeometryCommand,
	emptyGeometry,
} from "../src/domain/geometryCommands.ts";
import { moduleSummary } from "../src/domain/panelPoses.ts";
import { drawingBridge } from "../src/domain/mapDrawingGeometry.ts";
import { pointOnRoof } from "../src/domain/coordinates.ts";

register("./map-library-loader.mjs", import.meta.url);

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
		siteCentre = null,
		googleMapsApiKey = null,
		realMap = false,
		query = async () => {
			throw new Error("No request expected");
		},
	} = {},
) {
	const fixture = setupDom();
	const globals = new Map();
	if (realMap) {
		for (const name of ["getComputedStyle", "indexedDB"])
			globals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		globalThis.getComputedStyle = window.getComputedStyle.bind(window);
		Object.defineProperty(globalThis, "indexedDB", {
			configurable: true,
			value: new IDBFactory(),
		});
		const css = document.createElement("style");
		css.textContent =
			".sc-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#123456;--proto-neutral-600:#456789;--proto-teal-700:#0a665c;--proto-teal-400:#44bbcc;--proto-neutral-100:#eeeeee;}";
		document.head.append(css);
	}
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
			siteCentre,
			googleMapsApiKey,
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
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of globals) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
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

test("an address with a Google key opens the editable aerial map first", async (t) => {
	await mount(t, {
		siteCentre: [6.96, 50.94],
		googleMapsApiKey: "fixture-key",
	});
	assert.equal(button("Map").getAttribute("aria-pressed"), "true");
	assert.equal(button("3D").getAttribute("aria-pressed"), "false");
	await until(() => document.querySelector("[data-map-status]"));
});

test("map placement previews chosen rows and columns, cancels cleanly, and applies one array without coordinate input", async (t) => {
	const initial = structuredClone(flat);
	initial.arrays = [];
	initial.roofs[0].v_axis_enu = [0, 0.8, 0.6];
	initial.coordinate_system = {
		...initial.coordinate_system,
		north_reference: "true_north",
		north_source_id: "survey",
		anchor: {
			longitude_deg: 6.96,
			latitude_deg: 50.94,
			datum: "EPSG:4326",
			source_id: "survey",
		},
	};
	const app = await mount(t, { initial, realMap: true });
	await until(() => document.querySelector('[data-map-status="ready"]'));
	const { maps } = await import("./map-library-fixture.mjs");
	const map = maps.findLast((map) => !map.removed);
	const position = drawingBridge(initial).inverse(
		pointOnRoof(initial.roofs[0], [2, 3]),
	);
	const place = async () =>
		act(async () =>
			map.emit("click", {
				point: { x: 5, y: 5 },
				lngLat: { lng: position[0], lat: position[1] },
			}),
		);
	const modules = () =>
		map
			.getSource("linker-project-geometry")
			.data.features.filter((feature) => feature.properties.kind === "module");
	await click("Add module array");
	assert.equal(document.querySelector('[name="u"]'), null);
	assert.equal(document.querySelector('[name="v"]'), null);
	assert.equal(document.querySelector('[name="source"]'), null);
	assert.equal(document.querySelector('[name="rows"]').value, "1");
	assert.equal(button("Apply properties").disabled, true);
	await enter(document.querySelector('[name="rows"]'), "2");
	await enter(document.querySelector('[name="columns"]'), "3");
	map.hits = [];
	await place();
	assert.equal(
		modules().length,
		0,
		"outside-roof clicks do not place an array",
	);
	map.hits = [{ properties: { object_id: initial.roofs[0].id } }];
	await place();
	await until(() => modules().length === 6);
	assert.equal(app.edits, 0);
	assert.equal(app.current.arrays.length, 0);
	await enter(document.querySelector('[name="columns"]'), "4");
	await until(() => modules().length === 8);
	await click("Cancel properties");
	assert.equal(modules().length, 0);
	assert.equal(app.edits, 0);
	await click("Add module array");
	await enter(document.querySelector('[name="rows"]'), "2");
	await enter(document.querySelector('[name="columns"]'), "3");
	map.jumpTo({ center: [position[0], position[1]] });
	await click("Place panels at map centre");
	await until(() => modules().length === 6);
	const hash = location.hash;
	await click("Review panel layout");
	assert.equal(document.activeElement.name, "module");
	assert.equal(
		location.hash,
		hash,
		"review scroll does not change the saved-project route",
	);
	await click("Apply properties");
	assert.equal(app.edits, 1);
	assert.equal(app.current.arrays.length, 1);
	assert.equal(moduleSummary(app.current).count, 6);
	assert.ok(Math.abs(app.current.arrays[0].origin_uv[0] - 2) < 1e-6);
	assert.ok(Math.abs(app.current.arrays[0].origin_uv[1] - 3) < 1e-6);
	assert.equal(app.current.arrays[0].mount_tilt_deg, 0);
	assert.equal(app.current.arrays[0].source_id, "survey");
});

test("plan placement uses a roof click and the applied array remains draggable", async (t) => {
	const app = await mount(t, {
		initial: { ...flat, arrays: [] },
		siteCentre: [6.96, 50.94],
		realMap: true,
	});
	const oldPoint = Object.getOwnPropertyDescriptor(globalThis, "DOMPoint");
	globalThis.DOMPoint = class {
		constructor(x, y) {
			this.x = x;
			this.y = y;
		}
		matrixTransform() {
			return this;
		}
	};
	t.after(() => {
		if (oldPoint) Object.defineProperty(globalThis, "DOMPoint", oldPoint);
		else delete globalThis.DOMPoint;
	});
	await click("Add module array");
	assert.equal(button("Plan").getAttribute("aria-pressed"), "true");
	assert.equal(button("Map").disabled, true);
	const svg = document.querySelector(".sc-plan-svg");
	svg.getScreenCTM = () => ({
		a: 1,
		d: 1,
		inverse() {
			return this;
		},
	});
	svg.setPointerCapture = () => {};
	svg.hasPointerCapture = () => false;
	const pointer = async (type, target, x, y) =>
		act(async () => {
			const event = new window.Event(type, { bubbles: true });
			Object.assign(event, { pointerId: 1, button: 0, clientX: x, clientY: y });
			target.dispatchEvent(event);
		});
	const roof = svg.querySelector('[data-object="roof"]');
	await pointer("pointerdown", roof, 2, -3);
	await pointer("pointerup", roof, 2, -3);
	await until(() => svg.querySelectorAll(".sc-panel-shape").length === 1);
	assert.equal(app.edits, 0);
	await click("Apply properties");
	assert.deepEqual(app.current.arrays[0].origin_uv, [2, 3]);
	const panel = svg.querySelector(".sc-panel-shape");
	await pointer("pointerdown", panel, 2, -3);
	await pointer("pointermove", panel, 5, -4);
	await pointer("pointerup", panel, 5, -4);
	assert.equal(app.edits, 2);
	assert.deepEqual(app.current.arrays[0].origin_uv, [5, 4]);
});

test("keyboard numeric placement previews a concave roof position without a map or pointer", async (t) => {
	const initial = structuredClone(flat);
	initial.arrays = [];
	initial.roofs[0].boundary_uv = [
		[0, 0],
		[10, 0],
		[10, 2],
		[2, 2],
		[2, 10],
		[0, 10],
	];
	const app = await mount(t, { initial, locale: "de-DE" });
	await click("Add module array");
	assert.equal(button("Plan").getAttribute("aria-pressed"), "true");
	assert.equal(button("Map").disabled, true);
	const positions = document.querySelector(".sc-plan-position");
	assert.equal(positions.open, false, "coordinate entry stays optional");
	await act(async () => positions.querySelector("summary").click());
	const [u, v] = positions.querySelectorAll("input");
	assert.equal(button("Preview position").disabled, true);
	await enter(u, "0,5");
	await enter(v, "3,5");
	await click("Preview position");
	await until(() => document.querySelectorAll(".sc-panel-shape").length === 1);
	assert.equal(app.edits, 0);
	assert.equal(app.current.arrays.length, 0);
	await enter(u, "invalid");
	assert.equal(button("Preview position").disabled, true);
	await enter(u, "0,75");
	await click("Preview position");
	await click("Apply properties");
	assert.equal(app.edits, 1);
	assert.deepEqual(app.current.arrays[0].origin_uv, [0.75, 3.5]);
});

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

test("correcting a measured roof pitch keeps its array, holes and source", async (t) => {
	const initial = structuredClone(flat);
	const roof = initial.roofs[0];
	initial.sources[0].kind = "user_measurement";
	initial.sources[0].rights_basis = "user_attestation";
	roof.holes_uv = [
		[
			[15, 15],
			[16, 15],
			[16, 16],
			[15, 16],
		],
	];
	const app = await mount(t, { initial, locale: "de-DE" });
	await click(roof.name);
	await click("Edit numeric properties");
	const pitch = document.querySelector('[name="pitch"]');
	assert.ok(pitch, "a measured roof can be corrected after it is saved");
	assert.equal(pitch.value, "0");
	await enter(pitch, "30,5");
	await enter(document.querySelector('[name="bearing"]'), "180");
	await click("Apply properties");
	const changed = app.current.roofs[0];
	assert.equal(changed.id, roof.id);
	assert.deepEqual(changed.boundary_uv, roof.boundary_uv);
	assert.deepEqual(changed.holes_uv, roof.holes_uv);
	assert.deepEqual(app.current.arrays, initial.arrays);
	assert.deepEqual(app.current.sources, initial.sources);
	assert.deepEqual(
		changed.u_axis_enu.map((x) => x || 0),
		[-1, 0, 0],
	);
	assert.ok(
		Math.abs(changed.v_axis_enu[2] + Math.sin((30.5 * Math.PI) / 180)) < 1e-12,
	);
	await click(roof.name);
	await click("Edit numeric properties");
	await enter(
		document.querySelector('[name="name"]'),
		"Corrected measured roof",
	);
	await click("Apply properties");
	assert.deepEqual(app.current.roofs[0].u_axis_enu, changed.u_axis_enu);
	assert.deepEqual(app.current.roofs[0].v_axis_enu, changed.v_axis_enu);
});

test("the measured 30-degree production roof reopens with the angle the customer entered", async (t) => {
	const initial = structuredClone(flat);
	initial.sources[0].kind = "user_measurement";
	initial.sources[0].rights_basis = "user_attestation";
	const app = await mount(t, { initial });
	await click(initial.roofs[0].name);
	await click("Edit numeric properties");
	await enter(document.querySelector('[name="pitch"]'), "30");
	await click("Apply properties");
	const saved = structuredClone(app.current.roofs[0]);
	await click(saved.name);
	await click("Edit numeric properties");
	assert.equal(document.querySelector('[name="pitch"]').value, "30");
	await click("Apply properties");
	assert.deepEqual(app.current.roofs[0], saved);
});

test("a source-bound imported roof keeps its original orientation", async (t) => {
	const initial = structuredClone(flat);
	initial.sources[0].kind = "user_measurement";
	const roof = initial.roofs[0];
	await mount(t, {
		initial,
		geometryImports: {
			schema_version: 1,
			selected: { [roof.source_id]: "a".repeat(32) },
		},
	});
	await click(roof.name);
	await click("Edit numeric properties");
	assert.ok(document.querySelector('[name="boundary"]'));
	assert.equal(document.querySelector('[name="pitch"]'), null);
	assert.equal(document.querySelector('[name="bearing"]'), null);
});

test("invalid staged properties stay visible until corrected or cancelled", async (t) => {
	const app = await mount(t, { initial: flat });
	let revealed;
	window.HTMLElement.prototype.scrollIntoView = function () {
		revealed = this;
	};
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
	const rows = document.querySelector('[name="rows"]');
	assert.equal(document.activeElement, rows);
	assert.equal(revealed, rows.closest("label"));
	await click("Cancel properties");
	assert.equal(app.valid, true);
	assert.deepEqual(app.current, flat);
});

test("an existing array can change rows and mounting values while preserving its position", async (t) => {
	const app = await mount(t, { initial: flat, locale: "de-DE" });
	await click(flat.arrays[0].name);
	await click("Edit numeric properties");
	await enter(document.querySelector('[name="rows"]'), "1");
	await enter(document.querySelector('[name="row_gap"]'), "0,2");
	assert.equal(
		app.current.arrays[0].rows,
		2,
		"preview edits are not project edits",
	);
	assert.equal(document.querySelectorAll(".sc-panel-shape").length, 3);
	await click("Apply properties");
	assert.equal(app.edits, 1);
	assert.equal(app.current.arrays[0].id, flat.arrays[0].id);
	assert.deepEqual(app.current.arrays[0].origin_uv, flat.arrays[0].origin_uv);
	assert.deepEqual(app.current.arrays[0].excluded_slots, []);
	assert.equal(app.current.arrays[0].row_gap_m, 0.2);
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
		document.querySelector(".sc-module-table summary").click(),
	);
	const select = [...document.querySelectorAll("button")].find(
		(button) => button.textContent.trim() === "Select module",
	);
	await act(async () => select.click());
	await click("Exclude module");
	assert.equal(app.edits, 1);
	assert.equal(moduleSummary(app.current).count, 4);
	assert.equal(
		document.querySelectorAll('.sc-panel-shape[data-excluded="true"]').length,
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
	const exportField = document.querySelector('[name="export"]');
	assert.equal(exportField.value, "unknown");
	await act(async () => {
		exportField.value = "permitted";
		exportField.dispatchEvent(new Event("change", { bubbles: true }));
	});
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
	assert.equal(app.current.sources.at(-1).permissions.export, "permitted");
});

test("a measured module can be added without a product catalogue or a guessed power", async (t) => {
	const app = await mount(t, {
		locale: "de-DE",
		initial: { ...flat, module_specs: [], arrays: [] },
		query: async () => {
			throw new Error("catalogue unavailable");
		},
	});
	await click("Add module specification");
	for (const [name, value] of Object.entries({
		panel_length_mm: "1880",
		panel_width_mm: "1080",
		panel_thickness_mm: "32",
		panel_power_w: "423",
	})) {
		const input = document.querySelector('input[name="' + name + '"]');
		assert.equal(input.value, "");
		await enter(input, value);
	}
	await click("Apply properties");
	const [spec] = app.current.module_specs;
	assert.equal(app.edits, 1);
	assert.equal(spec.stc_power_w, 423);
	assert.equal(spec.length_m, 1.88);
	assert.equal(spec.width_m, 1.08);
	assert.equal(spec.gamma_pdc_per_c, null);
	assert.equal(spec.source.woo, undefined);
});
