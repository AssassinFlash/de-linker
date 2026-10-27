import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import imported from "../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import { setupDom, until } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

const activeMap = (maps) => maps.findLast((map) => !map.removed);
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim() === text,
	);

test("map view keeps metric inputs unchanged and gates/cancels each external owner across CMP and identity hiding", async (t) => {
	const fixture = setupDom();
	const previous = new globalThis.Map();
	for (const name of ["MutationObserver", "getComputedStyle"]) {
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value: window[name].bind(window),
			configurable: true,
		});
	}
	const css = document.createElement("style");
	css.textContent =
		".lp-map-host{--proto-neutral-300:#ccc;--proto-teal-900:#123;--proto-neutral-600:#456;--proto-teal-700:#278;--proto-teal-400:#4bc;--proto-neutral-100:#eee;}";
	document.head.append(css);
	const { createRoot } = await import("react-dom/client");
	const { default: MapViewport } =
		await import("../src/components/design/MapViewport.tsx");
	const { maps, behavior } = await import("./map-library-fixture.mjs");
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	const geometry = structuredClone(imported.metadata.geometry_import.geometry),
		before = JSON.stringify(geometry),
		camera = { current: null },
		picked = [];
	const props = {
		document: geometry,
		poses: [],
		selected: null,
		select: (id) => picked.push(id),
		disabled: false,
		openReferences() {},
		camera,
	};
	const render = async () =>
		act(async () =>
			root.render(
				React.createElement(
					React.StrictMode,
					null,
					React.createElement(MapViewport, props),
				),
			),
		);
	await render();
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.ok(maps.length >= 2, "StrictMode should release the first setup");
	assert.equal(maps[0].removals, 1);
	assert.equal(typeof activeMap(maps).options.style, "object");
	assert.deepEqual(activeMap(maps).options.style.sources, {});
	assert.ok(
		activeMap(maps).fitted,
		"the first ready view must fit the actual geometry",
	);
	assert.equal(
		activeMap(maps).getSource("linker-project-geometry").data.features[0]
			.geometry.coordinates.length,
		2,
	);
	activeMap(maps).hits = [{ properties: { object_id: geometry.roofs[0].id } }];
	await act(async () =>
		activeMap(maps).emit("click", { point: { x: 1, y: 1 } }),
	);
	assert.deepEqual(picked, [geometry.roofs[0].id]);
	await act(async () => button("Load street map").click());
	await until(() => typeof activeMap(maps)?.options.style === "string");
	const hiddenByButton = activeMap(maps);
	await act(async () => {
		button("Hide street map").click();
		assert.equal(hiddenByButton.removals, 1);
	});
	await until(() => typeof activeMap(maps)?.options.style === "object");
	await act(async () => button("Load street map").click());
	await until(() => typeof activeMap(maps)?.options.style === "string");
	const external = activeMap(maps);
	assert.equal(
		external.options.style,
		"https://tiles.openfreemap.org/styles/liberty",
	);
	await act(async () => {
		document.dispatchEvent(
			new window.CustomEvent("wp_listen_for_consent_change", {
				detail: { statistics: "deny" },
			}),
		);
		assert.equal(
			external.removals,
			1,
			"withdrawal must synchronously release the current owner",
		);
	});
	await until(() => typeof activeMap(maps)?.options.style === "object");
	assert.ok(button("Load street map"));
	await act(async () => button("Load street map").click());
	await until(() => typeof activeMap(maps)?.options.style === "string");
	const hiddenOwner = activeMap(maps);
	await act(async () => fixture.element.setAttribute("hidden", ""));
	await until(() => hiddenOwner.removed);
	await act(async () => fixture.element.removeAttribute("hidden"));
	assert.equal(typeof activeMap(maps).options.style, "object");
	behavior.autoLoad = false;
	await act(async () => button("Load street map").click());
	const unavailable = activeMap(maps);
	await act(async () =>
		unavailable.emit("error", { error: new Error("synthetic offline") }),
	);
	assert.equal(
		document.querySelector(".lp-map-view").dataset.mapStatus,
		"failed",
	);
	assert.equal(
		document.querySelector('.lp-map-view [role="status"]'),
		null,
		"a terminal provider refusal must not keep announcing loading",
	);
	assert.equal(
		JSON.parse(document.querySelector(".lp-map-view").dataset.mapFailure).stage,
		"resource",
	);
	behavior.autoLoad = true;
	await act(async () => button("Retry loading map").click());
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.equal(unavailable.removals, 1);
	await act(async () => button("Hide street map").click());
	await until(() => typeof activeMap(maps)?.options.style === "object");
	activeMap(maps).jumpTo({
		center: [6.9601, 50.9401],
		zoom: 19,
		bearing: 35,
		pitch: 10,
	});
	await act(async () =>
		root.render(React.createElement("p", null, "Other editor view")),
	);
	assert.equal(activeMap(maps), undefined);
	await render();
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.deepEqual(activeMap(maps).options.center, [6.9601, 50.9401]);
	assert.equal(activeMap(maps).options.bearing, 35);
	assert.equal(
		typeof activeMap(maps).options.style,
		"object",
		"view changes do not retain an external grant",
	);
	assert.equal(JSON.stringify(geometry), before);
	assert.ok(
		maps.filter((map) => map.removed).every((map) => map.removals === 1),
	);
});
