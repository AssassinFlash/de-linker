import energyFixture from "./fixtures/energy-run.json" with { type: "json" };
import replay from "./fixtures/energy-inputs.json" with { type: "json" };
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import assert from "node:assert/strict";
import test from "node:test";
import { IDBFactory } from "fake-indexeddb";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";

test("a storage project continues from its location directly to energy use", async () => {
	const fixture = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { default: Configurator } =
		await import("../src/components/configurator/Configurator.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const scope = "3".repeat(64);
	const session = {
		kind: "guest",
		query_scope: scope,
		claim_pending: false,
		runtime: {
			limits: {
				max_page_size: 30,
				max_json_depth: 32,
				max_body_bytes: 1000000,
			},
			models: {},
		},
	};
	const brief = {
		...emptyBrief(),
		system_scope: "storage_only",
		project_use: "commercial",
		site: {
			...emptyBrief().site,
			country_code: "DE",
			location_label: "Berlin",
		},
	};
	const project = {
		id: "1".repeat(32),
		title: "Workshop",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: { brief },
	};
	const requests = [];
	const client = {
		isCurrentScope: (s) => s === scope,
		query: async (path) => {
			requests.push(path);
			if (path === "projects/runs") return { items: [], next: null };
			throw new Error(path);
		},
	};
	const store = {
		read: async () => null,
		candidates: async () => [],
		write: async () => {},
	};
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const root = createRoot(fixture.element);
	try {
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						project,
						session,
						client,
						store,
						config: { locale: "en", countries: { DE: "Germany" } },
						recheck() {},
						close() {
							return true;
						},
					}),
				),
			),
		);
		await until(() =>
			fixture.element.textContent.includes("What is the project?"),
		);
		const navigation = fixture.element.querySelector(
			'nav[aria-label="Project navigation"]',
		);
		assert.deepEqual(
			[...navigation.querySelectorAll("button")].map((b) =>
				b.textContent.replace(/^\d+/, ""),
			),
			["Project", "Energy use", "System", "Review & share"],
		);
		const next = [...fixture.element.querySelectorAll("button")].find(
			(b) => b.textContent === "Continue with storage",
		);
		await until(() => !next.disabled);
		await act(async () => next.click());
		await until(() =>
			fixture.element.textContent.includes("What should the system do?"),
		);
		assert.equal(requests.includes("projects/revise"), false);
		assert.equal(
			fixture.element.textContent.includes("Installation routing"),
			false,
		);
	} finally {
		await fixture.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	}
});

for (const scenario of [
	"matching PV",
	"earlier site",
	"current retained inverter",
	"changed retained inverter",
	"matching energy and equipment",
	"changed energy and equipment",
]) {
	test(`report generation handles ${scenario}`, async () => {
		const dom = setupDom();
		globalThis.indexedDB = new IDBFactory();
		window.history.replaceState(
			null,
			"",
			`?project=${knownPv.project.id}#sc-review`,
		);
		const { createRoot } = await import("react-dom/client");
		const { QueryClient, QueryClientProvider } =
			await import("@tanstack/react-query");
		const { default: Configurator } =
			await import("../src/components/configurator/Configurator.tsx");
		const scope = "3".repeat(64);
		const session = {
			kind: "guest",
			query_scope: scope,
			claim_pending: false,
			runtime: {
				limits: {
					max_page_size: 30,
					max_json_depth: 32,
					max_body_bytes: 1000000,
				},
				models: {},
			},
		};
		const project = structuredClone(knownPv.project);
		project.revision++;
		project.input_sha256 = "9".repeat(64);
		project.inputs.brief.project_note = "Updated project description";
		const historical = new Map([[knownPv.project.revision, knownPv.project]]);
		const runs = [knownPv.run];
		const desired = {
			locale: "en",
			energy_run_id: null,
			pv_run_id: knownPv.run.id,
			equipment_run_id: null,
			logo: null,
		};
		if (scenario === "earlier site") {
			project.inputs.brief.site.latitude = 49;
			desired.pv_run_id = null;
		}
		function equipmentRun(task, revision, inputHash, fields) {
			const manifest_sha256 = "4".repeat(64);
			const assets =
				task === "search_woo_equipment_v1"
					? {}
					: { "woo.equipment_inputs": "b".repeat(64) };
			return {
				...knownPv.run,
				id: "4".repeat(32),
				revision,
				manifest_sha256,
				manifest: {
					...knownPv.run.manifest,
					revision,
					input_sha256: inputHash,
					context: {
						assets,
						code_sha256: "a".repeat(64),
						models: { task },
						parameters: { kind: task },
					},
				},
				result: {
					schema: 1,
					kind: task,
					project_id: project.id,
					revision,
					input_sha256: inputHash,
					manifest_sha256,
					runtime_sha256: "a".repeat(64),
					pinned_assets: assets,
					...fields,
				},
			};
		}
		if (scenario.includes("retained inverter")) {
			const existing_system = {
				schema_version: 1,
				name: "West barn inverter",
				inverter_power_kw: 7.5,
				keep_inverter: true,
			};
			project.inputs.existing_system = existing_system;
			const requirements = {
				schema_version: 1,
				grid_phase: 3,
				operating_mode: "grid_connected",
				pv_dc_kw: null,
				required_usable_kwh: 15,
				required_discharge_ac_kw: null,
				application: null,
			};
			const retained = equipmentRun(
				"search_woo_equipment_v1",
				project.revision,
				project.input_sha256,
				{ retained_inverter: { existing_system, requirements } },
			);
			runs.unshift(retained);
			if (scenario.startsWith("current"))
				desired.equipment_run_id = retained.id;
			else {
				project.revision++;
				project.input_sha256 = "8".repeat(64);
				project.inputs.existing_system = {
					...existing_system,
					inverter_power_kw: 8,
				};
			}
		}
		if (scenario.includes("energy and equipment")) {
			project.inputs.equipment_setup = {
				schema_version: 1,
				inverter_product_id: 101,
				battery_product_id: 201,
				modules_per_stack: 1,
				parallel_stacks: 1,
				accessory_product_ids: [],
				grid_phase: 3,
				operating_mode: "grid_connected",
				pv_dc_kw: null,
				required_usable_kwh: null,
				required_discharge_ac_kw: null,
			};
			project.inputs.energy_replay = structuredClone(replay);
			const energy = structuredClone(energyFixture);
			energy.id = "6".repeat(32);
			energy.project_id =
				energy.result.project_id =
				energy.manifest.project_id =
					project.id;
			energy.revision =
				energy.result.revision =
				energy.manifest.revision =
					project.revision;
			energy.manifest.input_sha256 = energy.result.input_sha256 =
				project.input_sha256;
			const check = equipmentRun(
				"qualify_woo_equipment_v1",
				project.revision,
				project.input_sha256,
				{
					assessment: {
						overall_status: "unresolved",
						equipment_status: "unresolved",
						checks: [],
						provisional_bill_of_materials: [],
						selected_products: [],
					},
				},
			);
			runs.unshift(check, energy);
			if (scenario.startsWith("matching")) {
				desired.energy_run_id = energy.id;
				desired.equipment_run_id = check.id;
				desired.pv_run_id = null; // Calculation used a different AC profile.
			} else {
				historical.set(project.revision, structuredClone(project));
				project.revision++;
				project.input_sha256 = "8".repeat(64);
				project.inputs.equipment_setup.inverter_product_id = 102;
			}
		}
		const requests = [];
		const client = {
			isCurrentScope: (s) => s === scope,
			query: async (path, body) => {
				if (path === "projects/runs")
					return {
						items: runs.map((run) => ({
							id: run.id,
							project_id: run.project_id,
							revision: run.revision,
							manifest_sha256: run.manifest_sha256,
							result_sha256: run.result_sha256,
							state: run.state,
							is_current: run.revision === project.revision,
							created_at: 1,
							task_kind: run.result.kind,
						})),
						next: null,
					};
				const found = runs.find((run) => run.id === body.run_id);
				if (path === "runs/read" && found) return found;
				if (path === "runs/inputs" && found)
					return {
						schema_version: 1,
						project_id: found.project_id,
						run_id: found.id,
						manifest_sha256: found.manifest_sha256,
						inputs:
							found.result.kind === "qualify_woo_equipment_v1"
								? {
										...project.inputs,
										equipment_selection: {
											...project.inputs.equipment_setup,
											product_revisions: {
												101: "a".repeat(64),
												201: "b".repeat(64),
											},
										},
									}
								: (historical.get(found.revision) ?? project).inputs,
					};
				if (path === "projects/read" && historical.has(body.revision))
					return historical.get(body.revision);
				throw new Error(path);
			},
			send: async (path, raw) => {
				const command = JSON.parse(raw);
				requests.push([path, command]);
				return {
					id: "e".repeat(32),
					project_id: project.id,
					revision: project.revision,
					manifest_sha256: "e".repeat(64),
					result_sha256: null,
					state: "queued",
					is_current: true,
					result: null,
					error: null,
					manifest: {
						schema: 1,
						project_id: project.id,
						revision: project.revision,
						input_sha256: project.input_sha256,
						context: {
							code_sha256: "f".repeat(64),
							models: { task: "planning_report_v1" },
							assets: {},
							parameters: { kind: "planning_report_v1" },
						},
					},
				};
			},
		};
		const cache = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
		const store = {
			read: async () => null,
			candidates: async () => [],
			write: async () => {},
		};
		const root = createRoot(dom.element);
		try {
			await act(async () =>
				root.render(
					React.createElement(
						QueryClientProvider,
						{ client: cache },
						React.createElement(Configurator, {
							project,
							client,
							session,
							store,
							config: { locale: "en", countries: {} },
							recheck() {},
							close: () => true,
						}),
					),
				),
			);
			const generate = () =>
				[...dom.element.querySelectorAll("button")].find(
					(button) => button.textContent === "Generate project report",
				);
			await until(() => generate() && !generate().disabled);
			await act(async () => generate().click());
			await until(() => requests.length > 0);
			assert.equal(requests.length, 1);
			assert.equal(requests[0][0], "runs/report");
			assert.equal(requests[0][1].expected_revision, project.revision);
			assert.deepEqual(requests[0][1].options, desired);
		} finally {
			await dom.dispose(root);
			cache.clear();
			delete globalThis.indexedDB;
		}
	});
}
