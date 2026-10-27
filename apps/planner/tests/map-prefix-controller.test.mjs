import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { MapPrefixController } from "../src/data/MapPrefixController.ts";
import { MapPickGate } from "../src/data/MapPickGate.ts";

function rig(t, { cleanupFailure = false } = {}) {
	const dom = new JSDOM("<!doctype html><canvas></canvas>"),
		canvas = dom.window.document.querySelector("canvas"),
		listeners = new Map(),
		sources = new Map(),
		layers = new Map(),
		points = [],
		failures = [],
		gate = new MapPickGate();
	let enabled = true;
	const map = {
		getCanvas: () => canvas,
		doubleClickZoom: {
			isEnabled: () => enabled,
			enable: () => {
				enabled = true;
			},
			disable: () => {
				enabled = false;
			},
		},
		on: (name, fn) => listeners.set(name, fn),
		off: (name, fn) => {
			if (listeners.get(name) === fn) listeners.delete(name);
		},
		addSource: (id, spec) =>
			sources.set(id, {
				data: spec.data,
				setData(data) {
					this.data = data;
				},
			}),
		getSource: (id) => sources.get(id),
		removeSource: (id) => sources.delete(id),
		addLayer: (layer) => layers.set(layer.id, layer),
		getLayer: (id) => layers.get(id),
		removeLayer: (id) => {
			if (cleanupFailure) {
				cleanupFailure = false;
				throw new Error("injected remove layer failure");
			}
			layers.delete(id);
		},
	};
	const begin = () => gate.beginPointer();
	dom.window.addEventListener("pointerdown", begin, true);
	const controller = new MapPrefixController(map, [[6.96, 50.94]], "#0a665c", {
		append: (point) => points.push(point),
		blockMapPick: () => gate.block(),
		failed: (cause) => failures.push(cause),
	});
	function pointer(type, options = {}) {
		const event = new dom.window.Event(type, { bubbles: true });
		Object.assign(event, {
			pointerId: 1,
			button: 0,
			isPrimary: true,
			clientX: 10,
			clientY: 20,
			...options,
		});
		canvas.dispatchEvent(event);
	}
	function click(detail = 1) {
		listeners.get("click")?.({
			originalEvent: { detail },
			lngLat: { lng: 6.961, lat: 50.941 },
		});
	}
	t.after(() => {
		controller.dispose();
		dom.window.close();
	});
	return {
		controller,
		map,
		pointer,
		click,
		points,
		sources,
		layers,
		failures,
		gate,
		get enabled() {
			return enabled;
		},
		window: dom.window,
	};
}
test("a restored open prefix uses Point/LineString without an artificial polygon and admits one real new gesture", (t) => {
	const r = rig(t),
		data = () => [...r.sources.values()][0].data;
	assert.deepEqual(
		data().features.map((f) => f.geometry.type),
		["Point"],
	);
	r.controller.update([
		[6.96, 50.94],
		[6.9601, 50.94],
	]);
	assert.deepEqual(
		data().features.map((f) => f.geometry.type),
		["LineString", "Point", "Point"],
	);
	r.click();
	assert.deepEqual(r.points, []);
	r.pointer("pointerdown");
	assert.equal(r.gate.blocked, true);
	r.pointer("pointerup");
	r.click();
	r.click();
	assert.deepEqual(r.points, [[6.961, 50.941]]);
});
test("pan, cancelled input, multi-pointer pinch, secondary button and double click cannot add corners", (t) => {
	const r = rig(t);
	r.pointer("pointerdown");
	r.pointer("pointermove", { clientX: 14 });
	r.pointer("pointerup", { clientX: 14 });
	r.click();
	r.pointer("pointerdown");
	r.pointer("pointercancel");
	r.pointer("pointerup");
	r.click();
	r.pointer("pointerdown");
	r.pointer("pointerdown", { pointerId: 2, isPrimary: false });
	r.pointer("pointerup", { pointerId: 2, isPrimary: false });
	r.pointer("pointerup");
	r.click();
	r.pointer("pointerdown", { button: 2 });
	r.pointer("pointerup", { button: 2 });
	r.click();
	r.pointer("pointerdown");
	r.pointer("pointerup");
	r.click(2);
	assert.deepEqual(r.points, []);
});
test("blur/lost capture interrupt collection and disposal removes overlays and restores map handlers", (t) => {
	const r = rig(t);
	assert.equal(r.enabled, false);
	r.pointer("pointerdown");
	r.window.dispatchEvent(new r.window.Event("blur"));
	r.pointer("pointerup");
	r.click();
	r.pointer("pointerdown");
	r.pointer("lostpointercapture");
	r.pointer("pointerup");
	r.click();
	assert.deepEqual(r.points, []);
	r.controller.dispose();
	assert.equal(r.layers.size, 0);
	assert.equal(r.sources.size, 0);
	assert.equal(r.enabled, true);
	r.pointer("pointerdown");
	r.pointer("pointerup");
	r.click();
	assert.deepEqual(r.points, []);
});
test("a cleanup failure is reported once while other resources and camera handlers still release", (t) => {
	const r = rig(t, { cleanupFailure: true });
	assert.doesNotThrow(() => r.controller.dispose());
	assert.equal(r.failures.length, 1);
	assert.equal(r.enabled, true);
	assert.equal(r.sources.size, 0);
	r.controller.dispose();
	assert.equal(r.failures.length, 1);
});
