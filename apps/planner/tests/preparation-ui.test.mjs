import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred } from "./dom-fixture.mjs";
import { PreparationResult } from "../src/components/energy/PreparationResult.tsx";
import { WeatherProgress } from "../src/components/energy/WeatherProgress.tsx";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import { beginDraft } from "../src/domain/draft.ts";
import { ApiError } from "../src/data/protocol.ts";
import fixture from "./fixtures/preparation-flow.json" with { type: "json" };

const scope = "a".repeat(64);
const session = {
	query_scope: scope,
	runtime: {
		limits: {
			max_json_depth: 32,
			max_body_bytes: 16777216,
			max_page_size: 100,
		},
	},
};
const selectButton = () =>
	document.querySelector(".lp-run-result > .lp-button");

async function mount(t, component) {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	window.requestAnimationFrame = (callback) => window.setTimeout(callback, 0);
	window.cancelAnimationFrame = (frame) => window.clearTimeout(frame);
	window.HTMLElement.prototype.scrollIntoView = function () {};
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
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
				component,
			),
		),
	);
	return { dom, root, queryClient };
}

async function sourceRig(t, kind, options = {}) {
	const run = structuredClone(fixture[`${kind}_run`]);
	const project = structuredClone(fixture[`${kind}_project`]);
	let inputs = structuredClone(project.inputs),
		setter,
		currentScope = true,
		edits = 0,
		rechecks = 0;
	const calls = [],
		client = {
			isCurrentScope: (value) => currentScope && value === scope,
			async query(path, body) {
				calls.push({ path, body });
				if (options.gate && path === "assets/read") await options.gate.promise;
				if (options.failure && path === "assets/read") throw options.failure;
				if (path === "projects/read") {
					assert.equal(body.revision, run.revision);
					return project;
				}
				if (path === "assets/read")
					return kind === "pv" &&
						body.asset_id === fixture.weather_run.result.prepared_asset.id
						? fixture.weather_run.result.prepared_asset
						: (options.asset ?? run.result.prepared_asset);
				if (path === "runs/weather/status") return fixture.weather_status;
				throw new Error("unexpected query " + path);
			},
			send() {
				throw new Error(
					"result reading and selection must not start another task",
				);
			},
		};
	function Harness() {
		const [value, setValue] = useState(inputs);
		setter = setValue;
		return React.createElement(PreparationResult, {
			run,
			inputs: value,
			session,
			client,
			recheck: () => rechecks++,
			locale: "en-GB",
			active: true,
			blocked: false,
			edit(operation) {
				const next = operation(inputs);
				inputs = next;
				edits++;
				setValue(next);
				return true;
			},
		});
	}
	await mount(t, React.createElement(Harness));
	return {
		run,
		project,
		calls,
		get inputs() {
			return inputs;
		},
		get edits() {
			return edits;
		},
		get rechecks() {
			return rechecks;
		},
		dropScope() {
			currentScope = false;
		},
		async change(operation, render = true) {
			inputs = operation(inputs);
			if (render) await act(async () => setter(inputs));
		},
	};
}

for (const kind of ["weather", "pv"]) {
	test(`${kind} source is selected only by an explicit action and preserves edits made while provenance is loading`, async (t) => {
		const gate = deferred(),
			rig = await sourceRig(t, kind, { gate });
		assert.equal(rig.edits, 0);
		await rig.change((current) => ({
			...current,
			customer_note: "A later unrelated edit",
		}));
		await act(async () => gate.resolve());
		await until(() => selectButton() && !selectButton().disabled);
		assert.match(document.body.textContent, /PVGIS-SARAH3/);
		assert.match(document.body.textContent, /ERA5/);
		assert.equal(
			rig.edits,
			0,
			"loading a valid result never selects it automatically",
		);
		await act(async () => selectButton().click());
		assert.equal(rig.edits, 1);
		assert.equal(rig.inputs.customer_note, "A later unrelated edit");
		if (kind === "weather")
			assert.equal(
				rig.inputs.pv_preparation.weather_asset_id,
				rig.run.result.prepared_asset.id,
			);
		else
			assert.equal(
				rig.inputs.profile_selections.selected.pv_available_ac,
				rig.run.result.prepared_asset.id,
			);
		assert.equal(selectButton().disabled, true);
		assert.equal(
			rig.calls.some((call) => call.path === "projects/save"),
			false,
			"selection remains an editable draft until native Save project",
		);
	});
}

test("a roof change between display and click cannot bind the earlier PV result", async (t) => {
	const rig = await sourceRig(t, "pv");
	await until(() => selectButton() && !selectButton().disabled);
	await rig.change((current) => {
		const changed = structuredClone(current);
		changed.geometry.arrays[0].columns++;
		return changed;
	}, false);
	await act(async () => selectButton().click());
	assert.equal(rig.edits, 0);
	assert.match(
		document.body.textContent,
		/source.*roof.*model.*changed|inputs.*changed/i,
	);
	assert.equal(
		rig.inputs.profile_selections?.selected?.pv_available_ac,
		undefined,
	);
});

test("an inconsistent stored source blocks selection without saying the user's roof changed", async (t) => {
	const asset = structuredClone(fixture.pv_run.result.prepared_asset);
	asset.content_sha256 = "0".repeat(64);
	const rig = await sourceRig(t, "pv", { asset });
	await until(() =>
		/source could not be checked/i.test(document.body.textContent),
	);
	assert.equal(selectButton().disabled, true);
	assert.equal(rig.edits, 0);
	assert.doesNotMatch(
		document.body.textContent,
		/The source request, roof or model has changed/,
	);
});

test("selection checks the current identity again and failed source access triggers session recheck", async (t) => {
	const rig = await sourceRig(t, "pv");
	await until(() => selectButton() && !selectButton().disabled);
	rig.dropScope();
	await act(async () => selectButton().click());
	assert.equal(rig.edits, 0);
});

test("a forbidden source read rechecks identity and leaves existing inputs intact", async (t) => {
	const rig = await sourceRig(t, "pv", {
		failure: new ApiError(403, "forbidden"),
	});
	await until(() => rig.rechecks > 0);
	assert.equal(selectButton().disabled, true);
	assert.equal(rig.edits, 0);
});

test("mixed history opens a real PV preparation result without invoking energy-result readers", async (t) => {
	const run = fixture.pv_run,
		project = fixture.pv_project,
		calls = [];
	function Harness() {
		window.history.replaceState(
			null,
			"",
			`?project=${project.id}&run=${run.id}#lp-calculations`,
		);
		const client = {
			isCurrentScope: (value) => value === scope,
			async query(path, body) {
				calls.push(path);
				if (path === "projects/runs")
					return {
						items: [fixture.weather_run, fixture.pv_run].map((item) => ({
							id: item.id,
							project_id: item.project_id,
							revision: item.revision,
							state: item.state,
							is_current: item.is_current,
							manifest_sha256: item.manifest_sha256,
							result_sha256: item.result_sha256,
							created_at: 1700000000,
							task_kind: item.manifest.context.parameters.kind,
						})),
						next: null,
					};
				if (path === "runs/read") return run;
				if (path === "projects/read") return project;
				if (path === "assets/read")
					return body.asset_id === fixture.weather_run.result.prepared_asset.id
						? fixture.weather_run.result.prepared_asset
						: run.result.prepared_asset;
				throw new Error("unexpected query " + path);
			},
			send() {
				throw new Error("opening history must not dispatch a mutation");
			},
		};
		return React.createElement(EnergyWorkspace, {
			draft: beginDraft(project),
			edit: () => true,
			flush: async () => true,
			session,
			client,
			recheck: () => {},
			locale: "en-GB",
			active: true,
			blocked: false,
			onValidity: () => {},
			openProfiles: () => {},
		});
	}
	await mount(t, React.createElement(Harness));
	await until(() => selectButton() && !selectButton().disabled);
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/2,943.945/,
	);
	assert.doesNotMatch(
		document.querySelector(".lp-run-result").textContent,
		/Battery parameters|Self-sufficiency/,
	);
	assert.ok(calls.includes("runs/read"));
});

for (const state of ["not_started", "fetching"]) {
	test(`weather status ${state} never promises a usable source or sends provider work`, async (t) => {
		const status = structuredClone(fixture.weather_status),
			calls = [];
		status.task_state = "cancelled";
		status.acquisition_state = state;
		status.capture_sha256 = null;
		const client = {
			isCurrentScope: () => true,
			async query(path) {
				calls.push(path);
				assert.equal(path, "runs/weather/status");
				return status;
			},
			send() {
				throw new Error("status is read-only");
			},
		};
		await mount(
			t,
			React.createElement(WeatherProgress, {
				runId: status.run_id,
				session,
				client,
				recheck: () => {},
				active: true,
			}),
		);
		await until(
			() =>
				!/Reading weather|Checking weather/i.test(document.body.textContent),
		);
		const text = document.body.textContent;
		assert.match(text, /ended without a validated weather source/);
		assert.doesNotMatch(text, /Source ready/);
		assert.equal(
			calls.length,
			1,
			"terminal local work has no unbounded provider polling",
		);
	});
}
