import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import nativePreparation from "./fixtures/preparation-flow-darwin-arm64.json" with { type: "json" };
import { authoredDiscoveryInputs } from "../src/domain/currentCalculation.ts";
import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import { environmentManager, focusManager } from "@tanstack/react-query";
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
		projectRevision = 1,
		inputs,
		hash,
		guided = false,
		loseSelectionReply = false,
		failFirstReport = false,
		rejectFind = false,
		foreignSelection = false,
		selectionGate = null,
		searchGate = null,
		reviseGate = null,
		readGate = null,
		findRefusal = null,
		pvReference = null,
		selectedPv = null,
		effectivePv = null,
		pvFailure = null,
		legacyInputs = null,
		savedRun = legacyInputs ? makeRun(projectId, "succeeded") : null,
		legacyUnavailable = false,
	},
) {
	const fixture = setupDom();
	const priorIndexedDB = Object.getOwnPropertyDescriptor(
		globalThis,
		"indexedDB",
	);
	t.after(() => {
		environmentManager.setIsServer(() => typeof window === "undefined");
		focusManager.setFocused(undefined);
		if (priorIndexedDB)
			Object.defineProperty(globalThis, "indexedDB", priorIndexedDB);
		else delete globalThis.indexedDB;
	});
	// jsdom loads after module evaluation, so query-core's module-level isServer
	// const stays true and would disable refetchInterval scheduling entirely.
	environmentManager.setIsServer(() => false);
	globalThis.indexedDB = new IDBFactory();
	window.history.replaceState(
		null,
		"",
		`/workspace/?project=${projectId}${guided ? "&guided=inquiry" : ""}${hash}`,
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
	const { readPlantDraft } = await import("../src/domain/equipmentPlant.ts");
	const { compilePlantSearch } = await import("../src/domain/plantSearch.ts");
	const { ApiError } = await import("../src/data/protocol.ts");
	const brief = { ...emptyBrief(), system_scope: "new_pv_storage" };
	brief.annual_load.kwh = 10;
	const project = {
		id: projectId,
		title: "Equipment lifecycle fixture",
		revision: projectRevision,
		input_sha256: "2".repeat(64),
		inputs: { brief, ...inputs },
	};
	const session = makeSession();
	const requests = [];
	const reads = [];
	let frozenInputs = legacyInputs;
	let comparisonUnavailable = legacyUnavailable;
	let findAttempts = 0;
	let lostReceipt = null;
	let lostSelection = null;
	let reportRun = null;
	let reportAttempts = 0;
	const revisions = new Map([[project.revision, structuredClone(project)]]);
	let serverRun = savedRun,
		nextScope = session.query_scope,
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
			admittedScope = nextScope;
			return { ...session, query_scope: nextScope };
		},
		async probeScope() {
			return nextScope;
		},
		isCurrentScope(scope) {
			return scope === admittedScope;
		},
		async query(path, body, scope) {
			assert.equal(scope, admittedScope);
			reads.push({ path, body, scope });
			if (path === readGate?.path) await readGate.wait();
			if (path === "products/current") return catalog();
			if (path === "assets/read" && body.asset_id === selectedPv?.id)
				return structuredClone(selectedPv);
			if (path === "projects/runs")
				return {
					items: serverRun ? [runPageItem(serverRun)] : [],
					next: null,
				};
			if (path === "runs/read") {
				assert.equal(
					body.run_id,
					(body.run_id === reportRun?.id ? reportRun : serverRun)?.id,
				);
				return structuredClone(
					body.run_id === reportRun?.id ? reportRun : serverRun,
				);
			}
			if (path === "runs/inputs") {
				assert.equal(body.project_id, projectId);
				assert.equal(body.run_id, serverRun.id);
				if (selectionGate) await selectionGate.promise;
				if (comparisonUnavailable)
					throw new ApiError(503, "version_unavailable");
				return {
					schema_version: 1,
					project_id: foreignSelection ? "0".repeat(32) : projectId,
					run_id: serverRun.id,
					manifest_sha256: serverRun.manifest_sha256,
					inputs: structuredClone(frozenInputs),
				};
			}
			if (path === "equipment/candidates/read") {
				const candidate = serverRun.result.search.candidates[0];
				assert.equal(body.run_id, serverRun.id);
				assert.equal(body.candidate_id, candidate.id);
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
			if (path === "projects/read") {
				assert.equal(body.project_id, projectId);
				if (scope !== session.query_scope) throw new ApiError(404, "not_found");
				return structuredClone(
					body.revision == null ? project : revisions.get(body.revision),
				);
			}
			throw new ApiError(404, "not_found");
		},
		async send(path, body, scope) {
			assert.equal(scope, admittedScope);
			const command = JSON.parse(body);
			requests.push({ path, body: command });
			assert.equal(command.project_id, projectId);
			if (path === "runs/find-equipment" && lostReceipt) {
				assert.equal(body, lostReceipt.body);
				return structuredClone(lostReceipt.receipt);
			}
			if (path === "projects/revise" && lostSelection) {
				assert.equal(body, lostSelection.body);
				return structuredClone(lostSelection.project);
			}
			assert.equal(command.expected_revision, project.revision);
			if (path === "projects/revise") {
				if (reviseGate) await reviseGate.promise;
				project.inputs = structuredClone(command.inputs);
				project.revision += 1;
				project.input_sha256 = "8".repeat(64);
				revisions.set(project.revision, structuredClone(project));
				if (loseSelectionReply) {
					lostSelection = { body, project: structuredClone(project) };
					throw new ApiError(502, "network_error");
				}
				return structuredClone(project);
			}
			if (path === "runs/report") {
				reportRun = makeRun(
					projectId,
					++reportAttempts === 1 && failFirstReport ? "failed" : "queued",
					project.revision,
					project.input_sha256,
					"planning_report_v1",
				);
				reportRun.id = (reportAttempts === 1 ? "8" : "9").repeat(32);
				return structuredClone(reportRun);
			}
			if (path === "runs/find-equipment") {
				if (++findAttempts === 1 && findRefusal)
					throw new ApiError(422, "invalid_input", null, null, findRefusal);
				if (searchGate) await searchGate.promise;
				project.inputs = authoredDiscoveryInputs(command.inputs);
				frozenInputs = structuredClone(project.inputs);
				project.revision += 1;
				project.input_sha256 = "8".repeat(64);
				revisions.set(project.revision, structuredClone(project));
				serverRun = makeRun(
					projectId,
					"queued",
					project.revision,
					project.input_sha256,
					SEARCH_TASK,
				);
				const receipt = {
					schema_version: 1,
					project: structuredClone(project),
					run: structuredClone(serverRun),
				};
				if (rejectFind || (findAttempts === 1 && pvFailure === "receipt")) {
					lostReceipt = { body, receipt };
					throw new ApiError(503, "request_failed");
				}
				return receipt;
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
				(node.getAttribute("aria-label") === text ||
					node.textContent.trim() === text) &&
				!node.closest("[hidden]") &&
				node.getAttribute("aria-hidden") !== "true",
		);
	const field = (label, tag) =>
		[...document.querySelectorAll("label")]
			.find(
				(node) =>
					node.querySelector("span")?.textContent.trim().startsWith(label) &&
					!node.closest("[hidden]"),
			)
			?.querySelector(tag);
	const fieldInput = (label) => field(label, "input");
	const fieldSelect = (label) => field(label, "select");
	async function updateSelect(label, value) {
		const select = fieldSelect(label);
		assert.ok(select, `Expected ${label} select`);
		await act(async () => {
			select.value = value;
			select.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	async function step(label) {
		const find = (name) =>
			[
				...document.querySelectorAll(
					".sc-project-navigation button,.sc-refinement-tabs button",
				),
			].find((node) => node.textContent.replace(/^\d+/, "").trim() === name);
		async function activate(name) {
			await untilRun(() => find(name)?.matches(":enabled"));
			await act(async () => find(name).click());
		}
		if (
			!find(label) &&
			["Roof & PV", "Energy profile & CSV", "Matched equipment"].includes(label)
		) {
			await activate("Fine-tune (optional)");
		}
		await activate(label);
	}

	return {
		async switchScope() {
			nextScope = "9".repeat(64);
			await act(async () => window.dispatchEvent(new window.Event("focus")));
			await until(
				() =>
					admittedScope === nextScope &&
					!document.body.textContent.includes(project.title),
			);
		},
		recoverLegacyInputs() {
			comparisonUnavailable = false;
		},
		project,
		requests,
		reads,
		step,
		updateSelect,
		fieldInput,
		fieldSelect,
		button,
		pending: () =>
			document
				.querySelector("main")
				?.textContent.includes("Finding equipment for your project"),
		setServerRun(state) {
			const previous = serverRun;
			serverRun = makeRun(
				projectId,
				state,
				previous.revision,
				previous.manifest.input_sha256,
				previous.manifest.context.parameters.kind,
			);
			if (state === "failed")
				serverRun.error = { code: "weather_provider_unavailable" };
			if (state === "succeeded" && pvReference) {
				const asset = structuredClone(pvReference.result.prepared_asset);
				asset.metadata.derived_from_revision = serverRun.revision;
				serverRun.result.prepared_asset = asset;
			}
			if (
				state === "succeeded" &&
				effectivePv !== null &&
				!frozenInputs.equipment_plant_setup
			) {
				frozenInputs.equipment_setup.pv_dc_kw = effectivePv;
				serverRun.result.search.candidates[0].selection.pv_dc_kw = effectivePv;
			}
			if (state === "succeeded" && frozenInputs.equipment_plant_setup) {
				const search = serverRun.result.search;
				const draft = readPlantDraft(frozenInputs);
				const backup = frozenInputs.backup_demand;
				if (backup) {
					draft.requirements = {
						...draft.requirements,
						operating_mode: "backup",
					};
				}
				if (effectivePv !== null) {
					draft.requirements = { ...draft.requirements, pv_dc_kw: effectivePv };
					frozenInputs.equipment_plant_setup.requirements.pv_dc_kw =
						effectivePv;
				}
				const plan = compilePlantSearch(draft);
				if (effectivePv !== null)
					frozenInputs.equipment_plant_requirements = plan;
				search.coverage = {
					template: "declared_plant_one_external_assembly_per_converter",
					gaps: {},
					plan,
				};
				const { selection, ...candidate } = search.candidates[0];
				search.candidates = [
					{
						...candidate,
						plant: {
							schema_version: 1,
							requirements: plan.requirements,
							units: plan.units.map(({ id, name, requirements }) => {
								const { application: _application, ...demand } = requirements;
								return { id, name, selection: { ...selection, ...demand } };
							}),
							parallel_groups: [],
						},
					},
				];
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

for (const pvFailure of [null, "provider", "receipt"]) {
	const description =
		pvFailure === "receipt"
			? "resumes the acknowledged earlier request"
			: pvFailure === "provider"
				? "allows site and orientation corrections before retry"
				: "continues through one comparison to a system option";
	test(`known PV ${description}`, async (t) => {
		const { emptyScenario } = await import("../src/domain/energyScenario.ts");
		const scenario = emptyScenario();
		const app = await equipmentApp(t, {
			projectId: knownPv.project.id,
			hash: "#sc-energy",
			pvReference: knownPv.run,
			effectivePv: 6.4,
			pvFailure,
			inputs: {
				...knownPv.project.inputs,
				equipment_setup: { ...savedSetup, pv_dc_kw: null },
				profile_selections: {
					schema_version: 1,
					selected: { gross_load: "e".repeat(32) },
				},
				energy_scenario: {
					...scenario,
					controller: "self_consumption_with_reserve_v1",
					schedule: [
						{
							...scenario.schedule[0],
							mode: "connected",
							pv_enabled: true,
							start_utc: "2019-12-31T23:00:00Z",
							end_utc: "2020-12-31T23:00:00Z",
						},
					],
				},
			},
		});
		await compare(app);
		if (pvFailure === "provider") {
			await untilRun(app.pending);
			await act(async () => app.setServerRun("failed"));
			await untilRun(() =>
				document.body.textContent.includes(
					"PVGIS could not estimate generation",
				),
			);
			await app.step("Roof & PV");
			const latitude = app.fieldInput("Latitude");
			assert.equal(latitude.value, "52.12567");
			await enter(latitude, "52.1");
			await enter(app.fieldInput("Azimuth"), "180");
			await act(async () => app.button("Continue with energy use").click());
			await compare(app);
		} else if (pvFailure === "receipt") {
			const check = () => app.button("Check previous request");
			await untilRun(() => check() && !check().disabled);
			await act(async () => check().click());
		}
		await untilRun(() => app.serverRunId() !== null);
		await act(async () => app.setServerRun("succeeded"));
		await untilRun(() => document.body.textContent.includes("ESS 5K"));
		assert.deepEqual(
			app.requests.map(({ path }) => path),
			pvFailure
				? ["runs/find-equipment", "runs/find-equipment"]
				: ["runs/find-equipment"],
		);
		if (pvFailure === "receipt")
			assert.deepEqual(app.requests[0].body, app.requests[1].body);
		if (pvFailure === "provider") {
			assert.notEqual(app.requests[0].body.key, app.requests[1].body.key);
			assert.equal(
				app.requests[1].body.expected_revision,
				app.requests[0].body.expected_revision + 1,
			);
		}
		const { inputs } = app.requests.at(-1).body;
		assert.equal(inputs.profile_selections.selected.pv_available_ac, undefined);
		assert.equal(inputs.profile_selections.selected.gross_load, "e".repeat(32));
		assert.equal(
			inputs.energy_scenario.schedule[0].start_utc,
			"2019-12-31T23:00:00Z",
		);
		if (pvFailure === "provider") {
			assert.equal(inputs.brief.site.latitude, 52.1);
			assert.equal(
				inputs.pvgis_reference.arrays[0].azimuth_north_clockwise_deg,
				180,
			);
		}
	});
}

async function compare(app) {
	await untilRun(() => app.button("Compare systems")?.matches(":enabled"));
	await act(async () => app.button("Compare systems").click());
}
async function chooseGoal(app, goal = "self") {
	await until(() => app.fieldSelect("Purpose"));
	await app.updateSelect("Purpose", goal);
}
for (const waitingForHistory of [true, false]) {
	test(`project navigation confirms the edited revision before preliminary comparison (history pending: ${waitingForHistory})`, async (t) => {
		const historyGate = deferred(),
			reviseGate = deferred();
		const app = await equipmentApp(t, {
			projectId: "4".repeat(32),
			hash: "#sc-project",
			reviseGate,
			inputs: { equipment_setup: { ...emptySetup, required_usable_kwh: 24 } },
			readGate: waitingForHistory
				? { path: "projects/runs", wait: () => historyGate.promise }
				: null,
		});
		const field = () => document.querySelector('input[name="location_label"]');
		await until(field);
		await enter(field(), "North quay");
		await app.step("Matched equipment");
		await act(async () => historyGate.resolve());
		await untilRun(() =>
			app.requests.some(({ path }) => path === "projects/revise"),
		);
		assert.equal(document.querySelector(".sc-direction-comparison"), null);
		await act(async () => reviseGate.resolve());
		await untilRun(() => document.querySelector(".sc-direction-comparison"));
		assert.equal(app.project.inputs.brief.site.location_label, "North quay");
		assert.equal(app.project.inputs.equipment_setup.required_usable_kwh, 24);
		assert.equal(location.hash, "#sc-preliminary-options");
		assert.deepEqual(
			app.requests.map(({ path }) => path),
			["projects/revise"],
		);
	});
}

for (const state of ["succeeded", "queued"])
	test(`System opens preliminary comparison for incomplete backup inputs after a ${state} search`, async (t) => {
		const id = "c".repeat(32);
		const app = await equipmentApp(t, {
			projectId: id,
			hash: "#sc-energy",
			inputs: { equipment_setup: savedSetup },
			savedRun: makeRun(id, state),
		});
		await chooseGoal(app, "backup");
		await app.step("Matched equipment");
		await untilRun(() => document.querySelector(".sc-direction-comparison"));
		assert.equal(app.button("Use this configuration"), undefined);
		assert.equal(app.project.inputs.backup_demand.duration_hours, null);
		assert.equal(searchRequests(app).length, 0);
	});

for (const entry of ["navigation", "direct"])
	for (const changed of [true, false])
		test(`${entry} System ${changed ? "refreshes" : "reuses"} an older search after reading its frozen settings`, async (t) => {
			const id = "9".repeat(32);
			const { emptyBrief } = await import("../src/domain/brief.ts");
			const brief = { ...emptyBrief(), system_scope: "new_pv_storage" };
			const original = { brief, equipment_setup: savedSetup };
			const app = await equipmentApp(t, {
				projectId: id,
				projectRevision: 2,
				hash: entry === "direct" ? "#sc-system" : "#sc-project",
				inputs: changed
					? {
							...original,
							equipment_setup: { ...savedSetup, inverter_product_id: 101 },
						}
					: original,
				savedRun: makeRun(id, "succeeded", 1),
				legacyInputs: original,
				legacyUnavailable: true,
			});
			if (entry === "navigation") {
				await untilRun(() => app.fieldSelect("Planned system"));
				await app.step("Matched equipment");
			}
			await untilRun(() => app.button("Try again"));
			assert.equal(app.button("Use this configuration"), undefined);
			app.recoverLegacyInputs();
			await act(async () => app.button("Try again").click());
			if (changed) {
				await untilRun(() => searchRequests(app).length === 1);
				assert.equal(searchRequests(app)[0].body.expected_revision, 2);
				assert.equal(app.button("Use this configuration"), undefined);
			} else {
				await untilRun(() => app.button("Use this configuration"));
				assert.deepEqual(app.requests, []);
			}
		});

test("Solar opens System using the edited array capacity rather than a previous result", async (t) => {
	const id = "e".repeat(32);
	const app = await equipmentApp(t, {
		projectId: id,
		hash: "#sc-solar",
		inputs: { equipment_setup: savedSetup },
		savedRun: makeRun(id, "succeeded"),
	});
	const field = () => app.fieldInput("Solar capacity (kWp)");
	await untilRun(() =>
		document.querySelector('[aria-label="Use module details"]'),
	);
	const option = document.querySelector('[aria-label="Use module details"]');
	if (option.getAttribute("aria-pressed") !== "true")
		await act(async () => option.click());
	await untilRun(field);
	await enter(field(), "13.7");
	await app.step("Matched equipment");
	await untilRun(() => searchRequests(app).length === 1);
	assert.equal(app.button("Use this configuration"), undefined);
	assert.ok(
		JSON.stringify(searchRequests(app)[0].body.inputs).includes("13.7"),
	);
});

test("a saved roof goes from Project through PVGIS generation, System and Review", async (t) => {
	const roof = nativePreparation.pvgis_reference_project;
	const app = await equipmentApp(t, {
		projectId: roof.id,
		hash: "#sc-project",
		pvReference: nativePreparation.pvgis_reference_run,
		effectivePv: 9.2,
		inputs: {
			...roof.inputs,
			equipment_setup: { ...savedSetup, pv_dc_kw: null },
		},
	});
	await untilRun(() => app.button("Continue with solar")?.matches(":enabled"));
	await act(async () => app.button("Continue with solar").click());
	assert.equal(location.hash, "#sc-solar");
	assert.equal(app.fieldInput("Calendar year").value, "2020");
	assert.match(
		document.querySelector(".sc-solar-total").textContent,
		/20 placed modules · 9.2 kWp/,
	);
	await act(async () => app.button("Continue with energy use").click());
	assert.equal(location.hash, "#sc-energy");
	await chooseGoal(app);
	await compare(app);
	await untilRun(app.pending);
	assert.equal(location.hash, "#sc-system");
	assert.deepEqual(
		app.requests.map(({ path }) => path),
		["runs/find-equipment"],
	);
	const search = app.requests[0].body;
	assert.equal(search.inputs.equipment_setup.pv_dc_kw, null);
	assert.equal(
		search.inputs.profile_selections?.selected.pv_available_ac,
		undefined,
	);
	await act(async () => app.setServerRun("succeeded"));
	await untilRun(() =>
		app.button("Use this configuration")?.matches(":enabled"),
	);
	await act(async () => app.button("Use this configuration").click());
	await untilRun(() => app.button("Review the proposal")?.matches(":enabled"));
	await act(async () => app.button("Review the proposal").click());
	assert.equal(location.hash, "#sc-review");
	assert.ok(document.querySelector(".sc-review"));
	await untilRun(() =>
		app.button("Generate project report")?.matches(":enabled"),
	);
	await act(async () => app.button("Generate project report").click());
	await untilRun(() => app.requests.some(({ path }) => path === "runs/report"));
	assert.equal(app.requests.at(-1).body.options.pv_run_id, app.serverRunId());
	await app.step("Roof & PV");
	await untilRun(() => app.button("Open roof layout")?.matches(":enabled"));
	await act(async () => app.button("Open roof layout").click());
	await act(async () =>
		document
			.querySelector(".sc-roof-editor .sc-panel-shape")
			.dispatchEvent(new window.MouseEvent("click", { bubbles: true })),
	);
	await act(async () => app.button("Remove selected").click());
	await app.step("Matched equipment");
	assert.equal(Boolean(app.button("Selected")), false);
	assert.equal(app.button("Review the proposal").disabled, true);
});

for (const purpose of [
	"pvgis_known_ac_reference_profile_v1",
	"csv_profile_v1",
]) {
	test(`the selected comparison report respects ${purpose}`, async (t) => {
		const selectedPv = { ...knownPv.run.result.prepared_asset, purpose };
		const nextPv = structuredClone(knownPv.run);
		nextPv.result.prepared_asset.id = "1".repeat(32);
		const app = await equipmentApp(t, {
			projectId: knownPv.project.id,
			hash: "#sc-solar",
			selectedPv,
			pvReference: nextPv,
			effectivePv: 6.4,
			inputs: {
				...knownPv.project.inputs,
				equipment_setup: { ...savedSetup, pv_dc_kw: null },
				profile_selections: {
					schema_version: 1,
					selected: { pv_available_ac: selectedPv.id },
				},
			},
		});
		await untilRun(() => app.fieldInput("Roof pitch")?.matches(":enabled"));
		await enter(app.fieldInput("Roof pitch"), "40");
		await act(async () => app.button("Continue with energy use").click());
		await chooseGoal(app);
		await compare(app);
		await untilRun(app.pending);
		assert.equal(
			app.requests[0].body.inputs.pvgis_reference.arrays[0].tilt_deg,
			40,
		);
		await act(async () => app.setServerRun("succeeded"));
		await untilRun(() =>
			app.button("Use this configuration")?.matches(":enabled"),
		);
		await act(async () => app.button("Use this configuration").click());
		await untilRun(() =>
			app.button("Review the proposal")?.matches(":enabled"),
		);
		await act(async () => app.button("Review the proposal").click());
		await untilRun(() =>
			app.button("Generate project report")?.matches(":enabled"),
		);
		await act(async () => app.button("Generate project report").click());
		await untilRun(() =>
			app.requests.some(({ path }) => path === "runs/report"),
		);
		assert.equal(
			app.requests.at(-1).body.options.pv_run_id,
			purpose === "csv_profile_v1" ? null : app.serverRunId(),
		);
		assert.equal(
			app.project.inputs.profile_selections.selected.pv_available_ac,
			selectedPv.id,
		);
	});
}

test("a manually drawn solar-only roof compares its placed capacity without a load profile", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "6".repeat(32),
		hash: "#sc-project",
		effectivePv: 0.92,
		inputs: {
			equipment_setup: { ...savedSetup, pv_dc_kw: null },
			geometry: {
				...(await import("../src/domain/geometryCommands.ts")).emptyGeometry(),
				module_specs:
					nativePreparation.pvgis_reference_project.inputs.geometry
						.module_specs,
			},
		},
	});
	const click = async (label) => {
		await until(() => app.button(label)?.matches(":enabled"));
		await act(async () => app.button(label).click());
	};
	await untilRun(() => app.fieldSelect("Planned system")?.matches(":enabled"));
	await app.updateSelect("Planned system", "pv_only");
	if (app.button("Switch to solar and exclude storage"))
		await click("Switch to solar and exclude storage");
	await click("Continue with solar");
	await click("Place modules on the roof");
	await click("Open roof layout");
	for (const [label, value] of [
		["Width", "8"],
		["Depth", "5"],
		["Pitch", "25"],
		["Azimuth", "180"],
		["Relative roof height", "3"],
		["Origin east / U", "0"],
		["Origin north / V", "0"],
		["Drawing source", "Installer site plan"],
	])
		await enter(app.fieldInput(label), value);
	await act(async () => document.querySelector(".sc-check input").click());
	await click("Add rectangular roof");
	await click("Modules");
	const module =
		nativePreparation.pvgis_reference_project.inputs.geometry.module_specs[0];
	await untilRun(() =>
		app
			.fieldSelect("Panel dimensions for this layout")
			?.querySelector(`option[value="${module.id}"]`),
	);
	await app.updateSelect("Panel dimensions for this layout", module.id);

	for (const [label, value] of [
		["Rows", "1"],
		["Columns", "2"],
		["Module gap", "0.05"],
		["Origin east / U", "1"],
		["Origin north / V", "1"],
	])
		await enter(app.fieldInput(label), value);
	await click("Place module group");
	assert.match(
		document.querySelector(".sc-solar-total").textContent,
		/2 placed modules · 0.92 kWp/,
	);
	await click("Continue with energy use");
	await chooseGoal(app);
	await compare(app);
	await until(
		() =>
			app.pending() ||
			document.querySelector(".sc-configurator > [role=alert]"),
	);
	assert.deepEqual(
		app.requests.map(({ path }) => path),
		["projects/revise", "projects/revise", "runs/find-equipment"],
	);
	const [roofSave, layoutSave, comparison] = app.requests.map(
		({ body }) => body,
	);
	assert.equal(roofSave.inputs.geometry.roofs.length, 1);
	assert.equal(roofSave.inputs.geometry.arrays.length, 0);
	assert.equal(layoutSave.inputs.geometry.arrays.length, 1);
	assert.equal(comparison.expected_revision, layoutSave.expected_revision + 1);
	const inputs = comparison.inputs;
	assert.deepEqual(inputs.geometry, layoutSave.inputs.geometry);
	assert.equal(inputs.equipment_setup.pv_dc_kw, null);
	await act(async () => app.setServerRun("succeeded"));
	await untilRun(() =>
		app.button("Use this configuration")?.matches(":enabled"),
	);
	assert.equal(inputs.profile_selections?.selected.pv_available_ac, undefined);
	assert.equal(inputs.geometry.coordinate_system.anchor, null);
});

const option = () => document.querySelector(".sc-package");
const searchRequests = (app) =>
	app.requests.filter(({ path }) => path === "runs/find-equipment");

for (const multi of [false, true]) {
	test(`${multi ? "multiple systems" : "single system"} requests require phase and preserve named authored demand`, async (t) => {
		const { emptyBrief } = await import("../src/domain/brief.ts");
		const app = await equipmentApp(t, {
			projectId: (multi ? "a" : "b").repeat(32),
			hash: "#sc-project",
			inputs: {
				brief: { ...emptyBrief(), system_scope: "storage_only" },
				equipment_setup: {
					...savedSetup,
					pv_dc_kw: 0,
					grid_phase: null,
					application: "commercial",
				},
				...(multi
					? {
							equipment_demand: {
								schema_version: 1,
								initial_usable_fraction: 0.5,
								max_unserved_load_kwh: 0,
								source_note: "Previous single-system starting charge",
							},
						}
					: {}),
			},
		});
		await untilRun(() =>
			app.button("Continue with storage")?.matches(":enabled"),
		);
		if (multi) {
			await until(() => app.button("Multiple systems")?.matches(":enabled"));
			await act(async () => app.button("Multiple systems").click());
			const names = [...document.querySelectorAll("label")]
				.filter((label) => label.textContent.includes("System name"))
				.map((label) => label.querySelector("input"));
			assert.equal(names.length, 2);
			await enter(names[1], "Workshop");
			await act(async () => app.button("Add system").click());
			assert.equal(
				[...document.querySelectorAll("button")].filter(
					(button) => button.textContent === "Remove system",
				).length,
				3,
			);
		}
		await act(async () => app.button("Continue with storage").click());
		await chooseGoal(app);
		assert.equal(app.fieldSelect("Grid connection").value, "");
		assert.equal(app.button("Compare systems").disabled, true);
		assert.equal(app.fieldInput("Usable storage capacity").value, "61.4");
		assert.equal(app.fieldInput("Continuous discharge power").value, "100");
		assert.equal(app.fieldInput("PV array"), undefined);
		await act(async () => app.button("Compare systems").click());
		assert.equal(app.requests.length, 0);
		await app.updateSelect("Grid connection", "3");
		await compare(app);
		await untilRun(app.pending);
		assert.deepEqual(
			app.requests.map(({ path }) => path),
			["runs/find-equipment"],
		);
		const { expected_revision, inputs } = searchRequests(app)[0].body;
		assert.equal(expected_revision, 1);
		assert.equal(inputs.equipment_plant_requirements, undefined);
		assert.equal(inputs.equipment_demand, undefined);
		const requirements = multi
			? inputs.equipment_plant_setup.requirements
			: inputs.equipment_setup;
		assert.equal(requirements.grid_phase, 3);
		assert.equal(requirements.pv_dc_kw, 0);
		assert.equal(requirements.required_usable_kwh, 61.4);
		assert.equal(requirements.required_discharge_ac_kw, 100);
		if (multi) {
			const units = inputs.equipment_plant_setup.units;
			assert.deepEqual(
				units.map((unit) => unit.name),
				["System 1", "Workshop", "System 3"],
			);
			assert.equal(units[0].inputs.equipment_setup.application, "commercial");
			assert.equal(units[1].inputs.equipment_setup.required_usable_kwh, null);
		} else assert.equal(requirements.application, "commercial");
	});
}

test("commercial backup compares direct demand while leaving device parameters unknown", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const app = await equipmentApp(t, {
		projectId: "1".repeat(32),
		hash: "#sc-energy",
		inputs: {
			brief: {
				...emptyBrief(),
				project_use: "commercial",
				system_scope: "storage_only",
			},
			equipment_setup: { ...emptySetup, grid_phase: 3 },
		},
	});
	await chooseGoal(app, "backup");
	assert.equal(app.button("Compare systems").disabled, true);
	await enter(app.fieldInput("Backup load"), "5");
	await enter(app.fieldInput("Required duration"), "4");
	assert.match(document.body.textContent, /20 kWh/);
	const optional = app.fieldInput("Usable storage capacity").closest("details");
	assert.equal(optional.open, false);
	assert.equal(app.fieldInput("Usable storage capacity").value, "");
	assert.equal(app.fieldInput("Continuous discharge power").value, "");
	assert.doesNotMatch(document.body.textContent, /Commercial storage sizing/);
	await compare(app);
	await untilRun(app.pending);
	const [{ path, body }] = app.requests;
	assert.equal(path, "runs/find-equipment");
	assert.equal(app.requests.length, 1);
	assert.equal(body.expected_revision, 1);
	assert.deepEqual(body.inputs.backup_demand, {
		schema_version: 1,
		load_kw: 5,
		duration_hours: 4,
	});
	assert.equal(body.inputs.equipment_setup.operating_mode, "backup");
	assert.equal(body.inputs.equipment_setup.required_usable_kwh, null);
	assert.equal(body.inputs.equipment_setup.required_discharge_ac_kw, null);
	assert.equal(body.inputs.profile_selections, undefined);
	assert.equal(body.inputs.energy_scenario.battery.usable_window_kwh, null);
});

test("changing the purpose drops backup demand before the next comparison", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "2".repeat(32),
		hash: "#sc-energy",
		inputs: {
			equipment_setup: savedSetup,
			backup_demand: { schema_version: 1, load_kw: 5, duration_hours: 4 },
		},
	});
	await until(() => app.fieldInput("Backup load"));
	assert.equal(app.fieldInput("Backup load").value, "5");
	await app.updateSelect("Purpose", "peak");
	await enter(app.fieldInput("Target grid import limit"), "13");
	await compare(app);
	await untilRun(app.pending);
	const { inputs } = searchRequests(app)[0].body;
	assert.equal(inputs.backup_demand, undefined);
	assert.equal(
		inputs.energy_scenario.controller,
		"peak_shaving_with_reserve_v1",
	);
	assert.equal(inputs.energy_scenario.schedule[0].import_cap_kw, 13);
	assert.equal(inputs.energy_scenario.initial_inventory.grid_kwh, null);
});

test("a pre-mutation refusal leaves comparison editable and a corrected request gets a new key", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "e".repeat(32),
		hash: "#sc-energy",
		inputs: { equipment_setup: savedSetup },
		findRefusal: ["equipment_setup.grid_phase"],
	});
	await chooseGoal(app);
	await compare(app);
	await untilRun(() =>
		document.body.textContent.includes(
			"Review the equipment requirements below",
		),
	);
	assert.equal(app.button("Check previous request"), undefined);
	await app.updateSelect("Grid connection", "1");
	await compare(app);
	await untilRun(app.pending);
	const [first, second] = searchRequests(app).map(({ body }) => body);
	assert.notEqual(first.key, second.key);
	assert.equal(first.expected_revision, second.expected_revision);
	assert.equal(second.inputs.equipment_setup.grid_phase, 1);
	assert.doesNotMatch(document.body.textContent, /equipment_setup\.grid_phase/);
});

test("a lost comparison receipt blocks another comparison and explicitly replays the original request", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "7".repeat(32),
		hash: "#sc-energy",
		inputs: { equipment_setup: savedSetup },
		rejectFind: true,
	});
	await chooseGoal(app);
	await compare(app);
	await untilRun(() =>
		app.button("Check previous request")?.matches(":enabled"),
	);
	assert.equal(searchRequests(app).length, 1);
	assert.equal(app.button("Compare systems").disabled, true);
	await app.step("Matched equipment");
	assert.doesNotMatch(
		document.querySelector("main").textContent,
		/Enter your energy needs/,
	);
	await act(async () => app.button("Check previous request").click());
	await untilRun(app.pending);
	const [original, replayed] = searchRequests(app).map(({ body }) => body);
	assert.deepEqual(replayed, original);
	assert.equal(searchRequests(app).length, 2);
	assert.equal(app.project.revision, 2);
});

test("a comparison dispatches once, polls in the background, and renders partial options", async (t) => {
	const gate = deferred();
	const app = await equipmentApp(t, {
		projectId: "6".repeat(32),
		hash: "#sc-energy",
		inputs: {
			equipment_setup: savedSetup,
			equipment_requirements: savedRequirements,
		},
		searchGate: gate,
	});
	await chooseGoal(app);
	await untilRun(() => app.button("Compare systems")?.matches(":enabled"));
	const submit = app.button("Compare systems");
	await act(async () => {
		submit.click();
		submit.click();
	});
	await until(() => searchRequests(app).length === 1);
	assert.equal(app.button("Compare systems").disabled, true);
	assert.ok(!app.button("Check previous request"));
	assert.doesNotMatch(
		document.body.textContent,
		/Confirm the result of your previous request/,
	);
	assert.ok(
		[...document.querySelectorAll('[role="status"]')].some(
			(node) => node.textContent === "Finding equipment for your project…",
		),
	);
	let prompted = false;
	const observer = new MutationObserver(() => {
		if (app.button("Check previous request")) prompted = true;
	});
	observer.observe(document.body, { childList: true, subtree: true });
	try {
		await act(async () => gate.resolve());
		await untilRun(app.pending);
	} finally {
		observer.disconnect();
	}
	assert.equal(prompted, false);
	assert.equal(window.location.hash, "#sc-system");
	assert.equal(searchRequests(app).length, 1);
	assert.equal(
		searchRequests(app)[0].body.inputs.equipment_setup.application,
		"commercial",
	);
	Object.defineProperty(document, "visibilityState", {
		value: "hidden",
		configurable: true,
	});
	await act(async () => focusManager.setFocused(false));
	try {
		app.setServerRun("succeeded");
		await untilRun(option);
		assert.equal(
			option().querySelector(".sc-option-products").getAttribute("aria-label"),
			"Linker ESS 5K + Linker Battery HV",
		);
		assert.match(option().textContent, /80\s+kWh/);
		assert.doesNotMatch(option().textContent, /100\s+kWh/);
		assert.match(
			document.querySelector("main").textContent,
			/Search incomplete: some configurations remain unchecked/,
		);
		assert.ok(
			app.reads.some(
				({ path, body }) =>
					path === "runs/read" && body.run_id === app.serverRunId(),
			),
		);
	} finally {
		delete document.visibilityState;
		await act(async () => focusManager.setFocused(undefined));
	}
});

test("one guided configuration choice saves it and prepares its report", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "b".repeat(32),
		guided: true,
		hash: "#sc-system",
		inputs: {
			equipment_setup: { ...savedSetup, equipment_use: null },
			equipment_requirements: savedRequirements,
		},
	});
	await untilRun(() => searchRequests(app).length === 1 && app.serverRunId());
	app.setServerRun("succeeded");
	await untilRun(() =>
		app.button("Use this configuration")?.matches(":enabled"),
	);
	await act(async () => app.button("Use this configuration").click());
	await untilRun(() => app.requests.some(({ path }) => path === "runs/report"));
	assert.deepEqual(
		app.requests.map(({ path }) => path),
		["runs/find-equipment", "projects/revise", "runs/report"],
	);
	const saved = app.requests[1].body.inputs.equipment_candidate;
	assert.equal(saved.run_id, app.serverRunId());
	assert.equal(app.requests[2].body.expected_revision, 3);
	assert.equal(window.location.hash, "#sc-review");
});

test("after losing the selection receipt, retrying keeps the same save and opens review", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "b".repeat(32),
		guided: true,
		loseSelectionReply: true,
		hash: "#sc-system",
		inputs: {
			equipment_setup: { ...savedSetup, equipment_use: null },
			equipment_requirements: savedRequirements,
		},
	});
	await untilRun(() => searchRequests(app).length === 1 && app.serverRunId());
	app.setServerRun("succeeded");
	await untilRun(() =>
		app.button("Use this configuration")?.matches(":enabled"),
	);
	await act(async () => app.button("Use this configuration").click());
	await untilRun(() => app.button("Try again")?.matches(":enabled"));
	await act(async () => app.button("Try again").click());
	await untilRun(() => app.requests.some(({ path }) => path === "runs/report"));
	assert.equal(window.location.hash, "#sc-review");
	const saves = app.requests.filter(({ path }) => path === "projects/revise");
	assert.equal(saves.length, 2);
	assert.deepEqual(saves[0].body, saves[1].body);
});

test("a failed guided report can be prepared again without reselecting the proposal", async (t) => {
	const app = await equipmentApp(t, {
		projectId: "b".repeat(32),
		guided: true,
		failFirstReport: true,
		hash: "#sc-system",
		inputs: {
			equipment_setup: { ...savedSetup, equipment_use: null },
			equipment_requirements: savedRequirements,
		},
	});
	await untilRun(() => searchRequests(app).length === 1 && app.serverRunId());
	app.setServerRun("succeeded");
	await untilRun(() =>
		app.button("Use this configuration")?.matches(":enabled"),
	);
	await act(async () => app.button("Use this configuration").click());
	await untilRun(() => app.button("Try again")?.matches(":enabled"));
	await act(async () => app.button("Try again").click());
	await untilRun(
		() =>
			app.requests.filter(({ path }) => path === "runs/report").length === 2,
	);
	assert.equal(window.location.hash, "#sc-review");
	const [first, second] = app.requests.filter(
		({ path }) => path === "runs/report",
	);
	assert.equal(first.body.expected_revision, second.body.expected_revision);
	assert.notEqual(first.body.key, second.body.key);
	assert.equal(
		app.requests.filter(({ path }) => path === "projects/revise").length,
		1,
	);
});

for (const [multi, selection] of [
	[false, "none"],
	[false, "battery"],
	[true, "none"],
	[true, "battery"],
	[true, "backup"],
	[true, "derived PV"],
]) {
	test(`${multi ? "plant" : "single"} ${selection} selection pins the search candidate to the project report`, async (t) => {
		const app = await equipmentApp(t, {
			projectId: (multi ? "d" : "c").repeat(32),
			effectivePv: selection === "derived PV" ? 9.2 : null,
			hash: "#sc-project",
			inputs: {
				equipment_setup: {
					...savedSetup,
					...(selection === "battery" ? { battery_product_id: 201 } : {}),
					equipment_use: null,
				},
				equipment_requirements: savedRequirements,
			},
		});
		await untilRun(() => app.button("Multiple systems")?.matches(":enabled"));
		if (multi) await act(async () => app.button("Multiple systems").click());
		await app.step("Energy profile & CSV");
		await chooseGoal(app, selection === "backup" ? "backup" : "self");
		if (selection === "backup") {
			await enter(app.fieldInput("Backup load"), "5");
			await enter(app.fieldInput("Required duration"), "4");
		}
		await compare(app);
		await untilRun(app.pending);
		app.setServerRun("succeeded");
		await untilRun(() =>
			app.button("Use this configuration")?.matches(":enabled"),
		);
		await act(async () => app.button("Use this configuration").click());
		await untilRun(() => app.button("Selected"));
		assert.equal(app.requests.length, 1);
		await act(async () => app.button("Review the proposal").click());
		await untilRun(() =>
			app.button("Generate project report")?.matches(":enabled"),
		);
		await act(async () => app.button("Generate project report").click());
		await untilRun(() =>
			app.requests.some(({ path }) => path === "runs/report"),
		);
		assert.deepEqual(
			app.requests.map(({ path }) => path),
			["runs/find-equipment", "projects/revise", "runs/report"],
		);
		const saved = app.requests[1].body.inputs;
		assert.deepEqual(saved.equipment_candidate, {
			run_id: app.serverRunId(),
			candidate_id: "c".repeat(64),
			assessment_sha256: "d".repeat(64),
		});
		if (multi) {
			assert.equal(saved.equipment_plant.units.length, 2);
			if (selection === "derived PV")
				assert.equal(saved.equipment_plant.requirements.pv_dc_kw, 9.2);
			assert.equal(
				saved.equipment_plant.units[1].selection.inverter_product_id,
				101,
			);
		} else {
			assert.equal(
				Object.hasOwn(saved.equipment_selection, "equipment_use"),
				false,
			);
			assert.equal(saved.equipment_setup.application, "commercial");
			assert.equal(saved.equipment_selection.application, undefined);
		}
		assert.equal(app.requests[2].body.expected_revision, 3);
		const assertModels = (inputs) => {
			const rows = multi
				? inputs.equipment_plant_setup.units.map(
						(u) => u.inputs.equipment_setup,
					)
				: [inputs.equipment_setup];
			rows.forEach((row, index) =>
				assert.deepEqual(row.comparison_models, {
					inverter_product_id: null,
					battery_product_id:
						selection === "battery" && index === 0 ? 201 : null,
				}),
			);
		};
		assertModels(saved);
		if (selection === "backup") {
			assert.equal(
				saved.equipment_plant.requirements.required_discharge_ac_kw,
				100,
			);
			assert.equal(saved.backup_demand.load_kw, 5);
			assert.equal(
				saved.equipment_plant.units[0].selection.required_discharge_ac_kw,
				100,
			);
		}
		await app.step("Energy profile & CSV");
		await compare(app);
		await untilRun(
			() =>
				app.requests.filter(({ path }) => path === "runs/find-equipment")
					.length === 2,
		);
		const again = app.requests.at(-1).body.inputs;
		assertModels(again);
		assert.deepEqual(again.equipment_candidate, saved.equipment_candidate);
		if (selection === "none") {
			await untilRun(app.pending);
			await app.step("Project & direction");
			const declarations = [
				...document.querySelectorAll("details > summary"),
			].find(
				(summary) => summary.textContent === "Equipment and system arrangement",
			);
			assert.ok(declarations, "Expected equipment and system arrangement");
			if (!declarations.parentElement.open)
				await act(async () => declarations.click());
			await untilRun(() =>
				app
					.fieldSelect("Inverter or integrated storage system")
					?.querySelector('option[value="101"]'),
			);
			assert.equal(
				app.fieldSelect("Inverter or integrated storage system").value,
				"",
			);
			await app.updateSelect("Inverter or integrated storage system", "101");
			await app.step("Energy profile & CSV");
			await compare(app);
			await untilRun(() => searchRequests(app).length === 3);
			const edited = searchRequests(app).at(-1).body.inputs;
			const unit = multi
				? edited.equipment_plant_setup.units[0].inputs
				: edited;
			assert.deepEqual(unit.equipment_setup.comparison_models, {
				inverter_product_id: 101,
				battery_product_id: null,
			});
		}
	});
}

for (const multi of [false, true]) {
	test(`${multi ? "plant" : "single"} legacy equipment edit keeps the other comparison class open`, async (t) => {
		const setup = { ...savedSetup, operating_mode: "grid_connected" };
		const unit = (equipment) => ({
			id: "main",
			name: "Main",
			inputs: { equipment_setup: equipment },
		});
		const declared = (equipment) =>
			multi
				? {
						equipment_plant_setup: {
							schema_version: 1,
							requirements: { ...savedRequirements },
							units: [unit(equipment)],
							parallel_groups: [],
						},
					}
				: { equipment_setup: equipment };
		const legacy = declared(setup);
		const adopted = declared({
			...setup,
			inverter_product_id: 101,
			battery_product_id: 201,
			modules_per_stack: 5,
			parallel_stacks: 2,
		});
		const app = await equipmentApp(t, {
			projectId: (multi ? "d" : "c").repeat(32),
			hash: "#sc-project",
			legacyInputs: legacy,
			inputs: {
				...adopted,
				equipment_candidate: {
					run_id: "7".repeat(32),
					candidate_id: "c".repeat(64),
					assessment_sha256: "d".repeat(64),
				},
			},
		});
		const field = () =>
			app.fieldSelect("Inverter or integrated storage system");
		const details = () =>
			document.querySelector(
				'section[aria-label="System arrangement"] details',
			);
		await untilRun(details);
		if (!details().open)
			await act(async () => details().querySelector("summary").click());
		await untilRun(() => field()?.matches(":enabled"));
		assert.equal(field().value, "");
		await app.updateSelect("Inverter or integrated storage system", "101");
		await app.step("Energy profile & CSV");
		await chooseGoal(app);
		await compare(app);
		await untilRun(() => searchRequests(app).length === 1);
		const inputs = searchRequests(app)[0].body.inputs;
		const equipment = multi
			? inputs.equipment_plant_setup.units[0].inputs.equipment_setup
			: inputs.equipment_setup;
		assert.deepEqual(equipment.comparison_models, {
			inverter_product_id: 101,
			battery_product_id: null,
		});
	});
}

for (const adopted of [true, false]) {
	test(`System waits for ${adopted ? "the adopted comparison" : "project history"} and can retry a failed read`, async (t) => {
		const gate = deferred();
		let fail = true;
		const app = await equipmentApp(t, {
			projectId: "c".repeat(32),
			hash: "#sc-project",
			legacyInputs: adopted ? { equipment_setup: savedSetup } : null,
			inputs: adopted
				? {
						equipment_candidate: {
							run_id: "7".repeat(32),
							candidate_id: "c".repeat(64),
							assessment_sha256: "d".repeat(64),
						},
					}
				: {},
			readGate: {
				path: adopted ? "runs/read" : "projects/runs",
				wait: async () => {
					await gate.promise;
					if (fail) throw new Error("read failed");
				},
			},
		});
		await untilRun(() =>
			document.querySelector('nav[aria-label="Project navigation"]'),
		);
		await app.step("Matched equipment");
		const empty = /Enter your energy needs/;
		assert.doesNotMatch(document.querySelector("main").textContent, empty);
		assert.equal(
			document.querySelector('main [role="status"]').textContent,
			"Reading saved calculation results…",
		);
		await act(async () => gate.resolve());
		await untilRun(() => app.button("Try again"));
		assert.ok(document.querySelector('[role="alert"]'));
		assert.doesNotMatch(document.querySelector("main").textContent, empty);
		fail = false;
		await act(async () => app.button("Try again").click());
		if (adopted) {
			await untilRun(() => app.button("Selected"));
			assert.match(option().textContent, /ESS 5K/);
		} else {
			await untilRun(() => document.querySelector(".sc-direction-comparison"));
			assert.equal(location.hash, "#sc-preliminary-options");
		}
		assert.deepEqual(app.requests, []);
	});
}

test("a retrofit with selected equipment keeps the drawn solar capacity when the comparison has no PV rating", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { default: geometry } = await import(
		"../../../fixtures/planning/geometry-flat.json",
		{ with: { type: "json" } }
	);
	const projectId = "c".repeat(32);
	const run = makeRun(projectId, "succeeded");
	const candidate = run.result.search.candidates[0];
	candidate.selection.pv_dc_kw = null;
	const app = await equipmentApp(t, {
		projectId,
		hash: "#sc-system",
		savedRun: run,
		inputs: {
			brief: { ...emptyBrief(), system_scope: "storage_addition" },
			geometry,
			equipment_setup: {
				...candidate.selection,
				comparison_models: {
					inverter_product_id: null,
					battery_product_id: null,
				},
			},
			equipment_candidate: {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
			},
		},
	});
	await untilRun(() => app.button("Selected"));
	const capacity = [...document.querySelectorAll("dt")].find(
		(label) => label.textContent === "Solar capacity",
	);
	assert.equal(capacity.nextElementSibling.textContent, "2.5 kWp");
});

test("a failed legacy model read still lets the customer save annual electricity use", async (t) => {
	const selected = {
		...savedSetup,
		inverter_product_id: 101,
		battery_product_id: 201,
	};
	const choice = {
		run_id: "7".repeat(32),
		candidate_id: "c".repeat(64),
		assessment_sha256: "d".repeat(64),
	};
	const app = await equipmentApp(t, {
		projectId: "c".repeat(32),
		hash: "#sc-energy",
		legacyInputs: { equipment_setup: savedSetup },
		legacyUnavailable: true,
		inputs: { equipment_setup: selected, equipment_candidate: choice },
	});
	await untilRun(() => app.button("Try again"));
	const annual = app.fieldInput("Annual electricity use");
	assert.ok(annual.matches(":enabled"));
	assert.ok(app.fieldSelect("Grid connection").matches(":disabled"));
	await enter(annual, "42");
	await act(async () => app.button("Save snapshot").click());
	await untilRun(() =>
		app.requests.some(({ path }) => path === "projects/revise"),
	);
	assert.deepEqual(app.requests.at(-1).body.inputs.equipment_candidate, choice);
	assert.deepEqual(app.requests.at(-1).body.inputs.equipment_setup, selected);
	assert.equal(app.requests.at(-1).body.inputs.brief.annual_load.kwh, 42);
	app.recoverLegacyInputs();
	await act(async () => app.button("Try again").click());
	await app.step("Project & direction");
	const details = document.querySelector(
		'section[aria-label="System arrangement"] details',
	);
	if (!details.open)
		await act(async () => details.querySelector("summary").click());
	const inverter = () =>
		app.fieldSelect("Inverter or integrated storage system");
	await untilRun(() => inverter()?.matches(":enabled"));
	assert.equal(inverter().value, "");
});

test("a saved change to model preferences refuses a new current report from the old choice", async (t) => {
	const projectId = "c".repeat(32);
	const selected = makeRun(projectId, "succeeded").result.search.candidates[0]
		.selection;
	const { product_revisions: _revisions, ...hardware } = selected;
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const brief = { ...emptyBrief(), system_scope: "new_pv_storage" };
	const app = await equipmentApp(t, {
		projectId,
		hash: "#sc-review",
		legacyInputs: { equipment_setup: savedSetup, brief },
		inputs: {
			brief,
			equipment_setup: {
				...hardware,
				comparison_models: {
					inverter_product_id: 101,
					battery_product_id: null,
				},
			},
			equipment_selection: selected,
			equipment_candidate: {
				run_id: "7".repeat(32),
				candidate_id: "c".repeat(64),
				assessment_sha256: "d".repeat(64),
			},
		},
	});
	await untilRun(() =>
		app.button("Generate project report")?.matches(":enabled"),
	);
	await act(async () => app.button("Generate project report").click());
	await untilRun(() =>
		document.body.textContent.includes("Compare systems again"),
	);
	assert.deepEqual(app.requests, []);
});

for (const change of [
	"purpose",
	"system scope",
	"single model preference",
	"plant model preference",
	"foreign snapshot",
	"session scope",
]) {
	test(`${change}: a previous equipment result cannot be used for changed inputs`, async (t) => {
		const gate = change === "session scope" ? deferred() : null;
		const app = await equipmentApp(t, {
			projectId: "4".repeat(32),
			hash: change === "plant model preference" ? "#sc-project" : "#sc-energy",
			inputs: { equipment_setup: savedSetup },
			foreignSelection: change === "foreign snapshot",
			selectionGate: gate,
		});
		if (change === "plant model preference") {
			await untilRun(() => app.button("Multiple systems")?.matches(":enabled"));
			await act(async () => app.button("Multiple systems").click());
			await app.step("Energy profile & CSV");
		}
		await chooseGoal(app);
		await compare(app);
		await untilRun(app.pending);
		app.setServerRun("succeeded");
		await untilRun(() =>
			app.button("Use this configuration")?.matches(":enabled"),
		);
		if (change.endsWith("model preference")) {
			await app.step("Project & direction");
			const details = document.querySelector(
				'section[aria-label="System arrangement"] details',
			);
			if (!details.open)
				await act(async () => details.querySelector("summary").click());
			await untilRun(() =>
				app
					.fieldSelect("Inverter or integrated storage system")
					?.matches(":enabled"),
			);
			await app.updateSelect("Inverter or integrated storage system", "101");
			await app.step("Matched equipment");
		} else if (change === "purpose") {
			await app.step("Energy profile & CSV");
			await app.updateSelect("Purpose", "peak");
			await app.step("Matched equipment");
		} else if (change === "system scope") {
			await app.step("Project & direction");
			await app.updateSelect("Planned system", "storage_only");
			await app.step("Matched equipment");
		}
		if (change !== "foreign snapshot" && change !== "session scope") {
			await untilRun(() => searchRequests(app).length === 2);
			assert.equal(
				app.button("Use this configuration"),
				undefined,
				"the earlier options are hidden during recalculation",
			);
			const updated = searchRequests(app)[1].body.inputs;
			if (change === "single model preference")
				assert.equal(updated.equipment_setup.inverter_product_id, 101);
			if (change === "plant model preference")
				assert.equal(
					updated.equipment_plant_setup.units[0].inputs.equipment_setup
						.inverter_product_id,
					101,
				);
			if (change === "system scope")
				assert.equal(updated.brief.system_scope, "storage_only");
			if (change === "purpose")
				assert.ok(
					updated.energy_scenario.schedule.some(
						(period) => period.import_policy === "limited",
					),
				);
			return;
		}
		await act(async () => app.button("Use this configuration").click());
		if (gate) {
			await untilRun(() =>
				app.reads.some(({ path }) => path === "runs/inputs"),
			);
			await app.switchScope();
			await act(async () => gate.resolve());
			assert.equal(app.button("Use this configuration"), undefined);
			assert.equal(app.button("Check previous request"), undefined);
		} else {
			await untilRun(() =>
				document.body.textContent.includes(
					"This configuration could not be selected",
				),
			);
			assert.equal(app.button("Review the proposal").disabled, true);
		}
		assert.equal(app.button("Selected"), undefined);
		assert.deepEqual(
			app.requests.map(({ path }) => path),
			["runs/find-equipment"],
		);
	});
}

for (const authored of [false, true]) {
	test(`${authored ? "explicit nulls override" : "unanswered setup inherits"} historical requirements`, async (t) => {
		const app = await equipmentApp(t, {
			projectId: "5".repeat(32),
			hash: "#sc-energy",
			inputs: {
				equipment_requirements: savedRequirements,
				...(authored ? { equipment_setup: emptySetup } : {}),
			},
		});
		await until(() => app.fieldInput("Usable storage capacity"));
		assert.equal(
			app.fieldInput("Usable storage capacity").value,
			authored ? "" : "61.4",
		);
		assert.equal(
			app.fieldInput("Continuous discharge power").value,
			authored ? "" : "100",
		);
		assert.equal(app.fieldSelect("Grid connection").value, authored ? "" : "3");
		await chooseGoal(app);
		if (authored) await app.updateSelect("Grid connection", "3");
		await compare(app);
		await untilRun(app.pending);
		const { equipment_setup: setup } = searchRequests(app)[0].body.inputs;
		assert.equal(setup.pv_dc_kw, authored ? null : 200);
		assert.equal(setup.required_usable_kwh, authored ? null : 61.4);
		assert.equal(setup.required_discharge_ac_kw, authored ? null : 100);
		assert.equal(setup.application, "commercial");
	});
}
