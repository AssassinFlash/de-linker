import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, until } from "./dom-fixture.mjs";

/** The session's lazy boundary mounts a fresh module per fixture, so each case
 * registers the substitution inside its own scope rather than at file scope. */
async function scene(behavior) {
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
	const { renderers, behavior: mode } =
		await import("./scene-renderer-three.mjs");
	mode.mode = behavior;
	const root = createRoot(fixture.element);
	const button = (label) =>
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent.trim() === label,
		);
	const render = () =>
		act(async () =>
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
	const dispose = async () => {
		await fixture.dispose(root);
		if (originalStyle)
			Object.defineProperty(globalThis, "getComputedStyle", originalStyle);
		else delete globalThis.getComputedStyle;
	};
	return { fixture, failures, renderers, render, dispose, button, mode };
}

test("null WebGL context leaves 3D unavailable, and retry repeats initialization without a stale loading indicator", async (t) => {
	// A failed module request must still reach the renderer factory: the lazy
	// module itself resolves here, so only the GPU initialisation can fail.
	const { register } = await import("node:module");
	register("./scene-renderer-loader.mjs", import.meta.url);
	const scene3d = await scene("fail");
	const { fixture, failures, renderers, render, dispose, button, mode } =
		scene3d;
	t.after(dispose);
	const before = JSON.stringify(flat);
	await render();
	await until(() => button("Retry 3D"));
	assert.match(failures[0].message, /getSupportedExtensions/);
	assert.match(fixture.element.textContent, /3D rendering is unavailable/);
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Fit 3D view"), undefined);
	assert.equal(renderers[0].initialDisposed, true);
	assert.equal(renderers[0].fallbackDisposed, true);
	assert.equal(renderers[0].disposed, true);
	mode.mode = "ready";
	await act(async () => button("Retry 3D").click());
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.equal(button("Fit 3D view").disabled, false);
	await act(async () => renderers[0].onDeviceLost());
	assert.ok(document.querySelector('[data-renderer="WebGL 2"]'));
	await act(async () => renderers.at(-1).onDeviceLost());
	assert.ok(button("Retry 3D"));
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Fit 3D view"), undefined);
	mode.mode = "fail";
	await act(async () => button("Retry 3D").click());
	await until(() => failures.length >= 2 && button("Retry 3D"));
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(JSON.stringify(flat), before);
});

test("a wedged initialisation becomes a retryable failure instead of permanent progress", async (t) => {
	const { register } = await import("node:module");
	register("./scene-renderer-loader.mjs", import.meta.url);
	t.mock.timers.enable({ apis: ["setTimeout"] });
	const scene3d = await scene("hang");
	const { fixture, renderers, render, dispose, button, mode } = scene3d;
	t.after(dispose);
	await render();
	// The renderer factory owns a device while init is outstanding.
	assert.match(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Retry 3D"), undefined);
	await act(async () => {
		t.mock.timers.tick(15_000);
	});
	// `until` polls with real timers, so the fake clock must stop first.
	t.mock.timers.reset();
	await until(() => button("Retry 3D"));
	assert.match(fixture.element.textContent, /3D rendering is unavailable/);
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	assert.equal(button("Fit 3D view"), undefined);
	// The abandoned instance never reached the React tree, so this factory
	// released both attempted backends and the renderer itself.
	assert.equal(renderers[0].initialDisposed, true);
	assert.equal(renderers[0].fallbackDisposed, true);
	assert.equal(renderers[0].disposed, true);
	// An explicit retry after the device recovers renders again.
	mode.mode = "ready";
	await act(async () => button("Retry 3D").click());
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.equal(button("Fit 3D view").disabled, false);
});

test("a hidden workspace section releases the 3D surface instead of keeping it resident", async (t) => {
	const { register } = await import("node:module");
	register("./scene-renderer-loader.mjs", import.meta.url);
	const scene3d = await scene("ready");
	const { fixture, render, dispose, button } = scene3d;
	t.after(dispose);
	await render();
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.ok(fixture.element.querySelector("[data-test-canvas]"));
	assert.equal(button("Fit 3D view").disabled, false);
	// The planner hides inactive workspaces with the native attribute and keeps
	// them mounted; the GPU surface must not stay resident behind them.
	fixture.element.setAttribute("hidden", "");
	await until(() => !fixture.element.querySelector("[data-test-canvas]"));
	assert.equal(button("Fit 3D view"), undefined);
	assert.doesNotMatch(fixture.element.textContent, /Preparing 3D/);
	fixture.element.removeAttribute("hidden");
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.equal(button("Fit 3D view").disabled, false);
});
