import { PlannerClient } from "../src/data/PlannerClient.ts";
import { authoredDiscoveryInputs } from "../src/domain/currentCalculation.ts";
import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { environmentManager } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
register("./map-library-loader.mjs", import.meta.url);

const SEARCH_TASK = "search_woo_equipment_v1";
const EQUIPMENT_TASK = "qualify_woo_equipment_v1";

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
			models: {
				equipment_search: SEARCH_TASK,
				report: "planning_report_v1",
				equipment_plant_search: "declared_plant_v1",
			},
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
	application: "commercial",
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
function makeRun(
	projectId,
	state,
	revision = 1,
	inputSha = "2".repeat(64),
	kind = SEARCH_TASK,
) {
	const succeeded = state === "succeeded";
	const search = succeeded
		? {
				schema: 1,
				kind: SEARCH_TASK,
				project_id: projectId,
				revision,
				input_sha256: inputSha,
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
							usable_energy_kwh: 80,
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
							energy: { nominal_kwh: 10 },
						},
					],
					ranking: "not_performed_before_qualification",
				},
			}
		: null;
	const run = {
		id: "7".repeat(32),
		project_id: projectId,
		revision,
		manifest_sha256: "a".repeat(64),
		result_sha256: succeeded ? "b".repeat(64) : null,
		state,
		is_current: true,
		manifest: {
			schema: 1,
			project_id: projectId,
			revision,
			input_sha256: inputSha,
			context: {
				code_sha256: "4".repeat(64),
				models: { task: kind },
				assets: { "woo.equipment_inputs": "5".repeat(64) },
				parameters: { kind },
			},
		},
		result: search,
		error: null,
	};
	if (kind === EQUIPMENT_TASK && succeeded)
		run.result = {
			schema: 1,
			kind,
			project_id: projectId,
			revision,
			input_sha256: inputSha,
			manifest_sha256: run.manifest_sha256,
			runtime_sha256: "4".repeat(64),
			pinned_assets: run.manifest.context.assets,
			assessment: {
				equipment_status: "satisfied",
				overall_status: "unresolved",
				checks: [],
				provisional_bill_of_materials: [],
				selected_products: [
					{ product_id: 101, model: "ESS 5K", brand: "Linker" },
				],
				country_assessment: {
					country_code: null,
					reason: "versioned_country_rules_required",
					status: "unresolved",
				},
			},
		};
	return run;
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
	task_kind: run.manifest.context.parameters.kind,
});

async function equipmentApp(
	t,
	{
		projectId,
		inputs,
		hash,
		rejectFind = false,
		validatePhase = false,
		validateHardware = false,
		demandCandidate = null,
	},
) {
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
	const requests = [];
	let frozenInputs = null;
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
	let client = {
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
					items: serverRun ? [runPageItem(serverRun)] : [],
					next: null,
				};
			if (path === "runs/read") return structuredClone(serverRun);
			if (path === "runs/inputs")
				return {
					schema_version: 1,
					project_id: projectId,
					run_id: serverRun.id,
					manifest_sha256: serverRun.manifest_sha256,
					inputs: structuredClone(frozenInputs),
				};
			if (path === "equipment/candidates/read") {
				const candidate = serverRun.result.search.candidates[0];
				return {
					run_id: serverRun.id,
					candidate_id: candidate.id,
					assessment_sha256: candidate.assessment_sha256,
					assessment: {
						equipment_status: "satisfied",
						overall_status: "satisfied",
						checks: [
							{
								id: "usable_energy",
								status: "satisfied",
								reason: "cited_usable_energy_and_sales_basis",
								facts: [],
								actual: 80,
								required: 61.4,
							},
						],
						provisional_bill_of_materials: [],
						selected_products: catalog().products.map((product) => ({
							product_id: product.id,
							model: product.model,
							brand: product.brand,
						})),
						country_assessment: {
							country_code: null,
							reason: "versioned_country_rules_required",
							status: "unresolved",
						},
					},
				};
			}
			if (path === "projects/read") return structuredClone(project);
			throw new ApiError(404, "not_found");
		},
		async send(path, body) {
			const command = JSON.parse(body);
			requests.push({ path, body: command });
			if (path === "projects/revise") {
				project.inputs = structuredClone(command.inputs);
				project.revision += 1;
				project.input_sha256 = "8".repeat(64);
				return structuredClone(project);
			}
			if (path === "runs/find-equipment" || path === "runs/check-equipment") {
				if (rejectFind) throw new ApiError(503, "request_failed");
				project.inputs = authoredDiscoveryInputs(command.inputs);
				frozenInputs = structuredClone(project.inputs);
				project.revision += 1;
				project.input_sha256 = "8".repeat(64);
				serverRun = makeRun(
					projectId,
					"queued",
					project.revision,
					project.input_sha256,
					path === "runs/check-equipment" ? EQUIPMENT_TASK : SEARCH_TASK,
				);
				return {
					schema_version: 1,
					project: structuredClone(project),
					run: structuredClone(serverRun),
				};
			}
			throw new ApiError(404, "not_found");
		},
	};
	if (validatePhase || validateHardware) {
		const adapter = client;
		const jsonReply = (body, status = 200) =>
			new Response(JSON.stringify(body), {
				status,
				headers: { "Content-Type": "application/json" },
			});
		client = new PlannerClient({
			baseUrl: location.origin + "/api/",
			nonceUrl: location.origin + "/nonce",
			origin: location.origin,
			fetch: async (url, request) => {
				const path = new URL(url).pathname;
				if (path === "/nonce") return new Response("abcdefghij");
				if (path.endsWith("/bootstrap")) return jsonReply(session);
				const operation = path.split("/rpc/")[1],
					command = JSON.parse(request.body);
				if (operation === "runs/check-equipment" && validateHardware) {
					const plant = command.inputs.equipment_plant_setup;
					const index = plant.units.findIndex(
						(unit) => unit.inputs.equipment_setup.inverter_product_id === null,
					);
					if (index >= 0) {
						requests.push({ path: operation, body: command });
						return jsonReply(
							{
								error: {
									code: "invalid_input",
									fields: [
										`equipment_plant_setup.units[${index}].inputs.equipment_setup.inverter_product_id`,
									],
								},
							},
							422,
						);
					}
				}
				if (operation === "runs/find-equipment") {
					const plant = command.inputs.equipment_plant_setup;
					const phase = plant
						? plant.requirements.grid_phase
						: command.inputs.equipment_setup.grid_phase;
					if (phase === null) {
						requests.push({ path: operation, body: command });
						const fields = plant
							? [
									{
										path: [
											"body",
											"inputs",
											"equipment_plant_setup",
											"requirements",
											"grid_phase",
										],
										kind: "literal_error",
									},
								]
							: ["equipment_setup.grid_phase"];
						return jsonReply({ error: { code: "invalid_input", fields } }, 422);
					}
				}
				try {
					return jsonReply(
						await (["runs/find-equipment", "runs/check-equipment"].includes(
							operation,
						)
							? adapter.send(operation, request.body)
							: adapter.query(operation, command)),
					);
				} catch (error) {
					return jsonReply(
						{
							error: {
								code: error.code ?? "request_failed",
								fields: error.fields,
							},
						},
						error.status ?? 500,
					);
				}
			},
		});
	}
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
		requests,
		fieldInput,
		fieldSelect,
		button,
		runHeading: () =>
			document.querySelector(".lp-run-result h3")?.textContent ?? null,
		setServerRun(state) {
			serverRun = makeRun(
				projectId,
				state,
				project.revision,
				project.input_sha256,
				serverRun.manifest.context.parameters.kind,
			);
			if (state === "succeeded" && demandCandidate) {
				serverRun.result.search.demand = {
					model: "single_ac_equipment_demand_v1",
					completion: "complete",
					interval_count: 3,
					work_used: 3,
					work_budget: 100,
				};
				serverRun.result.search.candidates[0].demand = demandCandidate;
			}
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

for (const multi of [false, true]) {
	test(`${multi ? "plant" : "single"} manually chosen hardware is checked once from current inputs and offered to the report`, async (t) => {
		const app = await equipmentApp(t, {
			projectId: (multi ? "d" : "c").repeat(32),
			hash: "#lp-equipment",
			inputs: { equipment_setup: { ...savedSetup, inverter_product_id: 101 } },
		});
		await untilRun(
			() =>
				app.button("Multiple systems") &&
				!app.button("Multiple systems").disabled,
		);
		if (multi) {
			await act(async () => app.button("Multiple systems").click());
			await until(() => app.button("System 2"));
			await act(async () => app.button("System 2").click());
			const inverter = [...document.querySelectorAll("label")]
				.find(
					(node) =>
						!node.closest("[hidden]") &&
						node.querySelector("span")?.textContent ===
							"Inverter or integrated storage system",
				)
				.querySelector("select");
			await act(async () => {
				inverter.value = "101";
				inverter.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
		}
		await untilRun(
			() =>
				app.button("Check equipment") &&
				!app.button("Check equipment").disabled,
		);
		await act(async () => app.button("Check equipment").click());
		await untilRun(() => app.runHeading() === "Queued");
		const writes = app.requests.filter((row) => row.path !== "projects/read");
		assert.deepEqual(
			writes.map((row) => row.path),
			["runs/check-equipment"],
		);
		const captured = writes[0].body.inputs;
		assert.equal(
			multi
				? captured.equipment_plant_setup.units.length
				: captured.equipment_setup.inverter_product_id,
			multi ? 2 : 101,
		);
		assert.equal(captured.energy_replay, undefined);
		assert.equal(captured.equipment_plant_requirements, undefined);
		app.setServerRun("succeeded");
		await untilRun(() => app.runHeading() === "Equipment check complete");
		assert.equal(app.button("Planning report").disabled, false);
		await act(async () => app.button("Planning report").click());
		assert.ok(
			app.fieldSelect("Equipment checks"),
			"the native report equipment selector is visible",
		);
		await untilRun(() =>
			app
				.fieldSelect("Equipment checks")
				?.querySelector(`option[value="${app.serverRunId()}"]`),
		);
		const option = app.fieldSelect("Equipment checks");
		assert.equal(option.disabled, false);
		await act(async () => {
			option.value = app.serverRunId();
			option.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
		assert.equal(option.value, app.serverRunId());
	});
}

test("a check refusal opens the named plant unit and targets its missing inverter", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "e".repeat(32),
		hash: "#lp-equipment",
		validateHardware: true,
		inputs: { equipment_setup: { ...savedSetup, inverter_product_id: 101 } },
	});
	await untilRun(
		() =>
			app.button("Multiple systems") &&
			!app.button("Multiple systems").disabled,
	);
	await act(async () => app.button("Multiple systems").click());
	await untilRun(
		() =>
			app.button("Check equipment") && !app.button("Check equipment").disabled,
	);
	await act(async () => app.button("Check equipment").click());
	const path =
		"equipment_plant_setup.units[1].inputs.equipment_setup.inverter_product_id";
	const field = () =>
		[...document.querySelectorAll("select")].find((node) => node.name === path);
	await until(
		() =>
			field()?.getAttribute("aria-invalid") === "true" &&
			document.activeElement?.getAttribute("name") === path,
	);
	assert.equal(field().closest("[hidden]"), null);
	assert.equal(app.button("System 2").getAttribute("aria-pressed"), "true");
	assert.match(
		document.getElementById(field().getAttribute("aria-describedby"))
			.textContent,
		/Choose an inverter/,
	);
	await act(async () => {
		field().value = "101";
		field().dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await until(() => field().getAttribute("aria-invalid") !== "true");
	await act(async () => app.button("Check equipment").click());
	await untilRun(() => app.runHeading() === "Queued");
	assert.equal(
		app.requests.filter((row) => row.path === "runs/check-equipment").length,
		2,
	);
});

for (const multi of [false, true]) {
	test(`${multi ? "plant" : "single"} unanswered grid phase receives a visible correction target and corrected submit`, async (t) => {
		const app = await equipmentApp(t, {
			projectId: (multi ? "b" : "a").repeat(32),
			hash: "#lp-equipment",
			validatePhase: true,
			inputs: { equipment_setup: { ...savedSetup, grid_phase: null } },
		});
		const searchText = multi
			? "Find equipment for these systems"
			: "Find equipment combinations";
		await untilRun(
			() =>
				app.button("Multiple systems") &&
				!app.button("Multiple systems").disabled,
		);
		if (multi) await act(async () => app.button("Multiple systems").click());
		await untilRun(
			() => app.button(searchText) && !app.button(searchText).disabled,
		);
		await act(async () => app.button(searchText).click());
		const phase = () =>
			[...document.querySelectorAll("select")].find(
				(field) =>
					field.name ===
					(multi
						? "equipment_plant_setup.requirements.grid_phase"
						: "equipment_setup.grid_phase"),
			);
		await until(
			() =>
				phase()?.getAttribute("aria-invalid") === "true" &&
				document.activeElement?.getAttribute("name") === phase()?.name,
		);
		assert.equal(document.activeElement?.getAttribute("name"), phase().name);
		const message = document.getElementById(
			phase().getAttribute("aria-describedby"),
		);
		assert.match(message.textContent, /single-phase or three-phase/);
		assert.equal(
			document.body.textContent.includes("equipment_setup.grid_phase"),
			false,
		);
		const mode = app.fieldSelect("Choose an operating mode");
		await act(async () => {
			mode.value = "backup";
			mode.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
		assert.equal(
			phase().getAttribute("aria-invalid"),
			"true",
			"editing another field must retain this correction",
		);
		await act(async () => {
			phase().value = "3";
			phase().dispatchEvent(new window.Event("change", { bubbles: true }));
		});
		await until(() => phase().getAttribute("aria-invalid") !== "true");
		await act(async () => app.button(searchText).click());
		await untilRun(() => app.runHeading() === "Queued");
		assert.equal(
			app.requests.filter((row) => row.path === "runs/find-equipment").length,
			2,
		);
		assert.equal(
			app.requests.some((row) => row.path === "projects/revise"),
			false,
		);
	});
}

test("energy intake directs an unknown-size customer to equipment without requiring device parameters", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#lp-load",
		inputs: { brief: { ...emptyBrief(), system_scope: "storage_only" } },
	});
	await untilRun(() => app.fieldSelect("Operating goal"));
	assert.ok(!app.fieldSelect("Operating goal").closest("[hidden]"));
	assert.ok(app.button("Choose equipment"));
	assert.ok(
		app.fieldInput("Usable stored energy").closest("[hidden]"),
		"device parameters are outside the initial Operation chapter",
	);
	await act(async () => app.button("01Storage").click());
	assert.ok(!app.fieldInput("Usable stored energy").closest("[hidden]"));
	await act(async () => app.button("03Operation").click());
	await act(async () => {
		const goal = app.fieldSelect("Operating goal");
		goal.value = "backup";
		goal.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () => app.button("Choose equipment").click());
	await untilRun(() => app.button("Find equipment combinations"));
	assert.equal(app.fieldSelect("Choose an operating mode").value, "backup");
	assert.equal(app.requests.length, 0);
});

test("unknown storage size stays optional and is saved as unknown for equipment discovery", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#lp-equipment",
		inputs: {
			brief: { ...emptyBrief(), system_scope: "storage_only" },
			equipment_setup: {
				...emptySetup,
				grid_phase: 3,
				operating_mode: "grid_connected",
			},
		},
	});
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	const known = app.fieldInput("Required usable energy").closest("details");
	assert.ok(known, "known sizing is an optional disclosure");
	assert.equal(known.open, false);
	await act(async () => app.button("Find equipment combinations").click());
	await untilRun(() =>
		app.requests.some((request) => request.path === "runs/find-equipment"),
	);
	const saved = app.requests.find(
		(request) => request.path === "runs/find-equipment",
	).body.inputs;
	assert.equal(saved.equipment_setup.required_usable_kwh, null);
	assert.equal(saved.equipment_setup.required_discharge_ac_kw, null);
	assert.equal(
		app.requests.some((request) => request.path === "projects/revise"),
		false,
	);
	assert.equal(
		app.requests.find((request) => request.path === "runs/find-equipment").body
			.expected_revision,
		1,
	);
	assert.equal(
		document.body.textContent.includes("Enter the search requirements first."),
		false,
	);
});

test("energy demand comparison sends current declarations without a chosen capacity and supports removal and Undo", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { emptyScenario } = await import("../src/domain/energyScenario.ts");
	const scenario = emptyScenario();
	delete scenario.battery_binding;
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#lp-equipment",
		inputs: {
			brief: { ...emptyBrief(), system_scope: "storage_only" },
			energy_scenario: scenario,
			equipment_setup: {
				...emptySetup,
				grid_phase: 3,
				operating_mode: "grid_connected",
			},
		},
	});
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	const toggle = () =>
		[...document.querySelectorAll("label")]
			.find((node) => node.textContent.includes("Compare against energy needs"))
			?.querySelector('input[type="checkbox"]');
	assert.ok(
		toggle(),
		"energy demand comparison is offered for a single AC storage system",
	);
	await act(async () => toggle().click());
	assert.equal(app.button("Find equipment combinations").disabled, true);
	assert.match(
		document.body.textContent,
		/Enter the initial usable capacity, allowed unserved load and source note/,
	);
	assert.equal(app.fieldInput("Initial usable capacity").value, "");
	assert.equal(app.fieldInput("Allowed unserved load").value, "");
	await enter(app.fieldInput("Initial usable capacity"), "50");
	await enter(app.fieldInput("Allowed unserved load"), "0");
	const note = document.querySelector(
		'textarea[name="equipment_demand.source_note"]',
	);
	await enter(note, "Measured starting charge for the outage comparison");
	assert.equal(app.button("Find equipment combinations").disabled, false);
	await enter(app.fieldInput("Initial usable capacity"), "101");
	assert.equal(app.button("Find equipment combinations").disabled, true);
	await enter(app.fieldInput("Initial usable capacity"), "50");
	await act(async () => app.button("Find equipment combinations").click());
	await untilRun(() => app.runHeading() === "Queued");
	const inputs = app.requests.find((row) => row.path === "runs/find-equipment")
		.body.inputs;
	assert.deepEqual(inputs.equipment_demand, {
		schema_version: 1,
		initial_usable_fraction: 0.5,
		max_unserved_load_kwh: 0,
		source_note: "Measured starting charge for the outage comparison",
	});
	assert.equal(inputs.equipment_setup.required_usable_kwh, null);
	assert.equal(inputs.energy_scenario.battery.usable_window_kwh, null);
	assert.deepEqual(inputs.energy_scenario, scenario);
	await act(async () => toggle().click());
	assert.equal(toggle().checked, false);
	await act(async () =>
		document.querySelector('button[aria-label="Undo"]').click(),
	);
	assert.equal(toggle().checked, true);
	assert.equal(app.fieldInput("Initial usable capacity").value, "50");
	await act(async () => toggle().click());
	await act(async () =>
		document
			.querySelector(
				'nav[aria-label="Project sections"] a[href="#lp-equipment"]',
			)
			.click(),
	);
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	await act(async () => app.button("Find equipment combinations").click());
	await untilRun(
		() =>
			app.requests.filter((row) => row.path === "runs/find-equipment")
				.length === 2,
	);
	const withoutDemand = app.requests.filter(
		(row) => row.path === "runs/find-equipment",
	)[1].body.inputs;
	assert.equal(Object.hasOwn(withoutDemand, "equipment_demand"), false);
	assert.deepEqual(withoutDemand.energy_scenario, scenario);
});

test("multiple systems discover from current named demand without a prepared hardware plan", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "8".repeat(32),
		hash: "#lp-equipment",
		inputs: {
			equipment_setup: { ...savedSetup, application: "commercial" },
			equipment_demand: {
				schema_version: 1,
				initial_usable_fraction: 0.5,
				max_unserved_load_kwh: 0,
				source_note: "Starting charge for single-system comparison",
			},
		},
	});
	await untilRun(
		() =>
			app.button("Multiple systems") &&
			!app.button("Multiple systems").disabled,
	);
	await act(async () => app.button("Multiple systems").click());
	await untilRun(
		() =>
			app.button("Find equipment for these systems") &&
			!app.button("Find equipment for these systems").disabled,
	);
	assert.equal(app.button("Prepare multi-system plan"), undefined);
	await act(async () => app.button("Find equipment for these systems").click());
	await untilRun(() => app.runHeading() === "Queued");
	const request = app.requests.find(
		(row) => row.path === "runs/find-equipment",
	);
	assert.equal(request.body.expected_revision, 1);
	assert.equal(request.body.inputs.equipment_plant_setup.units.length, 2);
	assert.equal(Object.hasOwn(request.body.inputs, "equipment_demand"), false);
	assert.equal(
		request.body.inputs.equipment_plant_setup.units[0].inputs.equipment_setup
			.application,
		"commercial",
	);
	assert.equal("equipment_plant_requirements" in request.body.inputs, false);
	assert.equal(
		app.requests.some((row) => row.path === "projects/revise"),
		false,
	);
});

test("switching to PV without storage clears the hidden demand declaration and Undo restores it", async (t) => {
	const demand = {
		schema_version: 1,
		initial_usable_fraction: 0.5,
		max_unserved_load_kwh: 0,
		source_note: "Measured charge",
	};
	const app = await equipmentApp(t, {
		projectId: "8".repeat(32),
		hash: "#lp-equipment",
		inputs: { equipment_setup: savedSetup, equipment_demand: demand },
	});
	await untilRun(() => app.button("Save project"));
	const plannedSystem = [...document.querySelectorAll("label")]
		.find((node) => node.textContent.includes("Planned system"))
		.querySelector("select");
	await act(async () => {
		plannedSystem.value = "pv_only";
		plannedSystem.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () => app.button("Save project").click());
	await untilRun(() =>
		app.requests.some((row) => row.path === "projects/revise"),
	);
	assert.equal(
		Object.hasOwn(
			app.requests.find((row) => row.path === "projects/revise").body.inputs,
			"equipment_demand",
		),
		false,
	);
	await act(async () =>
		document.querySelector('button[aria-label="Undo"]').click(),
	);
	await act(async () => app.button("Save project").click());
	await untilRun(
		() =>
			app.requests.filter((row) => row.path === "projects/revise").length === 2,
	);
	assert.deepEqual(
		app.requests.filter((row) => row.path === "projects/revise")[1].body.inputs
			.equipment_demand,
		demand,
	);
});

test("an unconfirmed discovery retains its original request for explicit retry", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "7".repeat(32),
		hash: "#lp-equipment",
		rejectFind: true,
		inputs: {
			equipment_setup: {
				...emptySetup,
				grid_phase: 3,
				operating_mode: "grid_connected",
			},
		},
	});
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	await act(async () => app.button("Find equipment combinations").click());
	await untilRun(() => app.button("Retry original calculation request"));
	assert.deepEqual(
		app.requests.map((request) => request.path),
		["runs/find-equipment"],
	);
	assert.equal(app.button("Find equipment combinations").disabled, true);
});

test("storage-only equipment keeps known kW/kWh requirements without PV fields in single and multiple systems", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#lp-equipment",
		inputs: {
			brief: { ...emptyBrief(), system_scope: "storage_only" },
			equipment_setup: { ...savedSetup, pv_dc_kw: 0 },
			equipment_requirements: { ...savedRequirements, pv_dc_kw: 0 },
		},
	});
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	assert.equal(app.fieldInput("PV array"), undefined);
	assert.equal(app.fieldInput("Required usable energy").value, "61.4");
	await act(async () => app.button("Multiple systems").click());
	await until(() => app.button("Add system"));
	assert.equal(app.fieldInput("Total PV nameplate rating"), undefined);
	assert.equal(app.fieldInput("Total required usable energy").value, "61.4");
	await act(async () => app.button("Add system").click());
	assert.equal(
		[...document.querySelectorAll("button")].filter(
			(b) => b.textContent === "Remove system",
		).length,
		3,
	);
});

test("equipment search keeps the declared application and shows results without a manual refresh", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		inputs: {
			equipment_setup: savedSetup,
			equipment_requirements: {
				...savedRequirements,
				application: "commercial",
			},
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
		node.textContent.includes("Linker ESS 5K + Linker Battery HV"),
	);
	assert.ok(option, "expected the found combination to be listed");
	assert.match(option.textContent, /Usable battery capacity: 80 kWh/);
	assert.doesNotMatch(option.textContent, /100 kWh/);
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

test("adopting a combination retains its report reference when default procurement was stored as null", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#lp-equipment",
		inputs: {
			equipment_setup: { ...savedSetup, equipment_use: null },
			equipment_requirements: savedRequirements,
		},
	});
	await untilRun(
		() =>
			app.button("Find equipment combinations") &&
			!app.button("Find equipment combinations").disabled,
	);
	await act(async () => app.button("Find equipment combinations").click());
	await untilRun(() => app.runHeading() === "Queued");
	app.setServerRun("succeeded");
	await untilRun(
		() =>
			app.button("Use this combination in the project") &&
			!app.button("Use this combination in the project").disabled,
	);
	await act(async () =>
		app.button("Use this combination in the project").click(),
	);
	await untilRun(() => app.fieldInput("Usable stored energy")?.value === "80");
	assert.equal(window.location.hash, "#lp-calculations");
	assert.equal(
		new URL(window.location.href).searchParams.get("energy_view"),
		"scenario",
	);
	assert.ok(app.button("03Operation").getAttribute("aria-current") === "step");
	await act(async () => app.button("01Storage").click());
	assert.ok(
		!app.fieldInput("Usable stored energy").closest("[hidden]"),
		"adopted storage parameters are in the active chapter",
	);
	await act(async () => app.button("Save project").click());
	await untilRun(() =>
		app.requests.some((request) => request.path === "projects/revise"),
	);
	const saved = app.requests
		.filter((request) => request.path === "projects/revise")
		.at(-1).body.inputs;
	assert.equal(saved.equipment_candidate?.candidate_id, "c".repeat(64));
	assert.equal(saved.equipment_selection.equipment_use, null);
	assert.equal(saved.equipment_setup.application, "commercial");
	assert.equal("application" in saved.equipment_selection, false);
});

for (const changedInput of ["efficiency", "system scope"]) {
	test(`energy-qualified adoption preserves frozen inventory and rejects changed ${changedInput}`, async (t) => {
		const { emptyScenario } = await import("../src/domain/energyScenario.ts");
		const scenario = emptyScenario();
		scenario.battery.usable_window_kwh = 12;
		const app = await equipmentApp(t, {
			projectId: "1".repeat(32),
			hash: "#lp-equipment",
			inputs: {
				equipment_setup: savedSetup,
				energy_scenario: scenario,
				equipment_demand: {
					schema_version: 1,
					initial_usable_fraction: 0.5,
					max_unserved_load_kwh: 0,
					source_note: "Frozen measured starting charge",
				},
			},
			demandCandidate: {
				status: "satisfied",
				reason: "target_met",
				equipment: null,
				metrics: {
					unserved_load_kwh: 0,
					maximum_interval_average_import_kw: 4,
					stored_initial: { pv_kwh: 3, grid_kwh: 7, initial_unknown_kwh: 11 },
				},
			},
		});
		await untilRun(
			() =>
				app.button("Find equipment combinations") &&
				!app.button("Find equipment combinations").disabled,
		);
		await act(async () => app.button("Find equipment combinations").click());
		await untilRun(() => app.runHeading() === "Queued");
		app.setServerRun("succeeded");
		await untilRun(
			() =>
				app.button("Use this combination in the project") &&
				!app.button("Use this combination in the project").disabled,
		);
		await act(async () =>
			document
				.querySelector(
					'nav[aria-label="Project sections"] a[href="#lp-calculations"]',
				)
				.click(),
		);
		await act(async () => app.button("Scenario settings").click());
		await act(async () => app.button("01Storage").click());
		if (changedInput === "efficiency") {
			await enter(app.fieldInput("Charging efficiency"), "80");
		} else {
			const plannedSystem = [...document.querySelectorAll("label")]
				.find((node) => node.textContent.includes("Planned system"))
				.querySelector("select");
			await act(async () => {
				plannedSystem.value = "storage_only";
				plannedSystem.dispatchEvent(
					new window.Event("change", { bubbles: true }),
				);
			});
		}
		await act(async () => app.button("Saved calculations").click());
		await untilRun(
			() =>
				app.button("Use this combination in the project") &&
				!app.button("Use this combination in the project").disabled,
		);
		await act(async () =>
			app.button("Use this combination in the project").click(),
		);
		await until(() =>
			document.body.textContent.includes(
				"The project inputs have changed since this comparison. Run the equipment search again before using its energy assumptions.",
			),
		);
		assert.equal(app.fieldInput("Usable stored energy").value, "12");
		if (changedInput === "efficiency")
			assert.equal(app.fieldInput("Charging efficiency").value, "80");
		await act(async () =>
			document.querySelector('button[aria-label="Undo"]').click(),
		);
		await act(async () => app.button("Saved calculations").click());
		await untilRun(
			() =>
				app.button("Use this combination in the project") &&
				!app.button("Use this combination in the project").disabled,
		);
		await act(async () =>
			app.button("Use this combination in the project").click(),
		);
		assert.equal(
			app.fieldInput("Usable stored energy")?.value,
			"80",
			"energy-qualified capacity replaces the old manual capacity",
		);
		await act(async () => app.button("Save project").click());
		await untilRun(() =>
			app.requests.some((row) => row.path === "projects/revise"),
		);
		const adopted = app.requests
			.filter((row) => row.path === "projects/revise")
			.at(-1).body.inputs;
		assert.equal(adopted.energy_scenario.battery.usable_window_kwh, 80);
		assert.deepEqual(adopted.energy_scenario.initial_inventory, {
			pv_kwh: 3,
			grid_kwh: 7,
			initial_unknown_kwh: 11,
			source_note: "Frozen measured starting charge",
		});
	});
}

test("explicit unknown setup fields stay unknown after reopen beside legacy demand", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "9".repeat(32),
		inputs: {
			// An authored null must not display an older prepared value.
			equipment_setup: emptySetup,
			equipment_requirements: savedRequirements,
		},
		hash: "#lp-equipment",
	});
	await untilRun(() => app.button("Find equipment combinations"));
	await untilRun(() => app.fieldInput("Required usable energy"));
	assert.equal(app.fieldInput("PV array").value, "");
	assert.equal(app.fieldInput("Required usable energy").value, "");
	assert.equal(
		app.fieldInput("Required continuous AC discharge power").value,
		"",
	);
	assert.equal(app.fieldSelect("Choose an operating mode").value, "");
	assert.equal(app.fieldSelect("Grid connection").value, "");
	assert.equal(app.fieldSelect("Application").value, "commercial");
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
