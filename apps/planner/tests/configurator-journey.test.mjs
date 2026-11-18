import energyFixture from "./fixtures/energy-run.json" with { type: "json" };
import replay from "./fixtures/energy-inputs.json" with { type: "json" };
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import flatRoof from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import assert from "node:assert/strict";
import test from "node:test";
import { IDBFactory } from "fake-indexeddb";
import React, { act } from "react";
import { deferred, enter, setupDom, until } from "./dom-fixture.mjs";
import preparation from "./fixtures/index.ts";

test("draft confirmation shows the frozen phase conflict and still lets the customer continue", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { DraftTransferButton } =
		await import("../src/components/energy/DraftTransferButton.tsx");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const origin = window.location.origin;
	const run = { id: "b".repeat(32), project_id: "a".repeat(32), revision: 3 };
	const applied = [];
	let phaseConflict = { actual: 1, required: 3 };
	let reportOnly = false;
	let phaseConflicts;
	const client = {
		origin,
		isCurrentScope: () => true,
		async query(path, command) {
			assert.equal(path, "draft/preview");
			assert.equal(command.report_run_id, run.id);
			return {
				schema_version: 1,
				project_id: run.project_id,
				report_run_id: run.id,
				revision: run.revision,
				handoff_id: "c".repeat(32),
				draft_sha256: "d".repeat(64),
				snapshot_sha256: "e".repeat(64),
				already_present: false,
				draft_urls: { en: `${origin}/draft/`, de: `${origin}/de/entwurf/` },
				...(reportOnly
					? { changes: [], report_only: true }
					: {
							changes: [
								{
									product_id: 1,
									label: "GoodWe inverter",
									before: 0,
									after: 1,
								},
							],
						}),
				...(phaseConflict === undefined
					? {}
					: { phase_conflict: phaseConflict }),
				...(phaseConflicts === undefined
					? {}
					: { phase_conflicts: phaseConflicts }),
			};
		},
	};
	const operations = {
		records: [],
		async start(...args) {
			applied.push(args);
		},
	};
	const render = (key, locale = "en") =>
		act(async () =>
			root.render(
				React.createElement(DraftTransferButton, {
					key,
					run,
					client,
					operations,
					scope: "owned",
					current: true,
					blocked: false,
					locale,
					reportOnly,
					recheck() {},
				}),
			),
		);
	const button = (text) =>
		[...dom.element.querySelectorAll("button")].find(
			(item) => item.textContent.trim() === text,
		);
	await render("conflict");
	await act(async () =>
		button("Add selected products to solution draft").click(),
	);
	assert.match(
		dom.element.textContent,
		/Grid phase mismatch\. Selected inverter: 1\. Project requirement: 3\. You can send an inquiry to discuss the configuration\./,
	);
	await act(async () => button("Confirm changes").click());
	assert.deepEqual(applied, [
		[
			"draft/apply",
			{
				expected_revision: 3,
				report_run_id: run.id,
				expected_draft_sha256: "d".repeat(64),
			},
		],
	]);

	phaseConflict = undefined;
	await render("without-conflict");
	await act(async () =>
		button("Add selected products to solution draft").click(),
	);
	assert.doesNotMatch(dom.element.textContent, /Grid phase mismatch/);
	assert.equal(button("Confirm changes").disabled, false);

	const { default: catalog } = await import(
		"../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json",
		{ with: { type: "json" } }
	);
	window.wp.i18n.__ = (message) =>
		catalog.locale_data.messages[message]?.[0] ?? message;
	phaseConflict = { actual: 1, required: 3 };
	await render("formal-german", "de");
	const add = button("Ausgewählte Produkte zum Lösungsentwurf hinzufügen");
	assert.ok(add);
	await act(async () => add.click());
	assert.match(
		dom.element.textContent,
		/Der ausgewählte Wechselrichter hat 1, das Projekt erfordert 3\. Senden Sie uns bei Bedarf eine Anfrage zur Konfiguration\./,
	);
	assert.equal(button("Änderungen bestätigen").disabled, false);
	phaseConflict = undefined;
	phaseConflicts = [
		{ unit: "Depot · East", actual: 1, required: 3 },
		{ unit: "West", actual: 1, required: 3 },
	];
	await render("multi-inverter-de", "de");
	await act(async () =>
		button("Ausgewählte Produkte zum Lösungsentwurf hinzufügen").click(),
	);
	for (const unit of ["Depot · East", "West"])
		assert.ok(
			dom.element.textContent.includes(
				`${unit}: Die Phasenanzahl passt nicht zum Projekt.`,
			),
		);

	window.wp.i18n.__ = (message) => message;
	reportOnly = true;
	await render("report-only");
	await act(async () => button("Attach report to inquiry").click());
	assert.match(dom.element.textContent, /Depot · East: Grid phase mismatch/);
	assert.match(dom.element.textContent, /West: Grid phase mismatch/);
	await act(async () => button("Attach report to inquiry").click());
	assert.equal(applied.length, 2);
});

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
	await act(async () =>
		[...dom.element.querySelectorAll(".sc-nav button")]
			.find((b) => b.textContent.includes("Review"))
			.click(),
	);
	assert.match(
		dom.element.querySelector('main section[aria-label="Project summary"]')
			.textContent,
		/6.4 kWp/,
	);
	assert.ok(
		![...dom.element.querySelectorAll("main button")].some((b) =>
			b.textContent.includes("solution draft"),
		),
	);
});

test("a storage project includes location and energy demand on one stage", async () => {
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
		inputs: { brief, geometry: flatRoof },
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
			["Project", "Choose a solution", "Review & inquire"],
		);
		await until(() => fixture.element.querySelector("#sc-energy select"));
		assert.equal(requests.includes("projects/revise"), false);
		assert.doesNotMatch(fixture.element.textContent, /PV strings and inputs/);
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
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					products: [],
					pv_modules: [],
					figure_projection_version: 2,
					compatibility_origin: "woocommerce",
				};
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
		const latitude = [...dom.element.querySelectorAll("label")]
			.find(
				(field) =>
					field.querySelector("span")?.textContent.trim() === "Latitude",
			)
			.querySelector("input");
		await enter(latitude, "1.234,5");
		assert.equal(latitude.value, "1.234,5");
		assert.equal(compare().disabled, true);
		await act(async () =>
			latitude.dispatchEvent(
				new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
			),
		);
		assert.equal(compare().disabled, false);
		await act(async () => compare().click());
		await until(() => window.location.hash === "#sc-system");
		await act(async () => root.unmount());
		cache.clear();
		queries.length = 0;
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
			queries.join(", "),
		);
	} finally {
		await dom.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	}
});

test("Review & inquire asks Genie and downloads the chosen report while the native inquiry uses the current report", async () => {
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
	const saving = deferred();
	const origin = window.location.origin;
	const handoff = {
		schema_version: 1,
		project_id: project.id,
		report_run_id: current.id,
		revision: current.revision,
		handoff_id: "c".repeat(32),
		snapshot_sha256: "e".repeat(64),
		report_only: true,
		draft_urls: { en: `${origin}/draft/`, de: `${origin}/de/entwurf/` },
	};
	const posts = [];
	window.HTMLFormElement.prototype.submit = function () {
		posts.push(Object.fromEntries(new window.FormData(this)));
	};
	const client = {
		origin,
		isCurrentScope: (s) => s === activeScope,
		async send(path, raw) {
			const command = JSON.parse(raw);
			requests.push([path, command]);
			if (path === "draft/apply")
				return {
					...handoff,
					intent_sha256: "b".repeat(64),
					items: [],
					inquiry_cart_hash: "",
					inquiry_draft_sha256: "f".repeat(64),
				};
			assert.equal(path, "projects/revise");
			await saving.promise;
			return {
				...project,
				revision: project.revision + 1,
				input_sha256: "d".repeat(64),
				inputs: command.inputs,
			};
		},
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
			if (path === "draft/inquiry-preview")
				return {
					...handoff,
					already_present: false,
					changes: [],
					draft_sha256: "d".repeat(64),
					inquiry_lines: [],
					inquiry_form_html: `<form method="post" action="/wp-admin/admin-post.php">
					<input type="hidden" name="action" value="linker_inquiry">
					<input type="hidden" name="linker_planner_handoff_id" value="${handoff.handoff_id}">
					<input type="hidden" name="linker_draft_hash"><input type="hidden" name="linker_planner_draft_sha256">
					<p>Workshop · input revision 3</p><button type="submit">Send inquiry</button></form>`,
				};
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
		await until(() => button("Send inquiry"));
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
		await until(() => button("Send inquiry"));
		assert.match(
			button("Send inquiry").form.textContent,
			/Workshop · input revision 3/,
		);
		assert.ok(!requests.some(([path]) => path === "draft/apply"));
		await act(async () => button("Send inquiry").click());
		await until(() => posts.length === 1);
		for (const [path, body] of requests.filter(([path]) =>
			["draft/inquiry-preview", "draft/apply"].includes(path),
		)) {
			assert.equal(body.project_id, project.id, path);
			assert.equal(body.report_run_id, current.id, path);
			assert.equal(body.expected_revision, 3, path);
		}
		assert.equal(posts[0].action, "linker_inquiry");
		assert.equal(posts[0].linker_planner_handoff_id, handoff.handoff_id);
		assert.equal(posts[0].linker_planner_draft_sha256, "f".repeat(64));

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
		await ask(dom.element.querySelector(".sc-project-toolbar"), 3, []);
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

		await act(async () => root.render(null));
		cache.clear();
		wrongProject = false;
		window.history.replaceState(null, "", `?project=${project.id}#sc-project`);
		await render("en");
		await until(() => dom.element.querySelector('[name="location_label"]'));
		await enter(dom.element.querySelector('[name="location_label"]'), "Berlin");
		await act(async () => button("Projects").click());
		await until(() => requests.some(([path]) => path === "projects/revise"));
		const step = [...dom.element.querySelectorAll(".sc-nav button")].find(
			(node) => node.textContent.includes("Review & inquire"),
		);
		await act(async () => step.click());
		for (let page = 0; page < 2; page++) {
			await until(
				() =>
					!button("Earlier calculations")?.disabled &&
					button("Earlier calculations"),
			);
			await act(async () => button("Earlier calculations").click());
		}
		await until(() => button("Revision 2", history()));
		await act(async () => button("Revision 2", history()).click());
		await until(() => button("Ask Genie", history()));
		await ask(history(), 2, [earlier.id]);
		await act(async () => saving.resolve());
		await until(() =>
			button(
				"Ask Genie",
				dom.element.querySelector(".sc-project-toolbar"),
			)?.matches(":enabled"),
		);
		assertContext(context(), 2, [earlier.id]);
		await ask(dom.element.querySelector(".sc-project-toolbar"), 4, []);

		await act(async () => root.render(null));
		cache.clear();
		const staleRequests = requests.length;
		project.revision = current.revision + 1;
		project.input_sha256 = "f".repeat(64);
		currentSummary.is_current = false;
		window.history.replaceState(null, "", deepLink);
		await render("en");
		await until(() => button("Download PDF", history()));
		await act(async () => button("Earlier calculations").click());
		await until(() =>
			requests
				.slice(staleRequests)
				.some(
					([path, body]) => path === "runs/read" && body.run_id === current.id,
				),
		);
		assert.equal(button("Send inquiry"), undefined);
		await act(async () => button("Close", history()).click());
		await until(() => dom.element.querySelector("[data-report-outdated]"));
		assert.ok(button("Download PDF"));
		assert.equal(button("Send inquiry"), undefined);
		assert.ok(
			!requests
				.slice(staleRequests)
				.some(([path]) => path.startsWith("draft/")),
		);
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
	"single-system wiring entered in Solar",
	"multi-system wiring entered in Solar",
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
		const editWiring = scenario.endsWith("wiring entered in Solar");
		const plantWiring = scenario === "multi-system wiring entered in Solar";
		const editPeak = scenario === "edited peak target with a saved candidate";
		if (editWiring) window.location.hash = "sc-solar";
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
			if (editWiring) project.inputs.geometry = flatRoof;
			else project.inputs.pv_string_plan = { schema_version: 1, strings: [] };
			if (plantWiring) {
				const { beginPlant, plantInputs, readPlantDraft } =
					await import("../src/domain/equipmentPlant.ts");
				const setup = project.inputs.equipment_setup;
				const plant = beginPlant(
					project.inputs,
					{ id: "east", name: "East" },
					{ id: "west", name: "West" },
				);
				const draft = readPlantDraft(plant);
				draft.units[1].inputs.equipment_setup = {
					...setup,
					inverter_product_id: 102,
				};
				project.inputs = plantInputs(plant, draft);
			}
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
				if (editWiring && path === "products/current")
					return { schema_version: 1, provider: "woocommerce", pv_modules: [] };
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
				if (path === "projects/revise" && (editPeak || editWiring)) {
					project = {
						...project,
						revision: project.revision + 1,
						inputs: command.inputs,
						input_sha256: "d".repeat(64),
					};
					return project;
				}
				if (path === "runs/check-equipment" && wiringCheck) {
					if (editWiring) {
						const moduleIds = [
							"array:0:0",
							"array:0:1",
							"array:0:2",
							"array:1:0",
							"array:1:1",
						];
						if (plantWiring) {
							assert.equal(command.inputs.pv_string_plan, undefined);
							assert.deepEqual(
								command.inputs.pv_plant_string_plan.units
									.toSorted((a, b) => a.unit_id.localeCompare(b.unit_id))
									.map((unit) => ({
										id: unit.unit_id,
										inverter: unit.plan.inverter_product_id,
										strings: unit.plan.strings.map(
											({ id, ...string }) => string,
										),
									})),
								[
									{
										id: "east",
										inverter: 101,
										strings: [
											{ mppt: 4, input: 1, module_ids: moduleIds.slice(0, 2) },
										],
									},
									{
										id: "west",
										inverter: 102,
										strings: [
											{ mppt: 4, input: 1, module_ids: moduleIds.slice(2) },
										],
									},
								],
							);
						} else {
							assert.deepEqual(
								command.inputs.pv_string_plan.strings.map(
									({ id, ...string }) => string,
								),
								[{ mppt: 4, input: 1, module_ids: moduleIds }],
							);
						}
						wiringCheck = equipmentRun(
							"qualify_woo_equipment_v1",
							project.revision,
							project.input_sha256,
							{ assessment: wiringCheck.result.assessment },
						);
						queuedCheck = {
							...wiringCheck,
							state: "queued",
							result: null,
							result_sha256: null,
						};
					}
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
			if (editWiring) {
				const editors = () =>
					[...dom.element.querySelectorAll("summary")].filter(
						(s) => s.textContent === "PV strings and inputs",
					);
				const button = (text, root = dom.element) =>
					[...root.querySelectorAll("button")].find(
						(b) => b.textContent === text,
					);
				const field = (text, root) =>
					[...root.querySelectorAll("label")]
						.find((l) => l.querySelector("span")?.textContent.trim() === text)
						?.querySelector("input");
				await until(() => editors().length === (plantWiring ? 2 : 1));
				for (const [index, prompt] of editors().entries()) {
					const editor = prompt.parentElement;
					await act(async () => prompt.click());
					await until(
						() =>
							button("Set up PV strings", editor) &&
							!button("Set up PV strings", editor).disabled,
					);
					await act(async () => button("Set up PV strings", editor).click());
					await until(() => button("Select all available modules", editor));
					await act(async () =>
						button("Select all available modules", editor).click(),
					);
					await enter(field("MPPT", editor), "2");
					await enter(field("Inverter input", editor), "1");
					if (plantWiring && index === 0)
						await enter(field("Modules to add to this string", editor), "2");
					const add = button("Add selected modules to string", editor);
					assert.equal(add.disabled, false);
					await act(async () => add.click());
					await act(async () => button("Edit string", editor).click());
					await enter(field("MPPT", editor), "4");
					assert.ok(!button("Save string changes", editor));
					assert.match(editor.textContent, /MPPT 4 · input 1/);
				}
				const [prompt, otherPrompt] = editors();
				const editor = prompt.parentElement;
				const other = otherPrompt?.parentElement;
				if (!editor.open) await act(async () => prompt.click());
				const clearSelection = async (scope = editor) => {
					const clear = button("Clear selection", scope);
					await act(async () =>
						clear.closest("details").querySelector("summary").click(),
					);
					assert.equal(clear.closest("details").open, true);
					await act(async () => clear.click());
				};
				await clearSelection();
				await act(async () => prompt.click());
				assert.equal(editor.open, false);
				await act(async () => button("3Review & inquire").click());
				assert.equal(window.location.hash, "#sc-solar");
				assert.equal(editor.open, true);
				const picker = button("Select all available modules", editor)
					.closest("details")
					.querySelector("summary");
				assert.ok(
					document.activeElement === picker,
					"focus the array in the cleared string's editor",
				);
				assert.equal(
					document.getElementById(picker.getAttribute("aria-describedby"))
						?.textContent,
					"Select at least one module for this string or cancel editing.",
				);
				const mppt = field("MPPT", other ?? editor);
				await enter(mppt, "0");
				await act(async () => button("3Review & inquire").click());
				assert.equal(window.location.hash, "#sc-solar");
				assert.ok(
					document.activeElement === mppt,
					"focus the invalid MPPT before the empty selection",
				);
				assert.ok(
					[...dom.element.querySelectorAll('[role="alert"]')].some(
						(alert) =>
							alert.textContent ===
							"Correct the highlighted input before leaving this project.",
					),
				);
				if (other)
					await act(async () => button("Cancel editing", other).click());
				await act(async () => button("Cancel editing", editor).click());
				assert.match(editor.textContent, /MPPT 4 · input 1/);
				await act(async () => button("Edit string", editor).click());
				await clearSelection();
				await act(async () => button("3Review & inquire").click());
				assert.equal(picker.closest("details").open, true);
				await act(async () =>
					button("Select all available modules", editor).click(),
				);
				assert.equal(picker.hasAttribute("aria-invalid"), false);
				if (other) {
					await act(async () => button("Done editing", editor).click());
					await enter(field("MPPT", editor), "4");
					const occupiedInput = field("Inverter input", editor);
					await enter(occupiedInput, "1");
					assert.equal(occupiedInput.getAttribute("aria-invalid"), "true");
					await act(async () => button("Edit string", other).click());
					await clearSelection(other);
					await act(async () => otherPrompt.click());
					assert.equal(other.open, false);
					await act(async () => button("3Review & inquire").click());
					assert.equal(window.location.hash, "#sc-solar");
					const otherPicker = button("Select all available modules", other)
						.closest("details")
						.querySelector("summary");
					assert.ok(
						document.activeElement === otherPicker,
						`focus the second array picker, got ${document.activeElement?.labels?.[0]?.querySelector("span")?.textContent.trim() ?? document.activeElement?.tagName}`,
					);
					assert.equal(other.open, true);
					await act(async () => button("Cancel editing", other).click());
				}
				await act(async () => button("3Review & inquire").click());
			}
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
				await act(async () => button("Projects").click());
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
			if (scenario !== "current retained inverter") {
				await until(() => generate() && !generate().disabled);
				await act(async () => generate().click());
			}
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
				editWiring
					? ["projects/revise", "runs/check-equipment", "runs/report"]
					: scenario === "automatic wiring check"
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
