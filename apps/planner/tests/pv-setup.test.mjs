import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import { readSolarSetup } from "../src/domain/solarSetup.ts";
import {
	beginDraft,
	editDraft,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import fixture from "./fixtures/index.ts";

// The existing synthetic model is served through the maintained-source
// contract. This fixture is never a runtime product or manufacturer fact.
function maintainedInputs(value) {
	const inputs = structuredClone(value);
	const source = {
		kind: "datasheet",
		note: "Synthetic maintained-source contract fixture",
		url: "https://example.test/module.pdf",
		document_sha256: "b".repeat(64),
		page: 1,
		woo: {
			product_id: 42,
			product_revision: "a".repeat(64),
			reference_input_id: "synthetic_woo_reference",
		},
	};
	for (const module of inputs.geometry.module_specs) module.source = source;
	for (const module of inputs.pv_generation?.modules ?? [])
		module.source = source;
	return inputs;
}
const maintained = maintainedInputs(fixture.pv_project.inputs);
const moduleReply = {
	schema_version: 1,
	provider: "woocommerce",
	pv_modules: [
		{
			specification: maintained.geometry.module_specs[0],
			parameters: maintained.pv_generation.modules[0],
		},
	],
};

const visible = (node) => !node.closest("[hidden]");
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim().endsWith(text) && visible(node),
	);
const control = (text) =>
	[...document.querySelectorAll("label")]
		.find(
			(node) =>
				visible(node) &&
				node.querySelector("span")?.textContent.startsWith(text),
		)
		?.querySelector("input,textarea,select");
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
async function mount(t, inputs, locale = "en-GB") {
	inputs = maintainedInputs(inputs);
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const project = { ...fixture.pv_project, inputs, revision: 3 },
		scope = "a".repeat(64),
		requests = [],
		session = {
			query_scope: scope,
			runtime: {
				models: {},
				limits: {
					max_json_depth: 32,
					max_body_bytes: 16777216,
					max_page_size: 100,
				},
			},
		},
		queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
	let current = beginDraft(project),
		setter,
		serverRun = null;
	const edit = (operation) => {
		try {
			current = editDraft(current, operation(current.history.current));
			setter(current);
			return true;
		} catch {
			return false;
		}
	};
	const client = {
		isCurrentScope: (value) => value === scope,
		async send(path, serialized) {
			const body = JSON.parse(serialized);
			requests.push({ path, body });
			assert.equal(path, "runs/pv");
			serverRun = {
				...fixture.pv_run,
				state: "queued",
				result: null,
				result_sha256: null,
				revision: body.expected_revision,
				manifest: {
					...fixture.pv_run.manifest,
					revision: body.expected_revision,
				},
			};
			return serverRun;
		},
		async query(path) {
			if (path === "products/current") return moduleReply;
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
									task_kind: "prepare_roof_pv_reference_v1",
								},
							]
						: [],
					next: null,
				};
			if (path === "runs/read") return serverRun;
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
				locale,
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
	await click("PV generation");
	await until(() => !button("Prepare PV model").disabled);
	await until(
		() => !button("Update parameters for current roof layout").disabled,
	);
	return {
		current: () => current,
		requests,
		edit: async (operation) => act(async () => edit(operation)),
	};
}

test("blank PV model can be completed through actual controls, keeps unfinished values across views, then sends one saved-revision task", async (t) => {
	const inputs = structuredClone(fixture.pv_project.inputs);
	delete inputs.pv_generation;
	inputs.unrelated = "retained";
	const h = await mount(t, inputs),
		expected = maintained.pv_generation,
		note = expected.source_note;
	assert.equal(button("Calculate PV for saved inputs").disabled, true);
	await click("Prepare PV model");
	assert.match(
		document.querySelector(".lp-focus-target").textContent,
		/complete module, array and conversion/,
	);
	await click("Update parameters for current roof layout");
	assert.equal(control("Temperature coefficient of maximum power"), undefined);
	assert.match(document.querySelector(".lp-pv-parameters").textContent, /-0.4/);
	await click("Array models");
	const reflectance = control("Ground reflectance");
	await enter(reflectance, "-");
	assert.equal(reflectance.getAttribute("aria-invalid"), "true");
	assert.equal(button("Confirm project save fixture").disabled, true);
	await click("Weather source");
	await click("PV generation");
	await click("Array models");
	assert.equal(control("Ground reflectance"), reflectance);
	assert.equal(reflectance.value, "-");
	await enter(reflectance, "20");
	assert.equal(
		h.current().history.current.solar_setup.pv.arrays[0].albedo,
		0.2,
	);
	await choose("Irradiance transposition", "perez");
	for (const [label, value] of [
		["Ground reflectance", "20"],
		["ASHRAE incidence-angle coefficient b", "0"],
		["Retained sky-diffuse irradiance", "100"],
		["Retained ground-reflected irradiance", "100"],
		["Spectral factor", "100"],
		["Irradiance retained after soiling", "100"],
		["DC power retained after wiring losses", "100"],
		["DC power retained after mismatch losses", "100"],
		["SAPM coefficient a", "-3.47"],
		["SAPM coefficient b", "-0.0594"],
		["Cell-to-module ΔT at 1000 W/m²", "3"],
	])
		await enter(control(label), value);
	await enter(control("Irradiance and loss assumptions"), note);
	await enter(
		control("Temperature-model source and mounting conditions"),
		note,
	);
	await click("Power conversion");
	await click("Add conversion group");
	assert.equal(control("PVWatts DC reference power").value, "");
	assert.equal(control("Nominal conversion efficiency").value, "");
	await act(async () =>
		document.querySelector('.lp-pv-membership input[type="checkbox"]').click(),
	);
	await enter(control("PVWatts DC reference power"), "10000");
	await enter(control("Nominal conversion efficiency"), "96");
	await enter(control("PVWatts reference efficiency"), "96.37");
	await enter(control("Conversion-model source and assumptions"), note);
	await enter(control("Overall PV model assumptions"), note);
	await click("Prepare PV model");
	const prepared = h.current().history.current.pv_generation;
	assert.deepEqual(prepared, {
		...expected,
		converters: [{ ...expected.converters[0], id: prepared.converters[0].id }],
	});
	assert.deepEqual(
		h.current().history.current.pv_preparation,
		inputs.pv_preparation,
	);
	assert.equal(h.current().history.current.unrelated, "retained");
	assert.equal(button("Calculate PV for saved inputs").disabled, true);
	assert.equal(h.requests.length, 0);
	await click("Confirm project save fixture");
	await until(() => !button("Calculate PV for saved inputs").disabled);
	await act(async () => {
		button("Calculate PV for saved inputs").click();
		button("Calculate PV for saved inputs")?.click();
	});
	await until(
		() =>
			h.requests.length === 1 &&
			button("Saved calculations").getAttribute("aria-pressed") === "true",
	);
	assert.equal(h.requests[0].path, "runs/pv");
	assert.equal(h.requests[0].body.expected_revision, 4);
	assert.match(h.requests[0].body.key, /^[a-f0-9-]{36}$/);
	assert.deepEqual(Object.keys(h.requests[0].body).sort(), [
		"expected_revision",
		"key",
		"project_id",
		"schema_version",
	]);
	await until(() =>
		/Roof-to-PV|PV generation/.test(
			document.querySelector(".lp-run-history")?.textContent ?? "",
		),
	);
});

test("conversion membership prevents a second assignment and requires complete model preparation after edits", async (t) => {
	const inputs = structuredClone(fixture.pv_project.inputs);
	inputs.energy_replay = { schema_version: 1 };
	const h = await mount(t, inputs);
	await click("Power conversion");
	await click("Add conversion group");
	let boxes = [
		...document.querySelectorAll('.lp-pv-membership input[type="checkbox"]'),
	];
	assert.equal(boxes[0].checked, true);
	assert.equal(boxes[1].disabled, true);
	assert.equal(h.current().history.current.pv_generation, undefined);
	assert.equal(h.current().history.current.energy_replay, undefined);
	await act(async () => boxes[0].click());
	boxes = [
		...document.querySelectorAll('.lp-pv-membership input[type="checkbox"]'),
	];
	assert.equal(boxes[1].disabled, false);
	await act(async () => boxes[1].click());
	assert.equal(
		document.querySelector('.lp-pv-membership input[type="checkbox"]').disabled,
		true,
	);
	await click("Prepare PV model");
	assert.match(
		document.querySelector(".lp-focus-target").textContent,
		/complete module, array and conversion/,
	);
	assert.equal(h.requests.length, 0);
});

test("PV dispatch refuses a weather/roof location mismatch and tolerates unsupported stored selections", async (t) => {
	const inputs = structuredClone(fixture.pv_project.inputs);
	inputs.weather_acquisition.request.latitude_deg = 51;
	const h = await mount(t, inputs);
	await click("Calculate PV for saved inputs");
	assert.match(
		document.querySelector(".lp-focus-target").textContent,
		/weather coordinates differ/i,
	);
	assert.equal(h.requests.length, 0);
	await h.edit((current) => ({ ...current, pv_preparation: "unsupported" }));
	assert.equal(button("Calculate PV for saved inputs").disabled, true);
	assert.ok(document.querySelector(".lp-energy-workspace"));
});

test("module evidence is read-only and historical missing bindings explain the required selection", async (t) => {
	const inputs = structuredClone(fixture.pv_project.inputs);
	const h = await mount(t, inputs);
	assert.equal(control("Temperature coefficient of maximum power"), undefined);
	await h.edit((current) => {
		const setup = readSolarSetup(current);
		return {
			...current,
			solar_setup: {
				...setup,
				pv: {
					...setup.pv,
					modules: setup.pv.modules.map((module) => ({
						...module,
						source: fixture.pv_project.inputs.pv_generation.modules[0].source,
					})),
				},
			},
		};
	});
	assert.match(
		document.querySelector(".lp-pv-parameters").textContent,
		/requires an updated module selection/,
	);
	assert.equal(h.requests.length, 0);
	await h.edit((current) => ({
		...current,
		solar_setup: {
			...current.solar_setup,
			pv: {
				...current.solar_setup.pv,
				modules: [
					{
						...current.solar_setup.pv.modules[0],
						module_spec_id: "module_private_X",
					},
				],
			},
		},
	}));
	assert.match(
		document.querySelector(".lp-pv-parameters h4").textContent,
		/Module specification outside the current layout/,
	);
	assert.doesNotMatch(
		document.querySelector(".lp-energy-workspace").textContent,
		/module_private_X/,
	);
});

test("German percentage edits retain exact text and decimal separators while storing model fractions", async (t) => {
	const h = await mount(t, structuredClone(fixture.pv_project.inputs), "de-DE");
	assert.equal(control("Temperature coefficient of maximum power"), undefined);
	assert.match(document.querySelector(".lp-pv-parameters").textContent, /-0,4/);
	await click("Array models");
	await enter(control("Ground reflectance"), "57");
	assert.equal(control("Ground reflectance").value, "57");
	await enter(control("Irradiance retained after soiling"), "56");
	assert.equal(control("Irradiance retained after soiling").value, "56");
	await enter(control("Ground reflectance"), "0,");
	assert.equal(control("Ground reflectance").value, "0,");
	await enter(control("Ground reflectance"), "0,57");
	assert.equal(control("Ground reflectance").value, "0,57");
	assert.equal(
		h.current().history.current.solar_setup.pv.arrays[0].albedo,
		0.0057,
	);
	assert.equal(
		h.current().history.current.solar_setup.pv.arrays[0].soiling_factor,
		0.56,
	);
	await click("Power conversion");
	await enter(control("Nominal conversion efficiency"), "57");
	assert.equal(control("Nominal conversion efficiency").value, "57");
	assert.equal(
		h.current().history.current.solar_setup.pv.converters[0].eta_nominal,
		0.57,
	);
	await click("Scenario settings");
	await enter(control("Charging efficiency"), "57");
	assert.equal(control("Charging efficiency").value, "57");
});
