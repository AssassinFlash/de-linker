import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { MapDrawingController } from "../src/data/MapDrawingController.ts";
import { MapPickGate } from "../src/data/MapPickGate.ts";
import imported from "../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import {
	bindMapRing,
	editMapVertex,
	mapRingCommand,
} from "../src/domain/mapDrawingGeometry.ts";
import { applyGeometryCommand } from "../src/domain/geometryCommands.ts";
import {
	beginDraft,
	editDraft,
	undoDraft,
	redoDraft,
} from "../src/domain/draft.ts";

// Real pinned Terra Draw modes/store; callback adapter and JSDOM do not establish
// WebGL, provider, native event synthesis or physical touch-device acceptance.
function fixture(t, start = { kind: "draw" }, options = {}) {
	const dom = new JSDOM("<!doctype html><canvas></canvas>", {
			pretendToBeVisual: true,
		}),
		canvas = dom.window.document.querySelector("canvas"),
		transactions = [],
		raw = [],
		failures = [],
		gate = new MapPickGate();
	const pixelScale = options.scale ?? 1e5;
	let callbacks,
		interrupted = 0,
		unregisters = 0;
	function toggle(initial) {
		let enabled = initial;
		return {
			isEnabled: () => enabled,
			enable() {
				enabled = true;
			},
			disable() {
				enabled = false;
			},
		};
	}
	const map = {
			getCanvas: () => canvas,
			dragPan: toggle(true),
			dragRotate: toggle(false),
			doubleClickZoom: toggle(true),
		},
		adapter = {
			project: (lng, lat) => ({ x: lng * pixelScale, y: -lat * pixelScale }),
			unproject: (x, y) => ({ lng: x / pixelScale, lat: -y / pixelScale }),
			getCoordinatePrecision: () => 9,
			setCursor(value) {
				canvas.style.cursor = value;
			},
			setDoubleClickToZoom(value) {
				if (value) map.doubleClickZoom.enable();
				else map.doubleClickZoom.disable();
			},
			getMapEventElement: () => canvas,
			getLngLatFromEvent: (event) =>
				options.endpoint
					? {
							lng: event.clientX / pixelScale,
							lat: -event.clientY / pixelScale,
						}
					: null,
			register(value) {
				callbacks = value;
				value.onReady?.();
			},
			render() {},
			clear() {
				callbacks?.onClear();
			},
			unregister() {
				unregisters++;
				this.clear();
				if (options.stopFailure)
					throw new Error("synthetic_adapter_cleanup_refusal");
			},
		};
	canvas.style.cursor = "crosshair";
	canvas.addEventListener("pointerdown", gate.beginPointer, true);
	const controller = new MapDrawingController(map, adapter, start, {
		raw(value) {
			raw.push(value);
		},
		transaction(value) {
			transactions.push(value);
			options.transaction?.(value);
		},
		interrupted() {
			interrupted++;
		},
		failed(error) {
			failures.push(error);
		},
		blockMapPick: gate.block,
	});
	t.after(() => {
		controller.dispose();
		dom.window.close();
	});
	const event = (x, y, extra = {}) => ({
		lng: x / pixelScale,
		lat: -y / pixelScale,
		containerX: x,
		containerY: y,
		button: "left",
		heldKeys: [],
		isContextMenu: false,
		...extra,
	});
	function pointer(type, target = canvas, extra = {}) {
		const value = new dom.window.Event(type, { bubbles: true });
		Object.assign(value, { pointerId: 1, isPrimary: true, ...extra });
		target.dispatchEvent(value);
	}
	async function click(x, y) {
		pointer("pointerdown");
		callbacks.onMouseMove(event(x, y));
		callbacks.onClick(event(x, y));
		pointer("pointerup");
		await Promise.resolve();
	}
	return {
		controller,
		map,
		raw,
		transactions,
		failures,
		gate,
		callbacks,
		canvas,
		dom,
		event,
		pointer,
		click,
		get interrupted() {
			return interrupted;
		},
		get unregisters() {
			return unregisters;
		},
	};
}

test("raw polygon previews never become completed transactions and the toolbar uses only committed points", async (t) => {
	const f = fixture(t);
	await f.click(0, 0);
	assert.equal(f.controller.finishCandidate(), false);
	await f.click(200, 0);
	assert.equal(f.controller.finishCandidate(), false);
	await f.click(200, 200);
	f.callbacks.onMouseMove(f.event(500, 500)); // Provisional point must not enter polygon.
	assert.equal(f.failures.length, 0);
	assert.equal(f.transactions.length, 0);
	assert.equal(f.raw.at(-1).committed_coordinate_count, 3);
	assert.equal(f.controller.finishCandidate(), true);
	await Promise.resolve();
	assert.equal(f.transactions.length, 1);
	assert.equal(f.transactions[0].steps.length, 1);
	assert.equal(f.transactions[0].steps[0].action, "draw");
	assert.deepEqual(f.transactions[0].steps[0].geometry.coordinates, [
		[
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
			[0, 0],
		],
	]);
	assert.equal(f.raw.at(-1).complete, true);
	assert.equal(f.failures.length, 0);
});

test("click closure uses the library's actual winding; completion click stays blocked after disposal", async (t) => {
	const f = fixture(t);
	for (const [x, y] of [
		[0, 0],
		[200, 0],
		[200, 200],
		[0, 0],
	])
		await f.click(x, y);
	assert.equal(f.transactions.length, 1);
	assert.deepEqual(f.transactions[0].steps[0].geometry.coordinates, [
		[
			[0, 0],
			[0.002, -0.002],
			[0.002, 0],
			[0, 0],
		],
	]);
	assert.ok(f.raw.length > 3);
	f.controller.dispose();
	assert.equal(f.gate.blocked, true);
	f.pointer("pointerdown");
	assert.equal(
		f.gate.blocked,
		false,
		"a later physical gesture may pick the map again",
	);
	assert.equal(f.unregisters, 1);
});

test("midpoint insertion and its drag produce one transaction with two immutable snapshots", async (t) => {
	const f = fixture(t, {
		kind: "edit",
		ring: [
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
		],
	});
	assert.equal(
		f.transactions.length,
		0,
		"programmatic projection/selection cannot commit",
	);
	assert.equal(f.raw.length, 0);
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(100, 0));
	f.callbacks.onDragStart(f.event(100, 0), () => {});
	assert.equal(
		f.transactions.length,
		0,
		"insert finish during pointerdown is provisional",
	);
	f.callbacks.onDrag(f.event(100, 30), () => {});
	f.callbacks.onDragEnd(f.event(100, 30), () => {});
	assert.equal(
		f.transactions.length,
		0,
		"wait for the entire pointerup dispatch",
	);
	f.pointer("pointerup");
	await Promise.resolve();
	assert.equal(f.transactions.length, 1);
	const steps = f.transactions[0].steps;
	assert.deepEqual(
		steps.map((step) => step.action),
		["insertMidpoint", "dragCoordinate"],
	);
	assert.notDeepEqual(steps[0].geometry, steps[1].geometry);
	assert.equal(f.failures.length, 0);
});

test("all drag movements including the fifth update the candidate; native Delete cannot erase the feature", async (t) => {
	const f = fixture(t, {
		kind: "edit",
		ring: [
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
		],
	});
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(0, 0));
	f.callbacks.onDragStart(f.event(0, 0), () => {});
	for (let at = 1; at <= 5; at++)
		f.callbacks.onDrag(f.event(-at * 10, 0), () => {});
	f.callbacks.onDragEnd(f.event(-50, 0), () => {});
	f.pointer("pointerup");
	await Promise.resolve();
	assert.equal(f.transactions.length, 1);
	assert.ok(
		f.transactions[0].steps[0].geometry.coordinates[0].some(
			(point) => point[0] === -0.0005,
		),
	);
	const before = f.raw.length;
	f.callbacks.onKeyUp({ key: "Delete", heldKeys: [], preventDefault() {} });
	assert.equal(f.raw.length, before);
	assert.equal(f.interrupted, 0);
	assert.equal(f.failures.length, 0);
});

for (const reason of [
	"cancel",
	"lostcapture",
	"outsideup",
	"blur",
	"hidden",
	"secondary",
	"dispose",
])
	test(`interrupted gesture (${reason}) retains raw input, cancels pending work and restores exact map handler states`, async (t) => {
		const f = fixture(t, {
			kind: "edit",
			ring: [
				[0, 0],
				[0.002, 0],
				[0.002, -0.002],
			],
		});
		f.pointer("pointerdown");
		f.callbacks.onMouseMove(f.event(100, 0));
		f.callbacks.onDragStart(f.event(100, 0), (value) => {
			if (!value) f.map.dragPan.disable();
		});
		f.callbacks.onDrag(f.event(100, 30), () => {});
		f.map.dragPan.disable();
		f.map.dragRotate.disable();
		f.map.doubleClickZoom.disable();
		assert.ok(f.raw.length > 0);
		const savedRaw = JSON.stringify(f.raw.at(-1));
		if (reason === "cancel") f.pointer("pointercancel");
		if (reason === "lostcapture") f.pointer("lostpointercapture");
		if (reason === "outsideup")
			f.pointer("pointerup", f.dom.window.document.body);
		if (reason === "blur")
			f.dom.window.dispatchEvent(new f.dom.window.Event("blur"));
		if (reason === "hidden") {
			Object.defineProperty(f.dom.window.document, "visibilityState", {
				value: "hidden",
			});
			f.dom.window.document.dispatchEvent(
				new f.dom.window.Event("visibilitychange"),
			);
		}
		if (reason === "secondary")
			f.pointer("pointerdown", f.canvas, { pointerId: 2, isPrimary: false });
		if (reason === "dispose") f.controller.dispose();
		await Promise.resolve();
		assert.equal(f.transactions.length, 0);
		assert.equal(JSON.stringify(f.raw.at(-1)), savedRaw);
		assert.equal(f.map.dragPan.isEnabled(), true);
		assert.equal(f.map.dragRotate.isEnabled(), false);
		assert.equal(f.map.doubleClickZoom.isEnabled(), true);
		assert.equal(f.canvas.style.cursor, "crosshair");
		assert.equal(f.unregisters, 1);
		assert.equal(f.interrupted, reason === "dispose" ? 0 : 1);
		assert.equal(f.controller.finishCandidate(), false);
		assert.equal(f.failures.length, 0);
	});

test("disposing after a queued finish invalidates its late transaction callback", async (t) => {
	const f = fixture(t);
	for (const [x, y] of [
		[0, 0],
		[200, 0],
		[200, 200],
	])
		await f.click(x, y);
	assert.equal(f.controller.finishCandidate(), true);
	f.controller.dispose();
	await Promise.resolve();
	assert.equal(f.transactions.length, 0);
	assert.equal(f.unregisters, 1);
});

test("the release endpoint, even without a final move event, replaces only the actually dragged vertex", async (t) => {
	const f = fixture(
		t,
		{
			kind: "edit",
			ring: [
				[0, 0],
				[0.002, 0],
				[0.002, -0.002],
			],
		},
		{ endpoint: true },
	);
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(0, 0));
	f.callbacks.onDragStart(f.event(0, 0), () => {});
	f.callbacks.onDrag(f.event(-50, 0), () => {});
	f.pointer("pointerup", f.canvas, { clientX: -75.1234, clientY: 12.1234 });
	f.callbacks.onDragEnd(f.event(-75.1234, 12.1234), () => {});
	await Promise.resolve();
	assert.equal(f.transactions.length, 1);
	const ring = f.transactions[0].steps[0].geometry.coordinates[0];
	assert.ok(
		ring.some(
			(point) => point[0] === -0.000751234 && point[1] === -0.000121234,
		),
	);
	assert.ok(ring.some((point) => point[0] === 0.002 && point[1] === 0));
	assert.ok(ring.some((point) => point[0] === 0.002 && point[1] === -0.002));
	assert.deepEqual(f.raw.at(-1).geometry, f.transactions[0].steps[0].geometry);
	assert.equal(f.failures.length, 0);
});

test("an unresolved release vertex is refused instead of assigning the cursor to an arbitrary point", async (t) => {
	const f = fixture(
		t,
		{
			kind: "edit",
			ring: [
				[0, 0],
				[0.002, 0],
				[0.002, -0.002],
			],
		},
		{ endpoint: true },
	);
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(0, 0));
	f.callbacks.onDragStart(f.event(0, 0), () => {});
	f.callbacks.onDrag(f.event(0, 0), () => {});
	f.pointer("pointerup", f.canvas, { clientX: -75, clientY: 12 });
	f.callbacks.onDragEnd(f.event(-75, 12), () => {});
	await Promise.resolve();
	assert.equal(f.transactions.length, 0);
	assert.equal(f.failures.length, 1);
	assert.match(f.failures[0].message, /endpoint_unresolved/);
	assert.equal(f.map.dragPan.isEnabled(), true);
	assert.equal(f.unregisters, 1);
});

test("a midpoint release corrects the inserted point and keeps all original display coordinates", async (t) => {
	const ring = [
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
		],
		f = fixture(t, { kind: "edit", ring }, { endpoint: true });
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(100, 0));
	f.callbacks.onDragStart(f.event(100, 0), () => {});
	f.callbacks.onDrag(f.event(100, 30), () => {});
	f.pointer("pointerup", f.canvas, { clientX: 100, clientY: 45 });
	f.callbacks.onDragEnd(f.event(100, 45), () => {});
	await Promise.resolve();
	assert.equal(f.failures.length, 0);
	assert.equal(f.transactions.length, 1);
	assert.deepEqual(
		f.transactions[0].steps.map((step) => step.action),
		["insertMidpoint", "dragCoordinate"],
	);
	const result = f.transactions[0].steps[1].geometry.coordinates[0];
	assert.ok(
		result.some((point) => point[0] === 0.001 && point[1] === -0.00045),
	);
	for (const old of ring)
		assert.ok(
			result.some((point) => point[0] === old[0] && point[1] === old[1]),
		);
	assert.deepEqual(result[0], result.at(-1));
});

test("a release onto another vertex is refused before API backfill or project submission", async (t) => {
	const f = fixture(
		t,
		{
			kind: "edit",
			ring: [
				[0, 0],
				[0.002, 0],
				[0.002, -0.002],
			],
		},
		{ endpoint: true },
	);
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(0, 0));
	f.callbacks.onDragStart(f.event(0, 0), () => {});
	f.callbacks.onDrag(f.event(-50, 0), () => {});
	f.pointer("pointerup", f.canvas, { clientX: 200, clientY: 0 });
	f.callbacks.onDragEnd(f.event(200, 0), () => {});
	await Promise.resolve();
	assert.equal(f.transactions.length, 0);
	assert.equal(f.failures.length, 1);
	assert.match(f.failures[0].message, /identity_ambiguous/);
	assert.ok(
		f.raw.at(-1).geometry.coordinates[0].some((point) => point[0] === -0.0005),
	);
});

test("a midpoint transaction cannot silently drag an unrelated original vertex", async (t) => {
	const f = fixture(t, {
		kind: "edit",
		ring: [
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
		],
	});
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(100, 0));
	f.callbacks.onDragStart(f.event(100, 0), () => {});
	// Exercise a changed library drag target in one active pointer transaction.
	f.callbacks.onMouseMove(f.event(0, 0));
	f.callbacks.onDragStart(f.event(0, 0), () => {});
	f.callbacks.onDrag(f.event(-50, 0), () => {});
	f.callbacks.onDragEnd(f.event(-50, 0), () => {});
	f.pointer("pointerup");
	await Promise.resolve();
	assert.equal(f.transactions.length, 0);
	assert.equal(f.failures.length, 1);
	assert.match(f.failures[0].message, /midpoint_target_changed/);
});

test("real library midpoint callbacks enter one metric project history step and undo/redo retains every source input", async (t) => {
	const document = structuredClone(imported.metadata.geometry_import.geometry),
		inputs = { geometry: document, extra_project_fact: "keep exactly" },
		baseline = {
			id: "1".repeat(32),
			title: "Synthetic controller-domain join",
			revision: 3,
			input_sha256: "a".repeat(64),
			inputs,
		};
	let binding = bindMapRing(document, {
			kind: "roof_hole",
			roof_id: document.roofs[0].id,
			index: 0,
		}),
		draft = beginDraft(baseline);
	const f = fixture(
		t,
		{ kind: "edit", ring: binding.ring.geographic },
		{
			scale: 1e7,
			transaction({ steps }) {
				for (const step of steps)
					binding = editMapVertex(binding, step.geometry, step.action);
				const geometry = applyGeometryCommand(
					document,
					mapRingCommand(binding),
				);
				draft = editDraft(draft, { ...inputs, geometry });
			},
		},
	);
	const a = binding.ring.geographic[0],
		b = binding.ring.geographic[1],
		x = ((a[0] + b[0]) * 1e7) / 2,
		y = (-(a[1] + b[1]) * 1e7) / 2;
	f.pointer("pointerdown");
	f.callbacks.onMouseMove(f.event(x, y));
	f.callbacks.onDragStart(f.event(x, y), () => {});
	f.callbacks.onDrag(f.event(x + 20, y + 20), () => {});
	f.callbacks.onDragEnd(f.event(x + 20, y + 20), () => {});
	f.pointer("pointerup");
	await Promise.resolve();
	assert.equal(f.failures.length, 0);
	assert.equal(f.transactions.length, 1);
	assert.equal(draft.history.past.length, 1);
	const result = draft.history.current.geometry;
	assert.deepEqual(result.roofs[0].boundary_uv, document.roofs[0].boundary_uv);
	assert.equal(
		result.roofs[0].holes_uv[0].length,
		document.roofs[0].holes_uv[0].length + 1,
	);
	for (const point of document.roofs[0].holes_uv[0])
		assert.ok(
			result.roofs[0].holes_uv[0].some(
				(current) => current[0] === point[0] && current[1] === point[1],
			),
		);
	assert.deepEqual(result.sources, document.sources);
	assert.deepEqual(undoDraft(draft).history.current, inputs);
	assert.deepEqual(
		redoDraft(undoDraft(draft)).history.current,
		draft.history.current,
	);
	assert.equal(draft.history.current.extra_project_fact, "keep exactly");
});

for (const terminal of ["interrupt", "failure", "dispose"])
	test(`adapter cleanup refusal still reports one terminal failure and lets the owner finish disposal (${terminal})`, async (t) => {
		const f = fixture(
			t,
			{
				kind: "edit",
				ring: [
					[0, 0],
					[0.002, 0],
					[0.002, -0.002],
				],
			},
			{ stopFailure: true, endpoint: true },
		);
		f.pointer("pointerdown");
		f.callbacks.onMouseMove(f.event(0, 0));
		f.callbacks.onDragStart(f.event(0, 0), () => {});
		f.callbacks.onDrag(f.event(-50, 0), () => {});
		const raw = JSON.stringify(f.raw.at(-1));
		let ownerCleanup = false;
		if (terminal === "interrupt")
			f.dom.window.dispatchEvent(new f.dom.window.Event("blur"));
		if (terminal === "failure")
			f.pointer("pointerup", f.canvas, { clientX: Infinity, clientY: 0 });
		if (terminal === "dispose")
			assert.doesNotThrow(() => f.controller.dispose());
		ownerCleanup = true;
		await Promise.resolve();
		assert.equal(ownerCleanup, true);
		assert.equal(f.transactions.length, 0);
		assert.equal(f.interrupted, 0);
		assert.equal(f.failures.length, 1);
		assert.ok(f.failures[0] instanceof AggregateError);
		assert.match(
			f.failures[0].message,
			terminal === "failure"
				? /map_drawing_failed/
				: /map_drawing_cleanup_failed/,
		);
		assert.ok(JSON.stringify(f.raw.at(-1)) === raw);
		assert.equal(f.map.dragPan.isEnabled(), true);
		assert.equal(f.map.dragRotate.isEnabled(), false);
		assert.equal(f.map.doubleClickZoom.isEnabled(), true);
		assert.equal(f.unregisters, 1);
		assert.doesNotThrow(() => f.controller.dispose());
		assert.equal(f.failures.length, 1, "late cleanup cannot notify twice");
	});

test("one refused handler restore does not skip other handlers or the cursor and is reported", (t) => {
	const f = fixture(t, {
		kind: "edit",
		ring: [
			[0, 0],
			[0.002, 0],
			[0.002, -0.002],
		],
	});
	f.map.dragPan.disable();
	f.map.dragPan.enable = () => {
		throw new Error("synthetic_pan_restore_refusal");
	};
	f.map.dragRotate.enable();
	f.map.doubleClickZoom.disable();
	f.canvas.style.cursor = "move";
	assert.doesNotThrow(() => f.controller.dispose());
	assert.equal(f.map.dragRotate.isEnabled(), false);
	assert.equal(f.map.doubleClickZoom.isEnabled(), true);
	assert.equal(f.canvas.style.cursor, "crosshair");
	assert.equal(f.failures.length, 1);
	assert.match(f.failures[0].message, /cleanup_failed/);
	assert.ok(
		f.failures[0].errors.some(
			(cause) => cause.message === "map_drawing_restore_failed",
		),
	);
});
