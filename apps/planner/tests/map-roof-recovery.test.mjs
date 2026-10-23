import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred } from "./dom-fixture.mjs";
import { MapDrawingDraftStore } from "../src/data/MapDrawingDraftStore.ts";
import { useMapDrawingDraft } from "../src/data/useMapDrawingDraft.ts";
import {
	startMapRoofDraft,
	appendMapRoofVertex,
	mapRoofDraftCommand,
} from "../src/domain/mapRoofDraft.ts";
import { applyGeometryCommand } from "../src/domain/geometryCommands.ts";
import { startMapRingDraft } from "../src/domain/mapRingDraft.ts";
import {
	editMapDrawingVertex,
	mapDrawingDraftCommand,
} from "../src/domain/mapDrawingDraft.ts";
import {
	mapPolygon,
	quantizeMapPosition,
} from "../src/domain/mapDrawingGeometry.ts";

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
	projectId = asset.project_id;
const scope = "a".repeat(64),
	priorScope = "b".repeat(64),
	otherScope = "c".repeat(64);
const body = (draft) => JSON.stringify(draft);

const moveRing = (draft, delta = 0.000001) => {
	const vertices = [...draft.vertices];
	vertices[1] = quantizeMapPosition([vertices[1][0] + delta, vertices[1][1]]);
	return editMapDrawingVertex(draft, mapPolygon(vertices), "dragCoordinate");
};
async function rig(t, custom = null) {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const store = new MapDrawingDraftStore();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	let flow,
		nativeScope = scope,
		props = {
			projectId,
			geometry,
			confirmedGeometry: null,
			locale: "de-DE",
			session: { query_scope: scope },
			client: { isCurrentScope: (value) => value === nativeScope },
			recoveryScopes: [scope],
			store: custom ? custom(store) : store,
		};
	function Harness() {
		flow = useMapDrawingDraft(props);
		return React.createElement(
			"p",
			null,
			flow.drawing?.schema_version === 1
				? flow.drawing.fields.name
				: (flow.drawing?.target.kind ?? "none"),
		);
	}
	const render = async (changes = {}) => {
		props = { ...props, ...changes };
		await act(async () => root.render(React.createElement(Harness)));
	};
	await render();
	await until(() => !flow.checking);
	t.after(async () => {
		await dom.dispose(root);
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	return {
		store,
		root,
		render,
		get flow() {
			return flow;
		},
		records: async () => {
			let records;
			await act(async () => {
				records = await store.list([scope], projectId);
			});
			return records;
		},
		native: (value) => {
			nativeScope = value;
		},
	};
}
test("drawing journal uses exact CAS, refuses a stale tab, and never deletes its newer copy", async (t) => {
	const r = await rig(t),
		draft = startMapRoofDraft(projectId, geometry, "de-DE"),
		first = body(draft),
		next = body(appendMapRoofVertex(draft, [6.96, 50.94]));
	await r.store.write(scope, null, first);
	await r.store.write(scope, first, next);
	await assert.rejects(
		r.store.write(
			scope,
			first,
			body({ ...draft, fields: { ...draft.fields, name: "stale tab" } }),
		),
		/conflict/,
	);
	await assert.rejects(r.store.clear(scope, first), /conflict/);
	assert.equal((await r.records())[0].body, next);
	assert.deepEqual(await r.store.list([otherScope], projectId), []);
	assert.deepEqual(await r.store.list([scope], "f".repeat(32)), []);
});

test("the same journal restores unchanged v1 bytes and v2 coordinate pairs, then settles an uncertain ring write before newer edits", async (t) => {
	const writes = [];
	let lose = false;
	const r = await rig(t, (store) => ({
		list: (...args) => store.list(...args),
		clear: (...args) => store.clear(...args),
		write: async (...args) => {
			writes.push({ previous: args[1], next: args[2] });
			await store.write(...args);
			if (lose) {
				lose = false;
				throw new Error("unknown ring acknowledgement");
			}
		},
	}));
	const legacy = body(
		appendMapRoofVertex(
			startMapRoofDraft(projectId, geometry, "de-DE"),
			[6.96, 50.94],
		),
	);
	const ring = startMapRingDraft(projectId, geometry, "en-GB", {
		kind: "roof_hole",
		roof_id: geometry.roofs[0].id,
		index: 0,
	});
	await r.store.write(scope, null, legacy);
	await r.store.write(scope, null, body(ring));
	await act(async () => r.flow.reload());
	await until(() => !r.flow.checking);
	const record = r.flow.records.find(
		(entry) => entry.drawing.schema_version === 2,
	);
	assert.equal(r.flow.records.length, 2);
	await act(async () => r.flow.begin({ kind: "restore", record }));
	assert.equal(
		r.flow.drawing.locale,
		"en-GB",
		"reopening in DE preserves the drawing's own locale",
	);
	const a = moveRing(r.flow.drawing),
		b = moveRing(a);
	lose = true;
	await act(async () => r.flow.update(a).catch(() => undefined));
	assert.equal(r.flow.storageFailed, true);
	await act(async () => r.flow.update(b));
	assert.equal(r.flow.storageFailed, false);
	assert.deepEqual(
		writes.slice(-3).map((entry) => entry.next),
		[body(a), body(a), body(b)],
	);
	assert.deepEqual(
		writes.at(-2),
		writes.at(-3),
		"exact uncertain intent is acknowledged before advancing",
	);
	await act(async () => r.flow.pause());
	await act(async () => r.flow.hide());
	await until(() => !r.flow.checking);
	assert.equal(
		r.flow.records.find((entry) => entry.drawing.schema_version === 1).body,
		legacy,
	);
	const restored = r.flow.records.find(
		(entry) => entry.drawing.schema_version === 2,
	);
	await act(async () => r.flow.begin({ kind: "restore", record: restored }));
	assert.deepEqual(r.flow.drawing.metric_vertices, b.metric_vertices);
	assert.deepEqual(r.flow.drawing.target, b.target);
});

test("a separate ring copy keeps the same edited object and retires only its exact server-confirmed result", async (t) => {
	const r = await rig(t);
	await act(async () =>
		r.flow.begin({
			kind: "edit_ring",
			target: { kind: "roof_boundary", roof_id: geometry.roofs[0].id },
		}),
	);
	await until(() => !r.flow.writing);
	const original = (await r.records())[0];
	await r.store.write(scope, original.body, body(moveRing(original.drawing)));
	const own = {
		...moveRing(r.flow.drawing, -0.000001),
		source_confirmed: true,
	};
	await act(async () => r.flow.update(own).catch(() => undefined));
	assert.equal(r.flow.storageFailed, true);
	await act(async () => r.flow.fork());
	await until(() => !r.flow.writing);
	assert.notEqual(r.flow.drawing.key, own.key);
	assert.deepEqual(r.flow.drawing.target, own.target);
	assert.deepEqual(
		mapDrawingDraftCommand(r.flow.drawing),
		mapDrawingDraftCommand(own),
	);
	const applied = applyGeometryCommand(
		geometry,
		mapDrawingDraftCommand(r.flow.drawing),
	);
	await act(async () =>
		r.flow.update({ ...r.flow.drawing, prepared_geometry: applied }),
	);
	await act(async () => r.flow.pause());
	await r.render({ geometry: applied, confirmedGeometry: geometry });
	assert.equal((await r.records()).length, 2);
	await r.render({ confirmedGeometry: applied });
	await until(() => !r.flow.drawing);
	const retained = await r.records();
	assert.equal(retained.length, 1);
	assert.equal(
		retained[0].drawing.key,
		original.drawing.key,
		"the competing tab's raw edit is untouched",
	);
});
test("serialized writes preserve real new points and invalid fields through pause, hide and recovery", async (t) => {
	const r = await rig(t);
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	const one = appendMapRoofVertex(r.flow.drawing, [6.96, 50.94]);
	const two = appendMapRoofVertex(one, [6.9601, 50.94]);
	await act(async () => {
		void r.flow.update(one);
		void r.flow.update({
			...two,
			fields: { ...two.fields, pitch: "12,,invalid" },
		});
	});
	await until(() => !r.flow.writing);
	assert.deepEqual((await r.records())[0].drawing.vertices, two.vertices);
	await act(async () => r.flow.pause());
	assert.equal(r.flow.active, false);
	await act(async () => r.flow.hide());
	await until(() => !r.flow.checking);
	await act(async () =>
		r.flow.begin({ kind: "restore", record: r.flow.records[0] }),
	);
	assert.equal(r.flow.drawing.fields.pitch, "12,,invalid");
	await act(async () =>
		r.flow.update(appendMapRoofVertex(r.flow.drawing, [6.9601, 50.9401])),
	);
	assert.deepEqual(r.flow.drawing.vertices.slice(0, 2), two.vertices);
});
test("only native-granted prior scopes are exposed; identity changes fence late reads and callbacks", async (t) => {
	const gate = deferred();
	let hold = false;
	const r = await rig(t, (store) => ({
		write: (...args) => store.write(...args),
		clear: (...args) => store.clear(...args),
		list: async (...args) => {
			if (hold) await gate.promise;
			return store.list(...args);
		},
	}));
	const draft = startMapRoofDraft(projectId, geometry, "de-DE");
	await r.store.write(
		priorScope,
		null,
		body({
			...draft,
			fields: { ...draft.fields, name: "prior private drawing" },
		}),
	);
	await r.render({ recoveryScopes: [scope, priorScope] });
	await until(() => !r.flow.checking);
	assert.equal(r.flow.records.length, 1);
	await act(async () =>
		r.flow.begin({ kind: "restore", record: r.flow.records[0] }),
	);
	const oldUpdate = r.flow.update;
	hold = true;
	r.native(otherScope);
	await r.render({
		session: { query_scope: otherScope },
		recoveryScopes: [otherScope],
	});
	assert.equal(r.flow.drawing, null);
	assert.deepEqual(r.flow.records, []);
	await assert.rejects(
		oldUpdate({ ...draft, fields: { ...draft.fields, name: "late write" } }),
		/session_changed/,
	);
	gate.resolve();
	await until(() => !r.flow.checking);
	assert.deepEqual(r.flow.records, []);
	assert.equal(
		(await r.store.list([priorScope], projectId))[0].drawing.fields.name,
		"prior private drawing",
	);
});
test("unknown local write outcomes remain retryable; a stale tab can explicitly fork without overwriting", async (t) => {
	let lose = true;
	const r = await rig(t, (store) => ({
		list: (...args) => store.list(...args),
		clear: (...args) => store.clear(...args),
		write: async (...args) => {
			await store.write(...args);
			if (lose) {
				lose = false;
				throw new Error("unknown local acknowledgement");
			}
		},
	}));
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	assert.equal(r.flow.storageFailed, true);
	await act(async () => r.flow.flush());
	assert.equal(r.flow.storageFailed, false);
	const old = (await r.records())[0];
	await r.store.write(
		scope,
		old.body,
		body({
			...old.drawing,
			fields: { ...old.drawing.fields, name: "newer tab" },
		}),
	);
	await act(async () =>
		r.flow
			.update({
				...r.flow.drawing,
				fields: { ...r.flow.drawing.fields, name: "this tab" },
			})
			.catch(() => undefined),
	);
	assert.equal(r.flow.storageFailed, true);
	await act(async () => r.flow.discard());
	assert.equal(r.flow.storageFailed, true);
	assert.equal((await r.records())[0].drawing.fields.name, "newer tab");
	await act(async () => r.flow.fork());
	await until(() => !r.flow.writing);
	assert.deepEqual(
		(await r.records()).map((item) => item.drawing.fields.name).sort(),
		["newer tab", "this tab"],
	);
});
test("a newer buffer settles exact uncertain bytes before advancing, including repeated lost acknowledgements", async (t) => {
	let lose = 2;
	const writes = [];
	const r = await rig(t, (store) => ({
		list: (...args) => store.list(...args),
		clear: (...args) => store.clear(...args),
		write: async (...args) => {
			writes.push({ previous: args[1], next: args[2] });
			await store.write(...args);
			if (JSON.parse(args[2]).vertices.length === 1 && lose-- > 0)
				throw new Error("unknown local acknowledgement");
		},
	}));
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	const zero = body(r.flow.drawing),
		one = appendMapRoofVertex(r.flow.drawing, [6.96, 50.94]),
		two = appendMapRoofVertex(one, [6.9601, 50.94]),
		newer = { ...two, fields: { ...two.fields, pitch: "12,,invalid" } };
	await act(async () => r.flow.update(one).catch(() => undefined));
	await act(async () => r.flow.update(newer).catch(() => undefined));
	assert.equal(r.flow.storageFailed, true);
	assert.equal(r.flow.drawing.vertices.length, 2);
	assert.equal(r.flow.drawing.fields.pitch, "12,,invalid");
	assert.equal((await r.records())[0].body, body(one));
	await act(async () => r.flow.retry());
	await until(() => !r.flow.checking);
	assert.equal(r.flow.storageFailed, false);
	assert.equal((await r.records())[0].body, body(newer));
	assert.deepEqual(writes, [
		{ previous: null, next: zero },
		{ previous: zero, next: body(one) },
		{ previous: zero, next: body(one) },
		{ previous: zero, next: body(one) },
		{ previous: body(one), next: body(newer) },
	]);
});
test("a pre-mutation refusal permits correction without retrying the refused bytes", async (t) => {
	const r = await rig(t);
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	const initial = (await r.records())[0].body;
	await act(async () =>
		r.flow
			.update({
				...r.flow.drawing,
				fields: { ...r.flow.drawing.fields, source: "x".repeat(4097) },
			})
			.catch(() => undefined),
	);
	assert.equal(r.flow.storageFailed, true);
	assert.equal((await r.records())[0].body, initial);
	await act(async () =>
		r.flow.update({
			...r.flow.drawing,
			fields: { ...r.flow.drawing.fields, source: "corrected source" },
		}),
	);
	assert.equal(r.flow.storageFailed, false);
	assert.equal(
		(await r.records())[0].drawing.fields.source,
		"corrected source",
	);
});
test("explicit discard confirms an uncertain write before deleting its exact owned copy", async (t) => {
	let lose = true;
	const r = await rig(t, (store) => ({
		list: (...args) => store.list(...args),
		clear: (...args) => store.clear(...args),
		write: async (...args) => {
			await store.write(...args);
			if (JSON.parse(args[2]).vertices.length === 1 && lose) {
				lose = false;
				throw new Error("unknown local acknowledgement");
			}
		},
	}));
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	await act(async () =>
		r.flow
			.update(appendMapRoofVertex(r.flow.drawing, [6.96, 50.94]))
			.catch(() => undefined),
	);
	assert.equal(r.flow.storageFailed, true);
	assert.equal((await r.records())[0].drawing.vertices.length, 1);
	await act(async () => r.flow.discard());
	await until(() => !r.flow.checking);
	assert.equal(r.flow.drawing, null);
	assert.equal(r.flow.storageFailed, false);
	assert.equal(r.flow.writing, false);
	assert.equal((await r.records()).length, 0);
});
test("prepared geometry survives local application and clears only after an exact confirmed server geometry", async (t) => {
	const r = await rig(t);
	await act(async () => r.flow.begin({ kind: "new_roof" }));
	await until(() => !r.flow.writing);
	let draft = r.flow.drawing;
	for (const point of [
		[6.96, 50.94],
		[6.9601, 50.94],
		[6.9601, 50.9401],
	])
		draft = appendMapRoofVertex(draft, point);
	draft = {
		...draft,
		phase: "staged",
		fields: {
			...draft.fields,
			name: "Synthetic prepared roof",
			pitch: "30",
			bearing: "180",
			height: "8",
			source: "synthetic drawing",
			rights: "test permission",
			calibration: "synthetic, not a measurement",
			permission: true,
		},
	};
	const result = applyGeometryCommand(geometry, mapRoofDraftCommand(draft));
	await act(async () => r.flow.update({ ...draft, prepared_geometry: result }));
	await act(async () => r.flow.deactivate());
	await r.render({ geometry: result });
	assert.equal((await r.records()).length, 1);
	await r.render({ confirmedGeometry: geometry });
	await until(() => !r.flow.checking);
	assert.equal((await r.records()).length, 1);
	await r.render({ confirmedGeometry: result });
	await until(() => r.flow.drawing === null && !r.flow.checking);
	assert.equal((await r.records()).length, 0);
});
