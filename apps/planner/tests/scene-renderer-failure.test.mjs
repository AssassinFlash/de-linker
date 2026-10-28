import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, until } from "./dom-fixture.mjs";
register("./scene-renderer-loader.mjs", import.meta.url);

test("null WebGL context leaves 3D unavailable, and retry repeats initialization without a stale loading indicator", async (t) => {
	const fixture = setupDom();
	const originalStyle = Object.getOwnPropertyDescriptor(
		globalThis,
		"getComputedStyle",
	);
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	const { createRoot } = await import("react-dom/client");
	const { default: SceneViewport } =
		await import("../src/components/design/SceneViewport.tsx");
	const { failures } = await import("./scene-renderer-fixture.mjs");
	const { renderers, behavior } = await import("./scene-renderer-three.mjs");
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		if (originalStyle)
			Object.defineProperty(globalThis, "getComputedStyle", originalStyle);
		else delete globalThis.getComputedStyle;
	});
	const before = JSON.stringify(flat);
	await act(async () =>
		root.render(
			React.createElement(SceneViewport, {
				document: flat,
				poses: [],
				selected: null,
				select() {},
				commit() {
					return false;
				},
				disabled: true,
			}),
		),
	);
	const button = (label) =>
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent.trim() === label,
		);
	await until(() => button("Retry 3D"));
	assert.match(failures[0].message, /getSupportedExtensions/);
	assert.match(fixture.element.textContent, /3D rendering is unavailable/);
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Fit 3D view"), undefined);
	assert.equal(renderers[0].initialDisposed, true);
	assert.equal(renderers[0].fallbackDisposed, true);
	assert.equal(renderers[0].disposed, true);
	behavior.mode = "ready";
	await act(async () => button("Retry 3D").click());
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.equal(button("Fit 3D view").disabled, false);
	await act(async () => renderers[0].onDeviceLost());
	assert.ok(document.querySelector('[data-renderer="WebGL 2"]'));
	await act(async () => renderers.at(-1).onDeviceLost());
	assert.ok(button("Retry 3D"));
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Fit 3D view"), undefined);
	behavior.mode = "fail";
	await act(async () => button("Retry 3D").click());
	await until(() => failures.length >= 2 && button("Retry 3D"));
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(JSON.stringify(flat), before);
});
