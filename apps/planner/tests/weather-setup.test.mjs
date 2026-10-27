import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import {
	beginDraft,
	editDraft,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import fixture from "./fixtures/preparation-flow.json" with { type: "json" };

const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent === text && !node.closest("[hidden]"),
	);
const control = (text) =>
	[...document.querySelectorAll("label")]
		.find((node) => node.querySelector("span")?.textContent.startsWith(text))
		?.querySelector("input,select");
async function click(text) {
	const node = button(text);
	assert.ok(node, "missing " + text);
	assert.equal(node.disabled, false, "disabled " + text);
	await act(async () => node.click());
}
async function choose(text, value) {
	await act(async () => {
		const node = control(text);
		node.value = value;
		node.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}

test("weather controls retain unfinished negative coordinates across views, require explicit preparation/save, then dispatch one frozen native request", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const scope = "a".repeat(64),
		project = {
			...fixture.weather_project,
			revision: 1,
			inputs: {
				geometry: fixture.weather_project.inputs.geometry,
				unrelated: "retained",
			},
		};
	const session = {
		query_scope: scope,
		runtime: {
			models: {},
			limits: {
				max_json_depth: 32,
				max_body_bytes: 16777216,
				max_page_size: 100,
			},
		},
	};
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	let current = beginDraft(project),
		setter,
		serverRun = null;
	const requests = [];
	function edit(operation) {
		try {
			current = editDraft(current, operation(current.history.current));
			setter(current);
			return true;
		} catch {
			return false;
		}
	}
	const client = {
		isCurrentScope: (value) => value === scope,
		async send(path, serialized) {
			const body = JSON.parse(serialized);
			requests.push({ path, body });
			assert.equal(path, "runs/weather");
			serverRun = {
				...fixture.weather_run,
				state: "queued",
				result: null,
				result_sha256: null,
				revision: body.expected_revision,
				manifest: {
					...fixture.weather_run.manifest,
					revision: body.expected_revision,
				},
			};
			return serverRun;
		},
		async query(path) {
			if (path === "projects/runs")
				return {
					items: serverRun
						? [
								{
									id: serverRun.id,
									project_id: project.id,
									revision: serverRun.revision,
									manifest_sha256: serverRun.manifest_sha256,
									result_sha256: null,
									state: "queued",
									is_current: true,
									created_at: 1700000000,
									task_kind: "acquire_pvgis_tmy_weather_v1",
								},
							]
						: [],
					next: null,
				};
			if (path === "runs/read") return serverRun;
			if (path === "runs/weather/status") return fixture.weather_status;
			throw new Error("Unexpected query " + path);
		},
	};
	function Harness() {
		const [draft, setDraft] = useState(current),
			[valid, setValid] = useState(true);
		setter = setDraft;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(
				"button",
				{
					disabled: !valid,
					onClick: () => {
						current = prepareSave(current, crypto.randomUUID(), {
							maxDepth: 32,
							maxBytes: 16777216,
						});
						const intent = current.pending;
						current = acknowledgeSave(current, intent, {
							...project,
							revision: intent.expectedRevision + 1,
							input_sha256: "e".repeat(64),
							inputs: intent.inputs,
						});
						setter(current);
					},
				},
				"Confirm project save fixture",
			),
			React.createElement(EnergyWorkspace, {
				draft,
				edit,
				flush: async () => true,
				session,
				client,
				recheck: () => {},
				locale: "en-GB",
				blocked: false,
				active: true,
				onValidity: setValid,
				openProfiles: () => {},
			}),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(Harness),
			),
		),
	);
	await click("Weather source");
	await until(() => !button("Prepare weather settings").disabled);
	assert.equal(control("Latitude").value, "");
	await click("Prepare weather settings");
	assert.match(
		document.querySelector(".lp-focus-target").textContent,
		/Weather settings need/,
	);
	assert.equal(requests.length, 0);
	const latitude = control("Latitude");
	await enter(latitude, "-");
	assert.equal(latitude.getAttribute("aria-invalid"), "true");
	assert.equal(button("Confirm project save fixture").disabled, true);
	await click("Scenario settings");
	await click("Weather source");
	assert.equal(control("Latitude"), latitude);
	assert.equal(latitude.value, "-");
	await enter(latitude, "-52.52");
	assert.equal(
		current.history.current.solar_setup.weather.request.latitude_deg,
		-52.52,
	);
	await click("Use roof coordinates");
	assert.equal(control("Latitude").value, "52.52");
	assert.equal(control("Longitude").value, "13.405");
	await enter(control("Latitude"), "-");
	await click("Use roof coordinates");
	assert.equal(
		control("Latitude").value,
		"52.52",
		"explicit location replacement clears unfinished text even when the saved number is unchanged",
	);
	assert.equal(control("Latitude").getAttribute("aria-invalid"), "false");
	await enter(control("First source year"), "2005.5");
	assert.equal(
		control("First source year").getAttribute("aria-invalid"),
		"true",
	);
	assert.match(
		control("First source year").closest("label").textContent,
		/whole number between/,
	);
	assert.equal(button("Confirm project save fixture").disabled, true);
	assert.equal(requests.length, 0);
	await enter(control("First source year"), "2005");
	await enter(control("Last source year"), "2023");
	await choose("Expected radiation database", "PVGIS-SARAH3");
	await choose("Terrain horizon", "false");
	await enter(control("Synthetic calculation year"), "2024");
	await click("Prepare weather settings");
	assert.match(
		document.querySelector(".lp-focus-target").textContent,
		/non-leap year/,
	);
	assert.equal(requests.length, 0);
	await enter(control("Synthetic calculation year"), "2023");
	await click("Prepare weather settings");
	assert.deepEqual(
		current.history.current.weather_acquisition,
		fixture.weather_project.inputs.weather_acquisition,
	);
	assert.equal(current.history.current.unrelated, "retained");
	assert.equal(button("Request weather for saved inputs").disabled, true);
	await click("Confirm project save fixture");
	await until(() => !button("Request weather for saved inputs").disabled);
	await act(async () => {
		button("Request weather for saved inputs").click();
		button("Request weather for saved inputs")?.click();
	});
	await until(
		() =>
			requests.length === 1 &&
			button("Saved calculations").getAttribute("aria-pressed") === "true",
	);
	assert.equal(requests[0].path, "runs/weather");
	assert.equal(requests[0].body.expected_revision, 2);
	assert.deepEqual(Object.keys(requests[0].body).sort(), [
		"expected_revision",
		"key",
		"project_id",
		"schema_version",
	]);
	assert.equal(requests[0].body.project_id, project.id);
	await click("Weather source");
	await enter(control("Last source year"), "2022");
	assert.equal(
		current.history.current.weather_acquisition,
		undefined,
		"edited weather choices cannot reuse compiled settings",
	);
	assert.equal(button("Request weather for saved inputs").disabled, true);
	assert.equal(
		requests.length,
		1,
		"editing and preparation never start an Actor",
	);
});
