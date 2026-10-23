// Real React, journal, domain, Terra Draw and its adapter. MapLibre's narrow
// public port is a fixture; native WebGL/provider/touch proof is separate.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { register } from "node:module";
import test from "node:test";
import React, { act, useState } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import { MapDrawingWorkspace } from "../src/components/design/MapDrawingWorkspace.tsx";
import { mapDrawingDraftStore } from "../src/data/MapDrawingDraftStore.ts";
import { applyGeometryCommand } from "../src/domain/geometryCommands.ts";
import { bindMapRing } from "../src/domain/mapDrawingGeometry.ts";
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
					typeof bad === "object"
						? bad
						: {
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

async function rig(t, options = {}) {
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
	// The application singleton intentionally keeps its open DB across remounts.
	// Reset only this test scope between separate rigs; reloads inside a rig keep it.
	for (const record of await mapDrawingDraftStore.list([scope], projectId))
		await mapDrawingDraftStore.clear(scope, record.body);
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
		selected = options.selected ?? null,
		nativeScope = scope,
		active = false,
		invalidReview = false;
	const client = {
		isCurrentScope: (value) => value === nativeScope,
		query: async (path, input) => {
			assert.equal(path, "geometry/review");
			queries.push(input);
			if (options.review) return options.review(input);
			return report(input.geometry, invalidReview);
		},
	};
	function Harness() {
		const [document, setDocument] = useState(options.geometry ?? geometry),
			[confirmed, setConfirmed] = useState(options.geometry ?? geometry);
		currentGeometry = document;
		confirm = setConfirmed;
		replaceGeometry = setDocument;
		return React.createElement(MapDrawingWorkspace, {
			geometry: document,
			confirmedGeometry: confirmed,
			projectId,
			locale: "en-GB",
			session: { query_scope: nativeScope },
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
			selected,
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
	if (options.pixelScale) {
		const map = maps.findLast((value) => !value.removed),
			scale = options.pixelScale;
		map.project = ({ lng, lat }) => ({ x: lng * scale, y: -lat * scale });
		map.unproject = ({ x, y }) => ({ lng: x / scale, lat: -y / scale });
	}
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
			records = await mapDrawingDraftStore.list([scope], projectId);
		});
		return records;
	}
	async function drag(from, to) {
		// The real pinned adapter consumes these DOM pointer events. The map's
		// linear projection remains a fixture, not native/GPU or touch evidence.
		const canvas = map().getCanvas(),
			a = map().project({ lng: from[0], lat: from[1] }),
			b = map().project({ lng: to[0], lat: to[1] });
		const pointer = (type, x, y, button = 0) => {
			const event = new window.Event(type, { bubbles: true, cancelable: true });
			Object.assign(event, {
				pointerId: 7,
				pointerType: "mouse",
				isPrimary: true,
				button,
				buttons: type === "pointerup" ? 0 : 1,
				clientX: x,
				clientY: y,
			});
			canvas.dispatchEvent(event);
		};
		await act(async () => {
			pointer("pointermove", a.x, a.y, -1);
			pointer("pointerdown", a.x, a.y);
			pointer("pointermove", a.x + 2, a.y);
			pointer("pointermove", b.x, b.y);
			pointer("pointerup", b.x, b.y);
			await Promise.resolve();
		});
		await until(
			() =>
				!document.body.textContent.includes("Saving drawing in this browser"),
		);
	}
	return {
		root,
		render,
		click,
		point,
		drag,
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
		select: async (value) => {
			selected = value;
			await render();
		},
		identity: async (value) => {
			nativeScope = value;
			await render();
		},
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

// Deliberately synthetic source claims and shapes. They exercise retained data,
// not survey precision, fire rules, source licensing or engineering approval.
const ringGeometry = {
	...geometry,
	sources: geometry.sources.map((source) => ({
		...source,
		spatial_precision_m: 0.002,
		permissions: { ...source.permissions, export: "prohibited" },
	})),
	obstacles: [
		{
			id: "synthetic_obstacle",
			name: "Synthetic obstacle",
			source_id: geometry.sources[0].id,
			roof_id: geometry.roofs[0].id,
			footprint_uv: [
				[1, 1],
				[3, 1],
				[3, 3],
				[1, 3],
			],
			height_m: 1.25,
			extrusion_axis_enu: [0, 0, 1],
		},
	],
	keepouts: [
		{
			id: "synthetic_keepout",
			name: "Synthetic keep-out",
			source_id: geometry.sources[0].id,
			roof_id: geometry.roofs[0].id,
			footprint_uv: [
				[10, 1],
				[12, 1],
				[12, 3],
				[10, 3],
			],
			reason: "Synthetic exclusion",
		},
	],
};
const ringCases = [
	{ kind: "roof_boundary", roof_id: geometry.roofs[0].id },
	{ kind: "roof_hole", roof_id: geometry.roofs[0].id, index: 0 },
	{ kind: "obstacle", id: "synthetic_obstacle" },
	{ kind: "keepout", id: "synthetic_keepout" },
];
const submitRing = async () =>
	act(async () =>
		document
			.querySelector("#lp-map-ring-properties")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
const confirmSource = async () =>
	act(async () => document.querySelector('[name="source_confirmed"]').click());
async function openRing(r, target) {
	if (target.kind === "roof_hole")
		await act(async () => {
			const select = document.querySelector(".lp-map-ring-selector select");
			select.value = "1";
			select.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	await r.click("Edit boundary on map");
	await until(
		() =>
			document.querySelector("#lp-map-ring-properties") &&
			!document.body.textContent.includes("Saving drawing in this browser"),
	);
	assert.deepEqual((await r.records())[0].drawing.target, target);
}
for (const target of ringCases)
	test(`real ${target.kind} UI keeps pointer edits through reload, refuses its invalid geometry and applies one exact project command`, async (t) => {
		const r = await rig(t, {
			geometry: ringGeometry,
			selected: target.roof_id ?? target.id,
			pixelScale: 1e7,
		});
		await openRing(r, target);
		await submitRing();
		await until(() =>
			document.querySelector('[name="source_confirmed"][aria-invalid="true"]'),
		);
		assert.equal(r.queries.length, 0);
		assert.equal(document.activeElement.name, "source_confirmed");
		assert.match(
			document.getElementById(
				document.activeElement.getAttribute("aria-describedby"),
			).textContent,
			/recorded source details/,
		);
		await confirmSource();
		const before = (await r.records())[0].drawing;
		await r.drag(before.vertices[1], [
			before.vertices[1][0] + 0.000001,
			before.vertices[1][1],
		]);
		const edited = (await r.records())[0].drawing;
		assert.notDeepEqual(
			edited.vertices,
			before.vertices,
			"actual pinned adapter processes a pointer transaction",
		);
		assert.equal(
			edited.source_confirmed,
			false,
			"new movement requires a new source declaration",
		);
		assert.deepEqual(edited.metric_vertices[0], before.metric_vertices[0]);
		assert.deepEqual(edited.metric_vertices[2], before.metric_vertices[2]);
		await r.click("Pause drawing");
		await until(() => !r.active);
		await act(async () => r.root.render(null));
		await r.render();
		await until(() => button("Open saved drawing"));
		await r.click("Open saved drawing");
		assert.deepEqual(
			(await r.records())[0].drawing.metric_vertices,
			edited.metric_vertices,
		);
		await confirmSource();
		r.invalidReview = {
			kind:
				target.kind === "obstacle"
					? "invalid_obstacle_polygon"
					: target.kind === "keepout"
						? "invalid_keepout_polygon"
						: "invalid_roof_polygon",
			category: "layout_conflict",
			object_id: target.roof_id ?? target.id,
			roof_id: geometry.roofs[0].id,
			related_id: null,
			required_m: null,
			actual_m: null,
		};
		await submitRing();
		await until(() =>
			document.body.textContent.includes("could not validate this boundary"),
		);
		assert.equal(r.commits.length, 0);
		assert.equal((await r.records())[0].drawing.prepared_geometry, null);
		assert.match(document.activeElement.textContent, /geometry check/);
		r.invalidReview = false;
		await submitRing();
		await until(() => !r.active && r.commits.length === 1);
		assert.deepEqual(r.commits[0].before, ringGeometry);
		assert.deepEqual(
			bindMapRing(r.geometry, target).ring.metric,
			edited.metric_vertices,
		);
		assert.deepEqual(r.geometry.sources, ringGeometry.sources);
		assert.equal(r.geometry.sources[0].permissions.export, "prohibited");
		assert.deepEqual(
			r.geometry.roofs[0].origin_enu,
			ringGeometry.roofs[0].origin_enu,
		);
		assert.equal(r.geometry.obstacles[0].height_m, 1.25);
		assert.deepEqual(r.geometry.obstacles[0].extrusion_axis_enu, [0, 0, 1]);
		assert.equal(r.geometry.keepouts[0].reason, "Synthetic exclusion");
		assert.ok(document.activeElement.classList.contains("lp-map-drawing"));
		assert.match(
			document.querySelector(".lp-drawing-status").textContent,
			/Boundary changes applied/,
		);
		await r.confirm(r.geometry);
		await until(
			() =>
				!document.querySelector("#lp-map-ring-properties") &&
				button("Edit boundary on map"),
		);
		assert.equal((await r.records()).length, 0);
	});

test("unchanged source-reviewed boundary adds no project command or calculation and keeps a visible result after raw retirement", async (t) => {
	const target = ringCases[0],
		r = await rig(t, { geometry: ringGeometry, selected: target.roof_id });
	await openRing(r, target);
	await confirmSource();
	await submitRing();
	await until(() => !r.active && button("Edit boundary on map"));
	assert.equal(r.commits.length, 0);
	assert.equal(r.queries.length, 0);
	assert.equal((await r.records()).length, 0);
	assert.match(
		document.querySelector(".lp-drawing-status").textContent,
		/boundary is unchanged/,
	);
	await r.select("synthetic_obstacle");
	assert.equal(document.querySelector(".lp-drawing-status"), null);
});

for (const invalidation of ["geometry", "identity"])
	test(`a ${invalidation} change while boundary review is pending cannot commit the obsolete result`, async (t) => {
		const gate = deferred(),
			target = ringCases[0];
		const r = await rig(t, {
			geometry: ringGeometry,
			selected: target.roof_id,
			pixelScale: 1e7,
			review: async (input) => {
				await gate.promise;
				return report(input.geometry, false);
			},
		});
		await openRing(r, target);
		const before = (await r.records())[0].drawing;
		await r.drag(before.vertices[1], [
			before.vertices[1][0] + 0.000001,
			before.vertices[1][1],
		]);
		await confirmSource();
		await submitRing();
		await until(() => r.queries.length === 1);
		if (invalidation === "geometry")
			await r.replaceGeometry({ ...ringGeometry, keepouts: [] });
		else await r.identity("c".repeat(64));
		await act(async () => gate.resolve());
		await until(
			() => !document.body.textContent.includes("Checking boundary geometry"),
		);
		assert.equal(r.commits.length, 0);
		assert.equal((await r.records())[0].drawing.prepared_geometry, null);
	});

test("an obsolete boundary result cannot commit after its prepared journal write was delayed", async (t) => {
	const gate = deferred(),
		target = ringCases[0],
		originalWrite = mapDrawingDraftStore.write;
	let held = false;
	mapDrawingDraftStore.write = async function (...args) {
		if (JSON.parse(args[2]).prepared_geometry) {
			held = true;
			await gate.promise;
		}
		return originalWrite.apply(this, args);
	};
	t.after(() => {
		mapDrawingDraftStore.write = originalWrite;
		gate.resolve();
	});
	const r = await rig(t, {
		geometry: ringGeometry,
		selected: target.roof_id,
		pixelScale: 1e7,
	});
	await openRing(r, target);
	const before = (await r.records())[0].drawing;
	await r.drag(before.vertices[1], [
		before.vertices[1][0] + 0.000001,
		before.vertices[1][1],
	]);
	await confirmSource();
	await submitRing();
	await until(() => held);
	await r.replaceGeometry({ ...ringGeometry, keepouts: [] });
	await act(async () => gate.resolve());
	await until(
		() => !document.body.textContent.includes("Checking boundary geometry"),
	);
	assert.equal(r.commits.length, 0);
	assert.ok(
		(await r.records())[0].drawing.prepared_geometry,
		"the protected candidate survives for recovery, without overwriting the new frame",
	);
});
