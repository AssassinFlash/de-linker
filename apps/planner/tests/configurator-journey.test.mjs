import energyFixture from "./fixtures/energy-run.json" with { type: "json" };
import replay from "./fixtures/energy-inputs.json" with { type: "json" };
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import flatRoof from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import assert from "node:assert/strict";
import test from "node:test";
import { IDBFactory } from "fake-indexeddb";
import React, { act } from "react";
import { enter, setupDom, until } from "./dom-fixture.mjs";
import preparation from "./fixtures/index.ts";

test("the configuration sidebar counts included roof modules when no PV capacity was entered or selected", async (t) => {
	const dom = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { default: Configurator } =
		await import("../src/components/configurator/Configurator.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const scope = "3".repeat(64);
	const cache = new QueryClient();
	const root = createRoot(dom.element);
	const project = {
		id: "1".repeat(32),
		title: "Roof capacity",
		revision: 1,
		input_sha256: "2".repeat(64),
	};
	const brief = { ...emptyBrief(), system_scope: "new_pv_storage" };
	const session = {
		kind: "guest",
		query_scope: scope,
		claim_pending: false,
		runtime: { limits: { max_page_size: 30 }, models: {} },
	};
	const client = {
		isCurrentScope: (value) => value === scope,
		query: async (path) => {
			assert.equal(path, "projects/runs");
			return { items: [], next: null };
		},
	};
	const store = {
		read: async () => null,
		candidates: async () => [],
		write: async () => {},
	};
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	});
	const capacity = () =>
		[...dom.element.querySelectorAll("dt")].find(
			(item) => item.textContent === "Solar capacity",
		)?.nextElementSibling?.textContent;
	const allExcluded = {
		...flatRoof,
		arrays: flatRoof.arrays.map((array) => ({
			...array,
			excluded_slots: ["0:0", "0:1", "0:2", "1:0", "1:1", "1:2"],
		})),
	};
	for (const [inputs, expected] of [
		[{ geometry: flatRoof }, "2.5 kWp"],
		[{ geometry: allExcluded }, "—"],
		[{}, "—"],
		[
			{
				geometry: flatRoof,
				pvgis_reference: knownPv.project.inputs.pvgis_reference,
			},
			"6.4 kWp",
		],
	]) {
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						key: expected + Boolean(inputs.geometry),
						project: { ...project, inputs: { brief, ...inputs } },
						session,
						client,
						store,
						config: { locale: "en", countries: {} },
						recheck: () => assert.fail("Unexpected identity change"),
						close: () => true,
					}),
				),
			),
		);
		await until(() => capacity() !== undefined);
		assert.equal(capacity(), expected);
	}
});

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

test("PV comparison submits one command and reopens on the saved equipment search", async () => {
	const dom = setupDom();
	globalThis.indexedDB = new IDBFactory();
	window.location.hash = "sc-energy";
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { default: Configurator } =
		await import("../src/components/configurator/Configurator.tsx");
	const { emptyScenario } = await import("../src/domain/energyScenario.ts");
	const { equipmentDraft } = await import("../src/domain/equipment.ts");
	const scope = "3".repeat(64),
		kind = "search_woo_equipment_v1";
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
	let project = structuredClone(knownPv.project),
		run = null;
	const scenario = emptyScenario();
	project.inputs.energy_scenario = {
		...scenario,
		controller: "self_consumption_with_reserve_v1",
		schedule: [
			{
				...scenario.schedule[0],
				mode: "connected",
				pv_enabled: true,
				start_utc: "2020-06-01T12:00:00Z",
				end_utc: "2020-06-01T14:00:00Z",
			},
		],
	};
	project.inputs.equipment_setup = {
		...equipmentDraft({}),
		grid_phase: 3,
		operating_mode: "grid_connected",
	};
	const queries = [],
		commands = [];
	const client = {
		isCurrentScope: (value) => value === scope,
		query: async (path, body) => {
			queries.push(path);
			if (path === "projects/runs") {
				if (!run) return { items: [], next: null };
				const { manifest, result, error, ...summary } = run;
				return {
					items: [{ ...summary, task_kind: kind, created_at: 1 }],
					next: null,
				};
			}
			assert.equal(path, "runs/read");
			assert.equal(body.run_id, run.id);
			return run;
		},
		send: async (path, raw) => {
			commands.push(path);
			assert.equal(path, "runs/find-equipment");
			const command = JSON.parse(raw);
			assert.deepEqual(
				command.inputs.pvgis_reference,
				project.inputs.pvgis_reference,
			);
			assert.equal(command.expected_revision, project.revision);
			project = {
				...project,
				inputs: command.inputs,
				revision: project.revision + 1,
			};
			run = {
				...knownPv.run,
				revision: project.revision,
				state: "queued",
				result: null,
				result_sha256: null,
				manifest: {
					...knownPv.run.manifest,
					revision: project.revision,
					input_sha256: project.input_sha256,
					context: {
						...knownPv.run.manifest.context,
						models: { task: kind },
						parameters: { kind },
						assets: { "woo.equipment_inputs": "a".repeat(64) },
					},
				},
			};
			return { schema_version: 1, project, run };
		},
	};
	const store = {
		read: async () => null,
		candidates: async () => [],
		write: async () => {},
	};
	let root = createRoot(dom.element),
		cache = new QueryClient();
	const render = () =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						project,
						session,
						client,
						store,
						config: { locale: "en", countries: {} },
						recheck: () => assert.fail("Unexpected identity change"),
						close: () => true,
					}),
				),
			),
		);
	try {
		await render();
		const compare = () =>
			[...dom.element.querySelectorAll("button")].find(
				(b) => b.textContent === "Compare systems",
			);
		await until(() => compare() && !compare().disabled);
		await act(async () => compare().click());
		await until(() => window.location.hash === "#sc-system");
		await act(async () => root.unmount());
		cache.clear();
		run = {
			...run,
			state: "succeeded",
			result_sha256: "c".repeat(64),
			result: {
				schema: 1,
				kind,
				project_id: project.id,
				revision: run.revision,
				input_sha256: project.input_sha256,
				manifest_sha256: run.manifest_sha256,
				runtime_sha256: run.manifest.context.code_sha256,
				pinned_assets: run.manifest.context.assets,
				prepared_asset: knownPv.run.result.prepared_asset,
				search: {
					completion: "exhausted_supported_domain",
					work_used: 1,
					work_budget: 100,
					qualified_count: 0,
					ranking: "not_performed_before_qualification",
					products: [],
					candidates: [],
					coverage: {
						template: "one_converter_one_external_battery_assembly",
						gaps: {},
					},
				},
			},
		};
		root = createRoot(dom.element);
		cache = new QueryClient();
		await render();
		await until(() =>
			dom.element.textContent.includes("A system for this project"),
		);
		assert.deepEqual(commands, ["runs/find-equipment"]);
		assert.ok(
			queries.every((path) => path === "projects/runs" || path === "runs/read"),
		);
	} finally {
		await dom.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	}
});

test("Review & share asks Genie and downloads the chosen report while inquiry stays with the current report", async () => {
	const dom = setupDom(),
		scope = "3".repeat(64),
		{ createRoot } = await import("react-dom/client"),
		{ QueryClient, QueryClientProvider } =
			await import("@tanstack/react-query"),
		{ default: Configurator } =
			await import("../src/components/configurator/Configurator.tsx"),
		{ emptyBrief } = await import("../src/domain/brief.ts"),
		current = structuredClone(preparation.geometric_pv.report_run),
		earlier = structuredClone(preparation.direct_beam.report_run);
	for (const record of [
		earlier,
		earlier.manifest,
		earlier.result,
		earlier.result.prepared_asset,
		earlier.result.prepared_attachments.bill_of_materials_csv,
	]) {
		record.project_id = current.project_id;
	}
	for (const run of [current, earlier])
		run.result.has_report_only_handoff = true;
	const project = {
		id: current.project_id,
		title: "Workshop",
		revision: current.revision,
		input_sha256: current.manifest.input_sha256,
		inputs: { brief: emptyBrief() },
	};
	const deepLink = `?project=${project.id}&run=${earlier.id}#lp-calculations`;
	window.history.replaceState(null, "", deepLink);
	globalThis.indexedDB = new IDBFactory();
	const summary = ({
		id,
		project_id,
		revision,
		manifest_sha256,
		result_sha256,
		state,
		is_current,
	}) => ({
		id,
		project_id,
		revision,
		manifest_sha256,
		result_sha256,
		state,
		is_current,
		created_at: 1700000000 + revision,
		task_kind: "planning_report_v1",
	});
	const currentSummary = summary(current);
	const newestCalculation = {
		...currentSummary,
		id: "a".repeat(32),
		created_at: currentSummary.created_at + 1,
		task_kind: "qualify_woo_equipment_v1",
	};
	const cursorFor = ({ id, created_at }) => ({
		before_id: id,
		before_created_at: created_at,
	});
	const downloads = [],
		requests = [],
		filenames = [];
	let activeScope = scope;
	let wrongProject = false;
	const client = {
		isCurrentScope: (s) => s === activeScope,
		async query(path, body) {
			requests.push([path, body]);
			if (path === "projects/runs") {
				if (body.before_id === null)
					return {
						items: [newestCalculation],
						next: cursorFor(newestCalculation),
					};
				if (body.before_id === newestCalculation.id) {
					assert.equal(body.before_created_at, newestCalculation.created_at);
					return { items: [currentSummary], next: cursorFor(currentSummary) };
				}
				assert.equal(body.before_id, current.id);
				assert.equal(body.before_created_at, currentSummary.created_at);
				return { items: [summary(earlier)], next: null };
			}
			if (path === "runs/read") {
				if (body.run_id === earlier.id)
					return wrongProject ? preparation.direct_beam.report_run : earlier;
				return body.run_id === current.id ? current : undefined;
			}
			if (path === "draft/preview") return new Promise(() => {});
			throw new Error(path);
		},
		async reportPdf(projectId, assetId, queryScope, _signal, sha) {
			downloads.push(["pdf", projectId, assetId, queryScope, sha]);
			return new Blob(["pdf"]);
		},
		async reportCsv(projectId, assetId, queryScope, sha) {
			downloads.push(["csv", projectId, assetId, queryScope, sha]);
			return new Blob(["csv"]);
		},
	};
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const root = createRoot(dom.element);
	window.HTMLAnchorElement.prototype.click = function () {
		filenames.push(this.download);
	};
	const button = (text, within = dom.element) =>
		[...within.querySelectorAll("button")].find((node) =>
			node.textContent.trim().startsWith(text),
		);
	const { useSiteIntegration } =
		await import("../src/data/useSiteIntegration.ts");
	document.querySelector("header").innerHTML =
		'<a hreflang="de" lang="de" href="/de/konfigurator/">Deutsch</a><a hreflang="en" lang="en" href="/solution-configurator/">English</a>';
	function Workspace({ locale }) {
		useSiteIntegration(project.id);
		return React.createElement(Configurator, {
			project,
			client,
			session: {
				kind: "guest",
				query_scope: scope,
				nonce: "guest-proof",
				claim_pending: false,
				runtime: {
					limits: {
						max_page_size: 1,
						max_json_depth: 32,
						max_body_bytes: 1000000,
					},
					models: {},
				},
			},
			store: {
				read: async () => null,
				candidates: async () => [],
				write: async () => {},
			},
			config: { locale, countries: {} },
			recheck() {},
			close: () => true,
		});
	}
	const render = (locale, key = locale) =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Workspace, { locale, key }),
				),
			),
		);
	try {
		await render("en");
		await until(() => {
			const history = dom.element.querySelector(
				'section[aria-label="Calculation history"]',
			);
			return history?.textContent.includes("Project planning report");
		});
		assert.deepEqual(
			requests
				.filter(([path]) => path === "projects/runs")
				.map(([, body]) => body.before_id),
			[null],
		);
		await act(async () => button("Earlier calculations").click());
		await until(() => button("Attach report to inquiry"));
		const context = (opener) => {
			let detail;
			const receive = (event) => (detail = event.detail);
			window.addEventListener("linker-genie-planning-context", receive);
			window.dispatchEvent(
				new CustomEvent("linker-genie-planning-context-request", {
					detail: { opener },
				}),
			);
			window.removeEventListener("linker-genie-planning-context", receive);
			return detail;
		};
		const assertContext = ({ page, plannerNonce }, revision, runIds) => {
			assert.equal(page.planning_project_id, project.id);
			assert.equal(page.planning_revision, revision);
			assert.deepEqual(page.planning_run_ids, runIds);
			assert.equal(page.planning_unsaved, false);
			assert.equal(plannerNonce, "guest-proof");
		};
		const ask = async (within, revision, runIds) => {
			const opener = button("Ask Genie", within);
			assert.ok(opener?.hasAttribute("data-linker-genie-open"));
			let openingContext;
			const capture = (event) => {
				if (event.target.closest("[data-linker-genie-open]") === opener)
					openingContext = context(opener);
			};
			// The already loaded dock asks for context from the document click capture.
			document.addEventListener("click", capture, true);
			try {
				await act(async () => opener.click());
			} finally {
				document.removeEventListener("click", capture, true);
			}
			assertContext(openingContext, revision, runIds);
			assertContext(context(), revision, runIds);
		};
		const history = () =>
			dom.element.querySelector('section[aria-label="Calculation history"]');
		const languageLink = (lang) =>
			document.querySelector(`header a[hreflang="${lang}"]`);
		await ask(history(), 2, [earlier.id]);
		assert.equal(
			document.getElementById("lp-calculations").contains(history()),
			true,
		);
		assert.equal(
			dom.element.textContent.includes("Projektplanungsbericht"),
			false,
		);
		activeScope = "4".repeat(64);
		assert.equal(context(), null);
		activeScope = scope;
		window.history.replaceState(null, "", `?project=${"f".repeat(32)}`);
		assert.equal(context(), null);
		window.history.replaceState(null, "", deepLink);
		assert.equal(
			new URL(languageLink("de").href).searchParams.get("run"),
			earlier.id,
		);
		window.history.replaceState(null, "", languageLink("de").href);
		await render("de");
		await until(() => button("Download PDF", history()));
		await ask(history(), 2, [earlier.id]);
		assert.equal(history().querySelector('input[type="file"]'), null);
		await act(async () => button("Download PDF", history()).click());
		await act(async () =>
			button("Download bill of materials (CSV)", history()).click(),
		);
		assert.match(
			button("Attach report to inquiry").closest(".sc-draft-transfer")
				.textContent,
			/Your inquiry uses the current report \(revision 3\)\./,
		);
		await act(async () => button("Attach report to inquiry").click());
		assert.equal(
			requests.find(([path]) => path === "draft/preview")[1].report_run_id,
			current.id,
		);

		await act(async () => button("Close", history()).click());
		assert.equal(
			new URL(languageLink("en").href).searchParams.has("run"),
			false,
		);
		assert.ok(dom.element.textContent.includes("Projektplanungsbericht"));
		await ask(button("Download PDF").closest("section"), 3, [current.id]);
		await act(async () => button("Download PDF").click());
		await act(async () => button("Earlier calculations").click());
		await until(() => button("Revision 2"));
		await act(async () => button("Revision 2").click());
		assert.equal(button("Revision 2").getAttribute("aria-pressed"), "true");
		assert.equal(
			new URL(languageLink("en").href).searchParams.get("run"),
			earlier.id,
		);
		await ask(history(), 2, [earlier.id]);
		await ask(dom.element.querySelector(".sc-project-heading"), 3, []);
		await act(async () => button("Revision 2").click());
		assert.equal(
			new URL(languageLink("en").href).searchParams.has("run"),
			false,
		);
		const earlierPdf = earlier.result.prepared_asset,
			earlierCsv = earlier.result.prepared_attachments.bill_of_materials_csv,
			currentPdf = current.result.prepared_asset;
		assert.deepEqual(downloads, [
			["pdf", project.id, earlierPdf.id, scope, earlierPdf.content_sha256],
			["csv", project.id, earlierCsv.id, scope, earlierCsv.content_sha256],
			["pdf", project.id, currentPdf.id, scope, currentPdf.content_sha256],
		]);
		assert.deepEqual(filenames, [
			`linker-planning-${project.id}-r2-en.pdf`,
			`linker-planning-${project.id}-r2-en.csv`,
			`linker-planning-${project.id}-r3-de.pdf`,
		]);
		await act(async () => root.render(null));
		cache.clear();
		wrongProject = true;
		window.history.replaceState(null, "", deepLink);
		await render("en");
		await until(() => button("Refresh calculation status", history()));
		assert.equal(button("Download PDF"), undefined);
		assert.equal(button("Ask Genie", history()), undefined);
		await act(async () => button("Close", history()).click());
		await act(async () => button("Earlier calculations").click());
		await until(() => button("Download PDF"));
	} finally {
		await dom.dispose(root);
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
	"automatic wiring check",
	"pending wiring check",
	"completed wiring check",
	"missing wiring evidence",
	"edited peak target with a saved candidate",
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
		const editPeak = scenario === "edited peak target with a saved candidate";
		if (editPeak) window.location.hash = "sc-energy";
		let project = structuredClone(knownPv.project);
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
						equipment_status: "satisfied",
						country_assessment: { status: "unresolved" },
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
		let wiringCheck;
		let queuedCheck;
		if (scenario.includes("wiring")) {
			project.inputs.equipment_setup = {
				schema_version: 1,
				inverter_product_id: 101,
				battery_product_id: null,
				modules_per_stack: null,
				parallel_stacks: null,
				accessory_product_ids: [],
				grid_phase: 3,
				operating_mode: "grid_connected",
				pv_dc_kw: 6.4,
				required_usable_kwh: null,
				required_discharge_ac_kw: null,
			};
			project.inputs.pv_string_plan = { schema_version: 1, strings: [] };
			wiringCheck = equipmentRun(
				"qualify_woo_equipment_v1",
				project.revision,
				project.input_sha256,
				{
					assessment: {
						overall_status: "unresolved",
						equipment_status: "satisfied",
						country_assessment: { status: "unresolved" },
						checks: [],
						provisional_bill_of_materials: [],
						selected_products: [],
						...(scenario !== "missing wiring evidence" && {
							pv_electrical: {
								schema_version: 1,
								method: "woo_layout_electrical_v2",
								strings: [],
							},
						}),
					},
				},
			);
			queuedCheck = {
				...wiringCheck,
				state: "queued",
				result: null,
				result_sha256: null,
			};
			if (scenario === "pending wiring check") runs.unshift(queuedCheck);
			if (scenario === "completed wiring check") runs.unshift(wiringCheck);
			desired.equipment_run_id = wiringCheck.id;
		}
		if (editPeak) {
			const { emptyScenario } = await import("../src/domain/energyScenario.ts");
			const { equipmentDraft } = await import("../src/domain/equipment.ts");
			const draft = emptyScenario();
			project.inputs.energy_scenario = {
				...draft,
				controller: "peak_shaving_with_reserve_v1",
				schedule: [
					{
						...draft.schedule[0],
						mode: "connected",
						import_policy: "limited",
						import_cap_kw: 10,
					},
				],
			};
			project.inputs.equipment_setup = {
				...equipmentDraft({}),
				inverter_product_id: 101,
				comparison_models: {
					inverter_product_id: null,
					battery_product_id: null,
				},
			};
			project.inputs.equipment_candidate = {
				run_id: "4".repeat(32),
				candidate_id: "5".repeat(32),
				assessment_sha256: "6".repeat(64),
			};
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
							task_kind: run.manifest.context.parameters.kind,
						})),
						next: null,
					};
				const found = runs.find((run) => run.id === body.run_id);
				if (path === "runs/read" && body.run_id === wiringCheck?.id)
					return wiringCheck;
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
				if (path === "projects/revise" && editPeak) {
					project = {
						...project,
						revision: project.revision + 1,
						inputs: command.inputs,
						input_sha256: "d".repeat(64),
					};
					return project;
				}
				if (path === "runs/check-equipment" && wiringCheck) {
					assert.deepEqual(command.inputs, project.inputs);
					runs.unshift(wiringCheck);
					return {
						schema_version: 1,
						project,
						run: queuedCheck,
					};
				}
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
			if (editPeak) {
				const peak = () =>
					[...dom.element.querySelectorAll("label")]
						.find((label) =>
							label.textContent.includes("Target grid import limit"),
						)
						?.querySelector("input");
				const button = (text) =>
					[...dom.element.querySelectorAll("button")].find(
						(item) => item.textContent === text,
					);
				await until(() => peak()?.value === "10");
				await enter(peak(), "8");
				await act(async () => button("Undo").click());
				await until(() => peak()?.value === "10");
				await enter(peak(), "9");
				await act(async () => button("Save snapshot").click());
				await until(() =>
					requests.some(([path]) => path === "projects/revise"),
				);
				const savedInputs = requests[0][1].inputs;
				assert.equal(savedInputs.energy_scenario.schedule[0].import_cap_kw, 9);
				assert.equal(savedInputs.equipment_setup.inverter_product_id, 101);
				assert.equal(savedInputs.equipment_candidate, undefined);
				return;
			}
			const generate = () =>
				[...dom.element.querySelectorAll("button")].find(
					(button) => button.textContent === "Generate project report",
				);
			await until(() => generate() && !generate().disabled);
			await act(async () => generate().click());
			if (scenario === "missing wiring evidence") {
				await until(() =>
					dom.element.textContent.includes(
						"The wiring check could not finish.",
					),
				);
				assert.deepEqual(
					requests.map(([path]) => path),
					["runs/check-equipment"],
				);
				return;
			}
			await until(() => requests.some(([path]) => path === "runs/report"));
			assert.deepEqual(
				requests.map(([path]) => path),
				scenario === "automatic wiring check"
					? ["runs/check-equipment", "runs/report"]
					: ["runs/report"],
			);
			const report = requests.at(-1)[1];
			assert.equal(report.expected_revision, project.revision);
			assert.deepEqual(report.options, desired);
		} finally {
			await dom.dispose(root);
			cache.clear();
			delete globalThis.indexedDB;
		}
	});
}
