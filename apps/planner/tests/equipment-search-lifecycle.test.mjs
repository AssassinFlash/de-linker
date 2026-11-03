import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";
import { environmentManager } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
register("./map-library-loader.mjs", import.meta.url);

const SEARCH_TASK = "search_woo_equipment_v1";

function makeSession() {
	return {
		schema_version: 1,
		kind: "guest",
		cookie_confirmed: true,
		expires_at: 2000000000,
		query_scope: "3".repeat(64),
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
}

/** A saved single-system equipment plan with consistent requirements. */
const savedRequirements = {
	schema_version: 1,
	grid_phase: 3,
	operating_mode: "grid_connected",
	pv_dc_kw: 200,
	required_usable_kwh: 61.4,
	required_discharge_ac_kw: 100,
};
const savedSetup = {
	schema_version: 1,
	inverter_product_id: null,
	battery_product_id: null,
	modules_per_stack: null,
	parallel_stacks: null,
	accessory_product_ids: [],
	grid_phase: 3,
	operating_mode: "grid_connected",
	pv_dc_kw: 200,
	required_usable_kwh: 61.4,
	required_discharge_ac_kw: 100,
};
const emptySetup = {
	schema_version: 1,
	inverter_product_id: null,
	battery_product_id: null,
	modules_per_stack: null,
	parallel_stacks: null,
	accessory_product_ids: [],
	grid_phase: null,
	operating_mode: null,
	pv_dc_kw: null,
	required_usable_kwh: null,
	required_discharge_ac_kw: null,
};

const catalog = () => ({
	schema_version: 1,
	provider: "woocommerce",
	products: [
		{
			id: 101,
			canonical_product_id: 101,
			product_revision: "6".repeat(64),
			model: "ESS 5K",
			brand: "Linker",
			device_class: "hybrid_inverter",
			figures: { ac_output_kw_nominal: 5 },
		},
		{
			id: 201,
			canonical_product_id: 201,
			product_revision: "6".repeat(64),
			model: "Battery HV",
			brand: "Linker",
			device_class: "battery_system",
			figures: { module_energy_kwh_usable: 5 },
		},
	],
	battery_assemblies: {},
	dc_battery_ports: {},
	parallel_controller_product_ids: [],
	cable_references: [],
	figure_projection_version: 2,
	compatibility_origin: "woocommerce",
});

/** Server-side run document for runs/equipment-search, per planningProtocol. */
function makeRun(projectId, state) {
	const succeeded = state === "succeeded";
	const search = succeeded
		? {
				schema: 1,
				kind: SEARCH_TASK,
				project_id: projectId,
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
								pv_dc_kw: 200,
								required_usable_kwh: 61.4,
								required_discharge_ac_kw: 100,
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
							model: "ESS 5K",
							brand: "Linker",
							sku: "L-ESS-5K",
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
		project_id: projectId,
		revision: 1,
		manifest_sha256: "a".repeat(64),
		result_sha256: succeeded ? "b".repeat(64) : null,
		state,
		is_current: true,
		manifest: {
			schema: 1,
			project_id: projectId,
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
		error: null,
	};
}

const runPageItem = (run) => ({
	id: run.id,
	project_id: run.project_id,
	revision: run.revision,
	manifest_sha256: run.manifest_sha256,
	result_sha256: run.result_sha256,
	state: run.state,
	is_current: run.is_current,
	created_at: 1730000000,
	task_kind: SEARCH_TASK,
});

async function equipmentApp(t, { projectId, inputs, hash }) {
	const fixture = setupDom();
	// jsdom loads after module evaluation, so query-core's module-level isServer
	// const stays true and would disable refetchInterval scheduling entirely.
	environmentManager.setIsServer(() => false);
	globalThis.indexedDB = new IDBFactory();
	window.history.replaceState(
		null,
		"",
		`/workspace/?project=${projectId}${hash}`,
	);
	const browserGlobals = new Map();
	const browserValues = {
		MutationObserver: window.MutationObserver,
		getComputedStyle: window.getComputedStyle.bind(window),
		requestAnimationFrame: (callback) =>
			setTimeout(() => callback(Date.now()), 0),
		cancelAnimationFrame: clearTimeout,
	};
	for (const [name, value] of Object.entries(browserValues)) {
		browserGlobals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value,
			configurable: true,
			writable: true,
		});
	}
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { ApiError } = await import("../src/data/protocol.ts");
	const brief = emptyBrief();
	brief.annual_load.kwh = 10;
	const project = {
		id: projectId,
		title: "Equipment lifecycle fixture",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: { brief, ...inputs },
	};
	const session = makeSession();
	let serverRun = null,
		admittedScope = session.query_scope;
	const store = {
		async read() {
			return null;
		},
		async readProfileImports() {
			return [];
		},
		async candidates() {
			return [];
		},
		async write() {},
	};
	const client = {
		origin: location.origin,
		invalidate() {
			admittedScope = null;
		},
		async bootstrap() {
			admittedScope = session.query_scope;
			return session;
		},
		isCurrentScope(scope) {
			return scope === admittedScope;
		},
		async query(path) {
			if (path === "products/current") return catalog();
			if (path === "projects/runs")
				return {
					schema_version: 1,
					items: serverRun ? [runPageItem(serverRun)] : [],
					next: null,
				};
			if (path === "runs/read") return structuredClone(serverRun);
			if (path === "projects/read") return structuredClone(project);
			throw new ApiError(404, "not_found");
		},
		async send(path) {
			if (path === "runs/equipment-search") {
				serverRun = makeRun(projectId, "queued");
				return structuredClone(serverRun);
			}
			throw new ApiError(404, "not_found");
		},
	};
	const config = {
		baseUrl: location.origin + "/api/",
		nonceUrl: location.origin + "/nonce",
		locale: "en-US",
		countries: { NO: "Norway" },
	};
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of browserGlobals) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(SessionBoundary, { client }, (value, recheck) =>
					React.createElement(Workspace, {
						key: value.query_scope,
						session: value,
						client,
						store,
						config,
						recheck,
					}),
				),
			),
		),
	);
	const button = (text) =>
		[...document.querySelectorAll("button")].find(
			(node) =>
				node.textContent === text &&
				!node.closest("[hidden]") &&
				node.getAttribute("aria-hidden") !== "true",
		);
	const fieldInput = (label) =>
		[...document.querySelectorAll("input")].find((input) =>
			document
				.getElementById(input.getAttribute("aria-labelledby"))
				?.textContent.includes(label),
		);
	const fieldSelect = (label) =>
		[...document.querySelectorAll("label.lp-field")]
			.find((node) => node.querySelector("span")?.textContent.includes(label))
			?.querySelector("select");
	return {
		root,
		fixture,
		client,
		project,
		fieldInput,
		fieldSelect,
		button,
		runHeading: () =>
			document.querySelector(".lp-run-result h3")?.textContent ?? null,
		setServerRun(state) {
			serverRun = makeRun(projectId, state);
		},
		serverRunId: () => serverRun?.id ?? null,
	};
}

/** Wait for a condition across real poll intervals (default budget 12s). */
async function untilRun(predicate) {
	const deadline = performance.now() + 12000;
	do {
		await act(async () => {
			await new Promise((resolve) => setTimeout(resolve, 25));
		});
		if (predicate()) return;
	} while (performance.now() < deadline);
	throw new Error("Expected run state was not reached");
}

test("equipment search results appear without a manual refresh", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		inputs: {
			equipment_setup: savedSetup,
			equipment_requirements: savedRequirements,
		},
		hash: "#lp-equipment",
	});
	await untilRun(() => app.button("Find equipment combinations"));
	const search = () => app.button("Find equipment combinations");
	await untilRun(() => search() && !search().disabled);
	await act(async () => search().click());
	// The accepted reply seeds the queued run; the workspace must switch to
	// the saved-calculations view on its own.
	await untilRun(() => app.runHeading() === "Queued");
	app.setServerRun("running");
	await untilRun(
		() => app.runHeading() === "Searching for equipment combinations…",
	);
	app.setServerRun("succeeded");
	await untilRun(() => app.runHeading() === "Equipment search finished");
	const option = [...document.querySelectorAll("option")].find((node) =>
		node.textContent.includes("Linker ESS 5K"),
	);
	assert.ok(option, "expected the found combination to be listed");
	assert.match(
		document.body.textContent,
		/Combinations assessed[^]*1/,
		"expected one assessed combination",
	);
	assert.equal(
		new URL(window.location.href).searchParams.get("run"),
		app.serverRunId(),
		"expected the finished run to be selected in the URL",
	);
});

test("saved equipment requirements backfill the form after reopen", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "9".repeat(32),
		inputs: {
			// A previously prepared project whose setup row was saved empty.
			equipment_setup: emptySetup,
			equipment_requirements: savedRequirements,
		},
		hash: "#lp-equipment",
	});
	await untilRun(() => app.button("Find equipment combinations"));
	await untilRun(() => app.fieldInput("Required usable energy"));
	assert.equal(app.fieldInput("PV array").value, "200");
	assert.equal(app.fieldInput("Required usable energy").value, "61.4");
	assert.equal(
		app.fieldInput("Required continuous AC discharge power").value,
		"100",
	);
	assert.equal(
		app.fieldSelect("Choose an operating mode").value,
		"grid_connected",
	);
	assert.equal(app.fieldSelect("Grid connection").value, "3");
	// Backfilled values must also satisfy the prepared-search preconditions.
	const search = () => app.button("Find equipment combinations");
	await untilRun(() => search() && !search().disabled);
	assert.ok(!search().disabled, "expected the search button enabled");
});

test("requirements-only projects still backfill the form", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "5".repeat(32),
		inputs: { equipment_requirements: savedRequirements },
		hash: "#lp-equipment",
	});
	await untilRun(() => app.fieldInput("Required usable energy"));
	assert.equal(app.fieldInput("PV array").value, "200");
	assert.equal(app.fieldInput("Required usable energy").value, "61.4");
	assert.equal(
		app.fieldInput("Required continuous AC discharge power").value,
		"100",
	);
	assert.equal(
		app.fieldSelect("Choose an operating mode").value,
		"grid_connected",
	);
	assert.equal(app.fieldSelect("Grid connection").value, "3");
});

test("a backgrounded tab keeps polling the search to completion", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "6".repeat(32),
		inputs: {
			equipment_setup: savedSetup,
			equipment_requirements: savedRequirements,
		},
		hash: "#lp-equipment",
	});
	await untilRun(() => app.button("Find equipment combinations"));
	const search = () => app.button("Find equipment combinations");
	await untilRun(() => search() && !search().disabled);
	await act(async () => search().click());
	await untilRun(() => app.runHeading() === "Queued");
	// Hide the document like a user switching tabs mid-search. The interval
	// must keep refetching (refetchIntervalInBackground) instead of freezing
	// on "Searching for equipment combinations…" until the tab is focused.
	Object.defineProperty(document, "visibilityState", {
		value: "hidden",
		configurable: true,
	});
	window.dispatchEvent(new window.Event("visibilitychange"));
	app.setServerRun("succeeded");
	try {
		await untilRun(() => app.runHeading() === "Equipment search finished");
	} finally {
		delete document.visibilityState;
	}
	assert.equal(
		app.runHeading(),
		"Equipment search finished",
		"expected the finished run while the tab stays hidden",
	);
});
