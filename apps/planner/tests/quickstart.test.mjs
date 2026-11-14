import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import {
	QuickStart,
	QUICK_START_COMMERCIAL_KWH,
	QUICK_START_GOALS,
	QUICK_START_ORIENTATIONS,
	QUICK_START_PV_SIZES,
	QUICK_START_RESIDENTIAL_KWH,
	quickStartAnnualOptions,
	quickStartDefaults,
	mergeQuickStartInputs,
	quickStartChoicesFrom,
	quickStartInputs,
	quickStartReady,
	quickStartSizing,
} from "../src/components/QuickStart.tsx";
import {
	DEFAULT_MODULE_TIER,
	MODULE_TIERS,
} from "../src/domain/moduleTiers.ts";
import { readBrief } from "../src/domain/brief.ts";
import { readEquipmentRequirements } from "../src/domain/equipmentRequirements.ts";

const SEARCH_TASK = "search_woo_equipment_v1";
const PROJECT_ID = "1".repeat(32);
const SCOPE = "3".repeat(64);

const session = {
	schema_version: 1,
	kind: "guest",
	cookie_confirmed: true,
	expires_at: 2000000000,
	query_scope: SCOPE,
	nonce: "abcdefghij",
	claim_pending: false,
	runtime: {
		schema_version: 1,
		runtime_sha256: "4".repeat(64),
		models: { equipment_search: SEARCH_TASK },
		limits: {
			max_body_bytes: 1000000,
			max_csv_bytes: 100000,
			max_page_size: 30,
			max_json_depth: 32,
		},
	},
};

function projectRecord(title, inputs) {
	return {
		id: PROJECT_ID,
		title,
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs,
	};
}

/** A server-side run document the planning protocol accepts, per task. */
function searchRun(state) {
	const succeeded = state === "succeeded";
	const search = succeeded
		? {
				schema: 1,
				kind: SEARCH_TASK,
				project_id: PROJECT_ID,
				revision: 1,
				input_sha256: "2".repeat(64),
				manifest_sha256: "a".repeat(64),
				runtime_sha256: "4".repeat(64),
				pinned_assets: { "woo.equipment_inputs": "5".repeat(64) },
				search: {
					coverage: {
						template: "one_converter_one_external_battery_assembly",
						gaps: {},
					},
					completion: "budget_exhausted",
					work_used: 4,
					work_budget: 1000,
					candidates: [
						{
							id: "c".repeat(64),
							assessment_sha256: "d".repeat(64),
							status: "satisfied",
							violated_checks: 0,
							unresolved_checks: 0,
							selection: {
								schema_version: 1,
								inverter_product_id: 101,
								battery_product_id: 201,
								modules_per_stack: 5,
								parallel_stacks: 2,
								accessory_product_ids: [],
								grid_phase: 3,
								operating_mode: "grid_connected",
								pv_dc_kw: 10,
								required_usable_kwh: 13.7,
								required_discharge_ac_kw: 6,
								product_revisions: {
									101: "6".repeat(64),
									201: "6".repeat(64),
								},
							},
						},
					],
					qualified_count: 1,
					products: [
						{
							canonical_product_id: 101,
							model: "ESS 10K",
							brand: "Linker",
							sku: "L-ESS-10K",
							product_revision: "6".repeat(64),
						},
						{
							canonical_product_id: 201,
							model: "Battery HV",
							brand: "Linker",
							sku: "L-BAT-HV",
							product_revision: "6".repeat(64),
						},
					],
					ranking: "not_performed_before_qualification",
				},
			}
		: null;
	return {
		id: "7".repeat(32),
		project_id: PROJECT_ID,
		revision: 1,
		manifest_sha256: "a".repeat(64),
		result_sha256: succeeded ? "b".repeat(64) : null,
		state,
		is_current: true,
		manifest: {
			schema: 1,
			project_id: PROJECT_ID,
			revision: 1,
			input_sha256: "2".repeat(64),
			context: {
				code_sha256: "4".repeat(64),
				models: { task: SEARCH_TASK },
				assets: { "woo.equipment_inputs": "5".repeat(64) },
				parameters: { kind: SEARCH_TASK },
			},
		},
		result: search,
		error: succeeded ? null : { code: "resource_limit" },
	};
}

/** Current product data before its figures are projected: not usable yet. */
const unpreparedCatalog = {
	schema_version: 1,
	provider: "woocommerce",
	products: [
		{
			id: 101,
			canonical_product_id: 101,
			product_revision: "6".repeat(64),
			model: "ESS 10K",
			brand: "Linker",
			device_class: "inverters",
			figures: {},
		},
	],
	dc_battery_ports: {},
	battery_assemblies: {},
	parallel_controller_product_ids: [],
	cable_references: [],
};

function draftStore() {
	const writes = [];
	return {
		writes,
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async write(_scope, draft) {
			writes.push(draft);
		},
	};
}

/**
 * Duck-typed transport for the two surfaces this screen uses. `searchStates`
 * is consumed in order so a retry can answer with a different outcome.
 */
function quickStartClient({ searchStates = [], onCreate } = {}) {
	const calls = [];
	let searchIndex = 0;
	const client = {
		origin: "https://fixture.invalid",
		calls,
		isCurrentScope: (value) => value === SCOPE,
		async send(path, body) {
			calls.push(path);
			if (path === "projects/create") {
				const command = JSON.parse(body);
				onCreate?.(command);
				return projectRecord(command.title, command.inputs);
			}
			if (path === "runs/equipment-search") {
				const state = searchStates[searchIndex++] ?? "failed";
				return searchRun(state);
			}
			throw new Error("Unexpected request " + path);
		},
		async query(path) {
			calls.push(path);
			if (path === "products/current") return unpreparedCatalog;
			throw new Error("Unexpected request " + path);
		},
	};
	return client;
}

async function renderQuickStart(t, client, options = {}) {
	const dom = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const root = (await import("react-dom/client")).createRoot(dom.element);
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(QuickStart, {
					session,
					client,
					store: draftStore(),
					config: {
						locale: "en-GB",
						countries: { DE: "Germany", FR: "France" },
					},
					recheck: () => undefined,
					...options,
				}),
			),
		),
	);
	return { dom, root };
}

const selectByLabel = (text) =>
	[...document.querySelectorAll("label")]
		.find((node) => node.querySelector("span")?.textContent === text)
		?.querySelector("select");
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim() === text,
	);
/** Choose a select option the way a reader does: value, then its change event. */
const chooseIn = async (label, value) => {
	const select = selectByLabel(label);
	if (!select) throw new Error("Missing select: " + label);
	await act(async () => {
		Object.getOwnPropertyDescriptor(
			window.HTMLSelectElement.prototype,
			"value",
		).set.call(select, value);
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
};
const stepNode = (id) =>
	document.querySelector(`.lp-quickstart-steps [data-step="${id}"]`);

test("the one-screen start opens on the approved planning defaults", async (t) => {
	const client = quickStartClient();
	await renderQuickStart(t, client);

	await until(
		() =>
			selectByLabel("Project type") !== undefined &&
			selectByLabel("PV array size") !== undefined,
	);

	assert.equal(quickStartDefaults().moduleTierId, DEFAULT_MODULE_TIER.id);
	assert.equal(DEFAULT_MODULE_TIER.stc_power_w, 450);
	assert.equal(selectByLabel("Project type").value, "residential");
	assert.equal(selectByLabel("PV array size").value, "10");
	assert.equal(selectByLabel("Roof orientation and tilt").value, "south_30");
	assert.equal(
		selectByLabel("Module power class").value,
		DEFAULT_MODULE_TIER.id,
	);
	assert.equal(
		selectByLabel("Module power class").selectedOptions[0].textContent,
		"450 Wp",
	);
	assert.equal(selectByLabel("Annual electricity use").value, "5000");
	assert.equal(selectByLabel("Grid connection").value, "3");
	assert.equal(
		selectByLabel("Grid connection").selectedOptions[0].textContent,
		"Three-phase",
	);
	assert.equal(selectByLabel("System goal").value, "self_use");
	assert.equal(
		selectByLabel("System goal").selectedOptions[0].textContent,
		"Use as much of my own solar as possible",
	);
	// Nothing was requested before the customer pressed the one button.
	assert.deepEqual(client.calls, []);
});

test("every list carries the approved options and the location is the only required field", async (t) => {
	const client = quickStartClient();
	await renderQuickStart(t, client);
	await until(() => selectByLabel("PV array size") !== undefined);

	const options = (label) =>
		[...selectByLabel(label).options].map((o) => o.value);
	assert.deepEqual(options("Project type"), ["residential", "commercial"]);
	assert.deepEqual(options("PV array size"), QUICK_START_PV_SIZES.map(String));
	assert.deepEqual(
		QUICK_START_PV_SIZES,
		[5, 8, 10, 12, 15, 20, 30, 50, 80, 100],
	);
	assert.deepEqual(options("Roof orientation and tilt"), [
		...QUICK_START_ORIENTATIONS,
	]);
	assert.deepEqual(
		options("Module power class"),
		MODULE_TIERS.map((t) => t.id),
	);
	assert.deepEqual(
		MODULE_TIERS.map((tier) => tier.stc_power_w),
		[400, 450, 500, 550, 600],
	);
	assert.deepEqual(options("Annual electricity use"), [
		"3500",
		"5000",
		"7500",
		"10000",
		"15000",
	]);
	assert.deepEqual(
		QUICK_START_RESIDENTIAL_KWH,
		[3500, 5000, 7500, 10000, 15000],
	);
	assert.deepEqual(options("Grid connection"), ["3", "1"]);
	assert.deepEqual(options("System goal"), [...QUICK_START_GOALS]);

	const submit = button("Generate solution");
	assert.ok(submit, "the one main button must be present");
	assert.equal(submit.disabled, true, "an empty location keeps it disabled");
	assert.equal(quickStartReady(quickStartDefaults()), false);

	await enter(document.querySelector('input[type="text"]'), "10115 Berlin");
	assert.equal(
		button("Generate solution").disabled,
		true,
		"a place without its country is still incomplete",
	);
	await chooseIn("Country", "DE");
	await until(() => button("Generate solution").disabled === false);
	assert.equal(
		quickStartReady({
			...quickStartDefaults(),
			location: "x",
			country: "DE",
		}),
		true,
	);
	assert.deepEqual(client.calls, []);
});

test("choosing the commercial type swaps the annual-consumption list", async (t) => {
	const client = quickStartClient();
	await renderQuickStart(t, client);
	await until(() => selectByLabel("Project type") !== undefined);
	assert.deepEqual(
		[...quickStartAnnualOptions("commercial")],
		[...QUICK_START_COMMERCIAL_KWH],
	);
	await act(async () => {
		const select = selectByLabel("Project type");
		Object.getOwnPropertyDescriptor(
			window.HTMLSelectElement.prototype,
			"value",
		).set.call(select, "commercial");
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await until(
		() => [...selectByLabel("Annual electricity use").options].length === 5,
	);
	assert.deepEqual(
		[...selectByLabel("Annual electricity use").options].map((o) => o.value),
		["30000", "50000", "100000", "250000", "500000"],
	);
	assert.equal(selectByLabel("Annual electricity use").value, "50000");
});

test("declared choices become the project brief and declared equipment requirements", async (t) => {
	// Translated copy resolves through the native i18n global the page provides.
	const dom = setupDom();
	t.after(() => dom.dispose({ unmount: async () => undefined }));
	const choices = {
		...quickStartDefaults(),
		projectType: "commercial",
		pvKwp: 30,
		annualKwh: 100000,
		phase: 1,
		goal: "backup",
		location: " 70173 Stuttgart ",
	};
	const inputs = quickStartInputs(choices);
	const brief = readBrief(inputs.brief);
	const requirements = readEquipmentRequirements(inputs.equipment_requirements);

	assert.equal(brief.project_use, "commercial");
	assert.equal(brief.system_scope, "new_pv_storage");
	assert.equal(brief.site.location_label, "70173 Stuttgart");
	assert.equal(brief.annual_load.kwh, 100000);
	assert.equal(brief.annual_load.basis, "user_estimate");
	assert.match(String(brief.project_note), /South-facing, 30°/);
	// Declared requirements only: the search qualifies real products against them.
	assert.equal(requirements.grid_phase, 1);
	assert.equal(requirements.operating_mode, "backup");
	assert.equal(requirements.pv_dc_kw, 30);
	assert.equal(
		requirements.required_usable_kwh,
		quickStartSizing(choices).usableKwh,
	);
	assert.deepEqual(quickStartSizing(choices), {
		usableKwh: 411,
		dischargeKw: 18,
	});
});

test("re-planning an existing project keeps its roof, profiles and saved inputs", async (t) => {
	const dom = setupDom();
	t.after(() => dom.dispose({ unmount: async () => undefined }));
	const existing = {
		brief: {
			schema_version: 1,
			project_use: "residential",
			system_scope: "new_pv_storage",
			site: {
				country_code: "DE",
				location_label: "Old place",
				latitude: 52.5,
				longitude: 13.4,
				coordinate_basis: "user_entered",
				timezone: "Europe/Berlin",
			},
			annual_load: { kwh: 7500, basis: "user_estimate", source_note: "" },
			project_note: "Customer note",
		},
		geometry: { schema_version: 1, roofs: ["kept"] },
		profile_selections: {
			schema_version: 1,
			selected: { gross_load: "a".repeat(32) },
		},
		equipment_setup: {
			schema_version: 1,
			inverter_product_id: 101,
			battery_product_id: 201,
			modules_per_stack: 4,
			parallel_stacks: 1,
			accessory_product_ids: [],
			grid_phase: 3,
			operating_mode: "grid_connected",
			pv_dc_kw: 12,
			required_usable_kwh: 20,
			required_discharge_ac_kw: 8,
		},
		equipment_candidate: { run_id: "b".repeat(32) },
	};
	const restored = quickStartChoicesFrom(existing);
	assert.equal(restored.pvKwp, 12);
	assert.equal(restored.annualKwh, 7500);
	assert.equal(restored.phase, 3);
	assert.equal(restored.goal, "self_use");
	assert.equal(restored.location, "Old place");
	const choices = { ...restored, location: "70173 Stuttgart" };

	const merged = mergeQuickStartInputs(existing, choices);
	// Everything this screen does not own survives untouched.
	assert.deepEqual(merged.geometry, existing.geometry);
	assert.deepEqual(merged.profile_selections, existing.profile_selections);
	assert.equal(merged.equipment_setup.inverter_product_id, 101);
	assert.equal(merged.equipment_setup.modules_per_stack, 4);
	assert.equal(merged.equipment_candidate, undefined);
	// The declared keys follow the new choices.
	assert.equal(merged.brief.site.location_label, "70173 Stuttgart");
	assert.equal(merged.brief.site.latitude, 52.5);
	assert.equal(merged.brief.project_note, "Customer note");
	assert.equal(merged.equipment_setup.pv_dc_kw, 12);
	assert.deepEqual(
		merged.equipment_requirements,
		readEquipmentRequirements(quickStartInputs(choices).equipment_requirements),
	);
});

test("a failed step keeps the confirmed results and offers a retry for that step", async (t) => {
	const client = quickStartClient({ searchStates: ["failed", "succeeded"] });
	await renderQuickStart(t, client);
	await until(() => selectByLabel("PV array size") !== undefined);
	await enter(document.querySelector('input[type="text"]'), "10115 Berlin");
	await chooseIn("Country", "DE");
	await until(() => button("Generate solution").disabled === false);

	await act(async () => {
		button("Generate solution").click();
	});

	// The project is created, then the chain stops at the equipment search.
	await until(() => stepNode("search")?.dataset.state === "blocked");
	const save = stepNode("save");
	assert.equal(save.dataset.state, "done");
	assert.match(save.textContent, /Revision 1/);
	assert.match(stepNode("search").textContent, /resource_limit/);
	const retry = () =>
		[...stepNode("search").querySelectorAll("button")].find((node) =>
			node.textContent.includes("Retry this step"),
		);
	assert.ok(retry(), "the failed step must offer its own retry");
	// Steps this screen cannot derive say so instead of failing silently.
	assert.equal(stepNode("weather").dataset.state, "blocked");
	assert.match(stepNode("weather").textContent, /site coordinates/);
	assert.equal(stepNode("pv").dataset.state, "blocked");
	assert.match(stepNode("pv").textContent, /placed modules/);
	assert.equal(stepNode("scenario").dataset.state, "blocked");
	assert.match(stepNode("scenario").textContent, /interval data/);
	assert.equal(stepNode("energy").dataset.state, "blocked");

	// Retrying the failed step reaches the equipment result and keeps the rest.
	// The button is disabled while the recovery check for the last operation
	// settles, so the retry waits for it to become available.
	await until(() => retry() && retry().disabled === false);
	await act(async () => {
		retry().click();
	});
	await until(() =>
		document.body.textContent.includes("Recommended equipment"),
	);
	assert.equal(stepNode("search").dataset.state, "done");
	assert.equal(stepNode("save").dataset.state, "done");
	assert.match(stepNode("save").textContent, /Revision 1/);
	assert.equal(
		client.calls.filter((path) => path === "runs/equipment-search").length,
		2,
	);
	// The combination is applied only after current product data is usable; the
	// search result stays on screen and the next step says why it waits.
	assert.equal(stepNode("qualify").dataset.state, "blocked");
	assert.match(
		stepNode("qualify").textContent,
		/Current product data is still being prepared/,
	);
	assert.doesNotMatch(stepNode("save").textContent, /undefined/);
});

test("a resolved place carries its coordinates and civil time into the project", async (t) => {
	// Translated copy resolves through the native i18n global the page provides.
	const dom = setupDom();
	t.after(() => dom.dispose({ unmount: async () => undefined }));
	const choices = {
		...quickStartDefaults(),
		location: "10115 Berlin",
		country: "DE",
	};
	// What the server's bundled postcode table answers for 10115.
	const place = {
		schema_version: 1,
		found: true,
		query: "10115 Berlin",
		country_code: "DE",
		location_label: "10115 Berlin",
		latitude: 52.5323,
		longitude: 13.3846,
		region: "DE-BE",
		timezone: "Europe/Berlin",
		attribution: "Postcode positions: GeoNames (CC BY 4.0)",
	};

	const resolved = readBrief(quickStartInputs(choices, place).brief);
	assert.equal(resolved.site.country_code, "DE");
	assert.equal(resolved.site.latitude, 52.5323);
	assert.equal(resolved.site.longitude, 13.3846);
	assert.equal(resolved.site.timezone, "Europe/Berlin");
	assert.equal(resolved.site.coordinate_basis, "user_entered");

	// A miss is not an error: the typed place stays, and nothing is invented.
	const miss = {
		schema_version: 1,
		found: false,
		query: "somewhere",
	};
	const kept = readBrief(quickStartInputs(choices, miss).brief);
	assert.equal(kept.site.location_label, "10115 Berlin");
	assert.equal(kept.site.latitude, null);
	assert.equal(kept.site.timezone, null);
	assert.equal(kept.site.coordinate_basis, "not_provided");
});
