import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";
import { loadGoogleMaps } from "../src/data/googleMaps.ts";
import { Google3DMap } from "../src/components/design/Google3DMap.tsx";

const script = () =>
	document.querySelector('script[data-linker-google-maps="1"]');
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim() === text,
	);

test("a failed Google script can be retried with a fresh request", async (t) => {
	const dom = setupDom();
	t.after(() => dom.dispose({ unmount() {} }));
	const first = loadGoogleMaps("test-key");
	const failedScript = script();
	const rejected = assert.rejects(first, /google_maps_load_error/);
	failedScript.dispatchEvent(new window.Event("error"));
	await rejected;
	assert.equal(failedScript.isConnected, false);
	const retry = loadGoogleMaps("test-key");
	const nextScript = script();
	assert.notEqual(nextScript, failedScript);
	const maps = { importLibrary: async () => ({}) };
	window.google = { maps };
	nextScript.dispatchEvent(new window.Event("load"));
	assert.equal(await retry, maps);
});

test("3D retry remounts the provider after failure while the aerial-map exit stays available", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	let attempts = 0;
	const made = [];
	class MapElement extends window.HTMLElement {
		constructor() {
			super();
			made.push(this);
		}
	}
	class MarkerElement extends window.HTMLElement {}
	window.customElements.define("test-google-map", MapElement);
	window.customElements.define("test-google-marker", MarkerElement);
	window.google = {
		maps: {
			async importLibrary() {
				if (++attempts === 1)
					throw new Error("provider temporarily unavailable");
				return { Map3DElement: MapElement, Marker3DElement: MarkerElement };
			},
		},
	};
	let openedMap = 0;
	await act(async () =>
		root.render(
			React.createElement(Google3DMap, {
				apiKey: "test-key",
				center: [6.96, 50.94],
				onSwitchToMap() {
					openedMap++;
				},
			}),
		),
	);
	await until(() => button("Retry 3D"));
	await act(async () => button("Open aerial map").click());
	assert.equal(openedMap, 1);
	await act(async () => button("Retry 3D").click());
	await until(() => made.length === 1);
	assert.equal(attempts, 2);
	assert.equal(made[0].isConnected, true);
	assert.equal(
		document.querySelector('[data-google3d-status="ready"]') !== null,
		true,
	);
});
