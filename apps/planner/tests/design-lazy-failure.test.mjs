import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, enter, until } from "./dom-fixture.mjs";
register("./scene-failure-loader.mjs", import.meta.url);

test("3D and map chunk failures and retries preserve unapplied raw properties and the plan path", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { DesignEditor } =
		await import("../src/components/design/DesignEditor.tsx");
	const caught = [];
	const root = createRoot(fixture.element, {
		onCaughtError: (error) => caught.push(error),
	});
	t.after(() => fixture.dispose(root));
	const button = (text) =>
		[...document.querySelectorAll("button")].find(
			(button) => button.textContent.trim() === text,
		);
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(DesignEditor, {
					sceneModuleUrl: new URL(
						"../src/components/design/SceneViewport.tsx",
						import.meta.url,
					).href,
					mapModuleUrl: new URL(
						"../src/components/design/MapViewport.tsx",
						import.meta.url,
					).href,
					geometry: flat,
					commit() {
						throw new Error("No edit expected");
					},
					locale: "en-GB",
					projectId: "1".repeat(32),
					session: { query_scope: "2".repeat(64) },
					client: { isCurrentScope: () => true },
					recheck() {},
					onValidity() {},
				}),
			),
		),
	);
	await act(async () => button(flat.arrays[0].name).click());
	await act(async () => button("Edit numeric properties").click());
	await enter(document.querySelector('[name="rows"]'), "2.5");
	await act(async () => button("3D").click());
	await until(() => button("Retry loading 3D"));
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
	assert.ok(button("Plan"));
	await act(async () => button("Retry loading 3D").click());
	await until(() => caught.length >= 2);
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
	await act(async () => button("Plan").click());
	assert.ok(document.querySelector(".lp-plan-svg"));
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
	assert.ok(
		caught.every((error) => error.message === "synthetic_3d_chunk_unavailable"),
	);
	assert.equal(new URL(caught[0].moduleUrl).search, "");
	assert.equal(
		new URL(caught[1].moduleUrl).searchParams.get("planner_retry"),
		"1",
	);
	await act(async () => button("Map").click());
	await until(() => button("Retry loading map"));
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
	await act(async () => button("Retry loading map").click());
	await until(() => caught.length >= 4);
	assert.ok(
		caught
			.slice(2)
			.every((error) => error.message === "synthetic_map_chunk_unavailable"),
	);
	assert.equal(
		new URL(caught[3].moduleUrl).searchParams.get("planner_retry"),
		"1",
	);
	await act(async () => button("Plan").click());
	assert.ok(document.querySelector(".lp-plan-svg"));
	assert.equal(document.querySelector('[name="rows"]').value, "2.5");
});
