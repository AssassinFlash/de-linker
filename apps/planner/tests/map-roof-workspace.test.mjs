// Real React, journal, domain, Terra Draw and its adapter. MapLibre's narrow
// public port is a fixture; native WebGL/provider/touch proof is separate.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { register } from "node:module";
import test from "node:test";
import React, { act, useState } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { MapRoofWorkspace } from "../src/components/design/MapRoofWorkspace.tsx";
import { mapRoofDraftStore } from "../src/data/MapRoofDraftStore.ts";
import { applyGeometryCommand } from "../src/domain/geometryCommands.ts";
register("./map-library-loader.mjs", import.meta.url);
const asset = JSON.parse(
	readFileSync(
		new URL(
			"../../../fixtures/planning/geometry-import-asset.json",
			import.meta.url,
		),
		"utf8",
	),
);
const geometry = asset.metadata.geometry_import.geometry,
	projectId = asset.project_id,
	scope = "a".repeat(64);
const button = (name) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim() === name,
	);
const report = (input, bad) => {
	const roof = input.roofs.at(-1);
	return {
		schema_version: 1,
		geometry_sha256: "a".repeat(64),
		runtime_sha256: "b".repeat(64),
		checker: "synthetic_layout_fixture",
		uv_resolution_m: 1e-14,
		libraries: { shapely: "fixture", geos: "fixture" },
		geometry_status: bad ? "conflicts_detected" : "no_conflicts_detected",
		engineering_status: "not_evaluated",
		review_complete: true,
		diagnostics_truncated: false,
		issue_count: bad ? 1 : 0,
		conflict_count: bad ? 1 : 0,
		candidate_checks: 0,
		module_count: 0,
		declared_stc_kwp: 0,
		limits: {
			max_diagnostics: 200,
			max_candidate_checks: 250000,
			max_uv_resolution_m: 1e-9,
		},
		issues: bad
			? [
					{
						kind: "invalid_roof_polygon",
						category: "layout_conflict",
						object_id: roof.id,
						roof_id: roof.id,
						related_id: null,
						required_m: null,
						actual_m: null,
					},
				]
			: [],
	};
};

async function rig(t) {
	const dom = setupDom(),
		previous = new globalThis.Map();
	for (const name of [
		"indexedDB",
		"MutationObserver",
		"getComputedStyle",
		"requestAnimationFrame",
		"cancelAnimationFrame",
	])
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	globalThis.MutationObserver = window.MutationObserver;
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	globalThis.requestAnimationFrame = (cb) =>
		setTimeout(() => cb(Date.now()), 0);
	globalThis.cancelAnimationFrame = clearTimeout;
	const style = document.createElement("style");
	style.textContent =
		".lp-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#123456;--proto-neutral-600:#456789;--proto-teal-700:#0a665c;--proto-teal-400:#44bbcc;--proto-neutral-100:#eeeeee;}";
	document.head.append(style);
	const { createRoot } = await import("react-dom/client"),
		{ maps } = await import("./map-library-fixture.mjs");
	const root = createRoot(dom.element),
		commits = [],
		queries = [],
		camera = { current: null };
	let currentGeometry,
		confirm,
		replaceGeometry,
		active = false,
		invalidReview = false;
	const client = {
		isCurrentScope: (value) => value === scope,
		query: async (path, input) => {
			assert.equal(path, "geometry/review");
			queries.push(input);
			return report(input.geometry, invalidReview);
		},
	};
	function Harness() {
		const [document, setDocument] = useState(geometry),
			[confirmed, setConfirmed] = useState(geometry);
		currentGeometry = document;
		confirm = setConfirmed;
		replaceGeometry = setDocument;
		return React.createElement(MapRoofWorkspace, {
			geometry: document,
			confirmedGeometry: confirmed,
			projectId,
			locale: "en-GB",
			session: { query_scope: scope },
			client,
			recheck() {},
			recoveryScopes: [scope],
			commit: (command) => {
				commits.push(command);
				setDocument((previous) => applyGeometryCommand(previous, command));
				return true;
			},
			onActivity: (value) => {
				active = value;
			},
			mapModuleUrl: null,
			poses: [],
			selected: null,
			select() {},
			disabled: false,
			openReferences() {},
			camera,
		});
	}
	const render = async () =>
		act(async () => root.render(React.createElement(Harness)));
	await render();
	await until(
		() =>
			document.querySelector('[data-map-status="ready"]') &&
			!document.body.textContent.includes("Checking saved drawings"),
	);
	t.after(async () => {
		await dom.dispose(root);
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	async function click(name) {
		const node = button(name);
		assert.ok(node, name);
		await act(async () => node.click());
	}
	function map() {
		return maps.findLast((value) => !value.removed);
	}
	async function point(lng, lat) {
		await act(async () => {
			const canvas = map().getCanvas();
			for (const type of ["pointerdown", "pointerup"]) {
				const event = new window.Event(type, { bubbles: true });
				Object.assign(event, {
					pointerId: 1,
					isPrimary: true,
					button: 0,
					clientX: 20,
					clientY: 20,
				});
				canvas.dispatchEvent(event);
			}
			map().emit("click", {
				point: { x: 20, y: 20 },
				originalEvent: { detail: 1 },
				lngLat: { lng, lat },
			});
		});
		await until(
			() =>
				!document.body.textContent.includes("Saving drawing in this browser"),
		);
	}
	async function records() {
		let records;
		await act(async () => {
			records = await mapRoofDraftStore.list([scope], projectId);
		});
		return records;
	}
	return {
		root,
		render,
		click,
		point,
		map,
		records,
		commits,
		queries,
		set invalidReview(value) {
			invalidReview = value;
		},
		get geometry() {
			return currentGeometry;
		},
		get active() {
			return active;
		},
		confirm: async (value) => act(async () => confirm(value)),
		replaceGeometry: async (value) => act(async () => replaceGeometry(value)),
	};
}
test("real drawing UI resumes a one-point journal, stages a roof, checks inputs and joins one project command", async (t) => {
	const r = await rig(t);
	await r.click("Start roof drawing");
	await until(() => r.active);
	await r.point(6.96, 50.94);
	assert.equal((await r.records())[0].drawing.vertices.length, 1);
	assert.equal(button("Close outline and review").disabled, true);
	await r.click("Pause drawing");
	await until(() => !r.active);
	await act(async () => r.root.render(null));
	await r.render();
	await until(() => button("Open saved drawing"));
	assert.equal(r.commits.length, 0);
	await r.click("Open saved drawing");
	await until(
		() => r.active && document.querySelector('[data-map-status="ready"]'),
	);
	await r.point(6.9601, 50.94);
	await r.point(6.9601, 50.9401);
	assert.equal((await r.records())[0].drawing.vertices.length, 3);
	await r.click("Close outline and review");
	await until(() => document.querySelector(".lp-drawing-properties"));
	assert.ok(
		[...r.map().sources.keys()].some((id) => id.startsWith("linker-draw-")),
		"actual Terra adapter has mounted its staged sources",
	);
	for (const [name, value] of Object.entries({
		name: "Synthetic entered roof",
		pitch: "90",
		bearing: "180",
		height: "8.125",
		source: "Synthetic supplied drawing",
		rights: "Synthetic test permission",
		calibration: "Synthetic coordinates, not survey data",
	}))
		await enter(document.querySelector(`[name="${name}"]`), value);
	await act(async () =>
		document
			.querySelector('.lp-drawing-properties input[type="checkbox"]')
			.click(),
	);
	const submit = async () =>
		act(async () =>
			document
				.querySelector(".lp-drawing-properties")
				.dispatchEvent(
					new window.Event("submit", { bubbles: true, cancelable: true }),
				),
		);
	await submit();
	await until(() =>
		document.querySelector('[name="pitch"][aria-invalid="true"]'),
	);
	assert.equal(r.queries.length, 0);
	assert.equal(r.commits.length, 0);
	assert.equal(document.activeElement.name, "pitch");
	const invalidPitch = document.activeElement;
	assert.match(
		document.getElementById(invalidPitch.getAttribute("aria-describedby"))
			.textContent,
		/Some roof or source details are missing or invalid/,
	);
	assert.ok(invalidPitch.closest("label").querySelector('[role="alert"]'));
	await enter(document.querySelector('[name="pitch"]'), "30");
	r.invalidReview = true;
	await submit();
	await until(() =>
		document.body.textContent.includes("could not pass the geometry check"),
	);
	assert.equal(r.commits.length, 0);
	assert.equal((await r.records())[0].drawing.phase, "staged");
	assert.match(document.activeElement.textContent, /geometry check/);
	assert.ok(document.activeElement.closest(".lp-drawing-properties"));
	r.invalidReview = false;
	await submit();
	await until(() => !r.active && r.commits.length === 1);
	assert.deepEqual(r.commits[0].before, geometry);
	assert.equal(r.geometry.roofs.length, geometry.roofs.length + 1);
	assert.equal(r.geometry.roofs.at(-1).origin_enu[2], 8.125);
	assert.equal(r.geometry.sources.at(-1).spatial_precision_m, null);
	assert.ok(document.activeElement.classList.contains("lp-map-drawing"));
	assert.match(
		document.querySelector(".lp-drawing-status").textContent,
		/Roof added to the project draft/,
	);
	const appliedGeometry = r.geometry;
	await r.replaceGeometry(geometry);
	assert.match(
		document.querySelector(".lp-drawing-status").textContent,
		/Drawing paused and retained/,
	);
	await r.click("Resume drawing");
	await submit();
	await until(() => !r.active && r.commits.length === 2);
	assert.ok(document.activeElement.classList.contains("lp-map-drawing"));
	assert.deepEqual(r.geometry, appliedGeometry);
	await r.replaceGeometry(geometry);
	await r.replaceGeometry(appliedGeometry);
	assert.match(
		document.querySelector(".lp-drawing-status").textContent,
		/Roof added to the project draft/,
	);
	assert.equal(
		(await r.records()).length,
		1,
		"local application cannot clear recovery",
	);
	await r.click("Close drawing preview");
	await until(() => button("Open saved drawing"));
	assert.equal(
		(await r.records()).length,
		1,
		"closing a preview cannot clear unconfirmed recovery",
	);
	await r.confirm(r.geometry);
	await until(
		() =>
			!button("Open saved drawing") &&
			!document.body.textContent.includes("Checking saved drawings"),
	);
	assert.equal((await r.records()).length, 0);
});
test("provider replacement restores an open prefix only after the new map loads and keeps its points", async (t) => {
	const r = await rig(t);
	await r.click("Start roof drawing");
	await until(() => r.active);
	await r.point(6.96, 50.94);
	const old = r.map();
	await r.click("Load street map");
	await until(
		() =>
			r.map() !== old && document.querySelector('[data-map-status="ready"]'),
	);
	assert.equal(old.removals, 1);
	assert.equal(r.active, true);
	assert.ok(
		[...r.map().sources.keys()].some((id) =>
			id.startsWith("linker-draw-prefix-"),
		),
	);
	await r.point(6.9601, 50.94);
	assert.equal((await r.records())[0].drawing.vertices.length, 2);
	await r.click("Pause drawing");
	await until(() => !r.active);
});
