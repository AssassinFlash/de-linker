import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred, enter } from "./dom-fixture.mjs";
import { PreparationResult } from "../src/components/energy/PreparationResult.tsx";
import { WeatherProgress } from "../src/components/energy/WeatherProgress.tsx";
import { readWeatherStatus } from "../src/data/weatherStatus.ts";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import {
	projectInputContract,
	beginDraft,
	editDraft,
	undoDraft,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import { PlantPvStringSetup } from "../src/components/equipment/PlantPvStringSetup.tsx";
import { panelPoses } from "../src/domain/panelPoses.ts";
import { equipmentDraft } from "../src/domain/equipment.ts";
import { DeviceConditionInputs } from "../src/components/equipment/DeviceConditionInputs.tsx";
import { PlanningReportResult } from "../src/components/energy/PlanningReportResult.tsx";
import { EquipmentResult } from "../src/components/equipment/EquipmentResult.tsx";
import { ApiError } from "../src/data/protocol.ts";
import { readRun } from "../src/data/planningProtocol.ts";
import { selectPreparation } from "../src/domain/preparationSelection.ts";
import { projectLanguageUrl } from "../src/data/useSiteIntegration.ts";
import fixture from "./fixtures/index.ts";
import plannerGerman from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };
import plantFixture from "./fixtures/plant-energy-run.json" with { type: "json" };

const scope = "a".repeat(64);
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
const selectButton = () =>
	document.querySelector(".lp-run-result > .lp-button");

for (const locale of ["en-GB", "de-DE"]) {
	test(`${locale}: controller network results load the shipped translations and keep historical checks readable`, async (t) => {
		const german = locale.startsWith("de");
		const assessment = {
			model: "woo_multi_converter_plant_v1",
			overall_status: "unresolved",
			selected_products: [],
			provisional_bill_of_materials: [],
			systems: [],
			checks: [
				{
					id: "group:synthetic:controller_network_count",
					semantic_id: "plant_controller_network_count",
					group_name: "Synthetic owner scope",
					status: "satisfied",
					reason: "controller_network_limit_comparison",
					actual: 2,
					required: 10,
					control_network: "lan",
					facts: [
						{
							value: 10,
							unit: "count",
							source: {
								url: "https://example.invalid/controller.pdf",
								page: 1,
								figure_key: "max_lan_inverters",
							},
						},
					],
				},
			],
		};
		let replace;
		function Harness() {
			const [value, setValue] = useState(assessment);
			replace = setValue;
			window.wp.i18n.__ = (message) =>
				german
					? (plannerGerman.locale_data.messages[message]?.[0] ?? message)
					: message;
			return React.createElement(EquipmentResult, {
				run: { state: "succeeded", revision: 1 },
				locale,
				dirty: false,
				confirmedRevision: 1,
				assessmentOverride: value,
				embedded: true,
			});
		}
		await mount(t, React.createElement(Harness));
		const text = document.body.textContent;
		assert.equal(
			text.includes("10 count"),
			false,
			"dimensionless counts never expose the internal unit token",
		);
		assert.ok(
			text.includes("LAN · 10"),
			"the source retains its documented LAN scope",
		);
		assert.equal(
			document
				.querySelector('a[href="https://example.invalid/controller.pdf"]')
				.getAttribute("href"),
			"https://example.invalid/controller.pdf",
		);
		assert.ok(
			text.includes(
				german
					? "Wechselrichter am Controller"
					: "Inverters on the controller network",
			),
		);
		assert.ok(
			text.includes("Synthetic owner scope"),
			"the owner's UI retains its group name",
		);
		const entries = () =>
			new Map(
				[...document.querySelectorAll("dl div")].map((row) => [
					row.querySelector("dt")?.textContent,
					row.querySelector("dd")?.textContent.trim(),
				]),
			);
		assert.equal(
			entries().get(
				german ? "Controller-Kommunikation" : "Controller communication",
			),
			"LAN",
		);
		assert.equal(
			entries().get(
				german ? "Wechselrichter in dieser Gruppe" : "Inverters in this group",
			),
			"2",
		);
		assert.equal(
			entries().get(
				german ? "Maximal unterstützte Anzahl" : "Maximum supported",
			),
			"10",
		);
		assert.ok(
			text.includes(
				german
					? "Die Betriebsgrenzen der Wechselrichtergruppe sind separat aufgeführt."
					: "The operating limits of the inverter group are shown separately.",
			),
		);
		await act(async () =>
			replace({
				...assessment,
				checks: [
					{
						...assessment.checks[0],
						control_network: undefined,
						required: null,
						status: "unresolved",
						reason: "current_cited_controller_network_limit_required",
					},
				],
			}),
		);
		assert.equal(
			entries().get(
				german ? "Controller-Kommunikation" : "Controller communication",
			),
			german ? "Nicht angegeben" : "Not specified",
		);
		assert.equal(
			entries().get(
				german ? "Maximal unterstützte Anzahl" : "Maximum supported",
			),
			"—",
		);
		await act(async () =>
			replace({
				...assessment,
				checks: [
					{
						...assessment.checks[0],
						semantic_id: "plant_parallel_count",
						reason: "parallel_count_uses_applicable_manufacturer_limit",
					},
				],
			}),
		);
		assert.equal(
			entries().has(
				german ? "Maximal unterstützte Anzahl" : "Maximum supported",
			),
			false,
		);
		assert.equal(entries().get(german ? "Ergebnis" : "Result"), "2");
		await act(async () =>
			replace({
				...assessment,
				checks: [
					{
						...assessment.checks[0],
						facts: [
							{
								...assessment.checks[0].facts[0],
								source: {
									...assessment.checks[0].facts[0].source,
									figure_key: "max_devices",
								},
							},
						],
					},
				],
			}),
		);
		assert.equal(
			document.body.textContent.includes("LAN · 10"),
			false,
			"an unscoped device count never acquires a LAN claim",
		);
	});
}

test("a frozen English report marks its own language inside a German planner page", async (t) => {
	const run = structuredClone(fixture.geometric_pv.report_run);
	run.result.report.locale = "en";
	run.result.report.title = "Project planning report";
	run.result.report.subtitle =
		"Saved project inputs and selected calculation results";
	const client = {
		origin: "https://fixture.invalid",
		isCurrentScope: (value) => value === scope,
	};
	await mount(
		t,
		React.createElement(PlanningReportResult, {
			run,
			client,
			scope,
			recheck() {},
			operations: {},
			current: true,
			blocked: false,
			locale: "de-DE",
		}),
	);
	const result = document.querySelector(".lp-run-result");
	assert.equal(result.querySelector("h3").lang, "en");
	assert.equal(
		result.querySelector(".lp-run-heading > div > p:nth-of-type(1)").lang,
		"en",
	);
	const notice = result.querySelector("[role=status]");
	assert.equal(notice.textContent, "Report language: English");
	assert.equal(notice.lang, "de-DE");
	const reportSections = [
		...result.querySelectorAll(".lp-scenario-block, details.lp-comparison"),
	];
	assert.ok(reportSections.length > 0);
	assert.ok(reportSections.every((section) => section.lang === "en"));
});

test("the geometric PV workspace uses all retained intervals, adopts frozen AC explicitly and selects its report run", async (t) => {
	const native = fixture.geometric_pv;
	// The retained source is listed exactly as the service derives it from the
	// owned asset, so the setup must recognise a real selection instead of
	// falling back to a saved identifier placeholder.
	const retained = native.weather_asset,
		retainedLabel = retained.metadata.provenance.label,
		retainedYear =
			retained.metadata.weather_interpretation.synthetic_energy_year;
	const runtimeSession = {
		...session,
		runtime: {
			...session.runtime,
			models: {
				geometric_pv_generation: native.run.result.kind,
				report: "planning_report_v1",
			},
			limits: {
				...session.runtime.limits,
				geometric_pv_generation: native.run.manifest.context.parameters.limits,
			},
		},
	};
	let current = beginDraft(native.project),
		submitted,
		setter;
	const sent = [];
	const client = {
		origin: "https://fixture.invalid",
		isCurrentScope: (value) => value === scope,
		async query(path, body) {
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					pv_modules: [fixture.direct_beam.module_template],
					products: [],
				};
			assert.equal(body.project_id, native.project.id);
			if (path === "weather/assets") {
				return {
					schema_version: 1,
					project_id: native.project.id,
					offset: 0,
					assets: [
						{
							asset_id: retained.id,
							content_sha256: retained.content_sha256,
							metadata_sha256: retained.metadata_sha256,
							label: retainedLabel,
							synthetic_year: retainedYear,
							interval_count: retained.metadata.weather.interval_count,
						},
					],
					next_offset: null,
				};
			}
			if (path === "assets/read")
				return body.asset_id === native.weather_asset.id
					? native.weather_asset
					: native.profile_asset;
			if (path === "runs/read")
				return body.run_id === native.report_run.id
					? native.report_run
					: native.run;
			if (path === "projects/read") return native.project;
			if (path === "profiles/preview") return native.profile_preview_initial;
			if (path === "projects/runs")
				return {
					items: [
						Object.fromEntries(
							Object.entries({
								...native.run,
								task_kind: native.run.result.kind,
								created_at: 100,
							}).filter(
								([key]) => !["manifest", "result", "error"].includes(key),
							),
						),
					],
					next: null,
				};
			throw new Error("unexpected geometric PV read " + path);
		},
		async send(path, body) {
			const command = JSON.parse(body);
			sent.push(path);
			assert.equal(command.expected_revision, current.baseline.revision);
			if (path === "runs/report") {
				submitted = command.options;
				return native.report_run;
			}
			assert.equal(path, "runs/geometric-pv");
			return native.run;
		},
	};
	function Harness() {
		const [value, setValue] = useState(current);
		setter = setValue;
		return React.createElement(EnergyWorkspace, {
			draft: value,
			session: runtimeSession,
			client,
			locale: "en-GB",
			active: true,
			blocked: false,
			recoveryScopes: [scope],
			onValidity() {},
			recheck() {},
			flush: async () => true,
			openProfiles() {},
			openDesign() {},
			sceneModuleUrl: null,
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setValue(current);
				return true;
			},
		});
	}
	await mount(
		t,
		React.createElement(Harness),
		`?project=${native.project.id}&energy_view=geometric-pv`,
	);
	const button = (name) =>
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent === name,
		);
	await until(
		() =>
			button("Calculate saved PV reference with roof shading") &&
			!button("Calculate saved PV reference with roof shading").disabled,
	);
	assert.match(
		document.body.textContent,
		/All 8,760 retained weather intervals/,
	);
	// The setup resolves the retained asset from the real listing: the saved
	// identifier placeholder is not what a user is shown when the source exists.
	const source = () => {
		// The direct-beam setup names the same field; only the PV reference
		// scope lists its own retained source here.
		const section = [...document.querySelectorAll("section")].find(
			(node) =>
				node.querySelector("h3")?.textContent ===
				"PV reference with roof shading",
		);
		return [...section.querySelectorAll("label")]
			.find((node) => node.textContent.includes("Project weather source"))
			.querySelector("select");
	};
	await until(() =>
		[...source().options].some((option) => option.value === retained.id),
	);
	assert.equal(source().value, retained.id);
	assert.equal(
		source().selectedOptions[0].textContent,
		`${retainedLabel} · ${retainedYear}`,
	);
	assert.equal(
		[...source().options].some((option) =>
			option.textContent.startsWith("Saved weather source"),
		),
		false,
	);
	assert.doesNotMatch(
		document.body.textContent,
		/This project has no retained weather source/,
	);
	assert.equal(current.history.current.profile_selections, undefined);
	await act(async () =>
		button("Calculate saved PV reference with roof shading").click(),
	);
	await until(
		() =>
			button("Use this PV profile") && !button("Use this PV profile").disabled,
	);
	await until(() => document.querySelector('svg[role="img"]'));
	assert.match(document.querySelector(".lp-run-result").textContent, /8,760/);
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/unobstructed reference components/,
	);
	assert.equal(current.history.current.profile_selections, undefined);
	await act(async () => button("Use this PV profile").click());
	assert.deepEqual(current.history.current.profile_selections.selected, {
		pv_available_ac: native.profile_asset.id,
	});
	// Selecting a curve edits the draft; acknowledge that save before creating a report.
	await act(async () => {
		current = prepareSave(current, crypto.randomUUID(), {
			maxDepth: 32,
			maxBytes: 1000000,
		});
		current = acknowledgeSave(current, current.pending, {
			...native.project,
			revision: 3,
			inputs: current.pending.inputs,
			input_sha256: "d".repeat(64),
		});
		setter(current);
	});
	await act(async () => button("Planning report").click());
	await until(() =>
		[...document.querySelectorAll("select")].some((node) =>
			[...node.options].some((option) => option.value === native.run.id),
		),
	);
	const choice = [...document.querySelectorAll("select")].find((node) =>
		[...node.options].some((option) => option.value === native.run.id),
	);
	assert.match(choice.textContent, /PV reference with roof shading/);
	await act(async () => {
		choice.value = native.run.id;
		choice.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () => button("Generate planning report").click());
	await until(() => submitted !== undefined);
	assert.equal(submitted.pv_run_id, native.run.id);
	assert.equal(submitted.direct_beam_run_id, undefined);
	assert.deepEqual(sent, ["runs/geometric-pv", "runs/report"]);
});

test("owned geometric setup saves with the cumulative contract and shows frozen night/daylight separately from PV", async (t) => {
	const native = fixture.direct_beam;
	const beamSession = {
		...session,
		runtime: {
			...session.runtime,
			models: {
				direct_beam_visibility: "prepare_direct_beam_visibility_v1",
				report: "planning_report_v1",
			},
			limits: {
				...session.runtime.limits,
				direct_beam_visibility: native.visibility_limits,
			},
		},
	};
	let current = beginDraft(native.project),
		submitted,
		setHarness,
		valid;
	const sent = [];
	const summary = (run, created_at, task_kind) =>
		Object.fromEntries(
			Object.entries({ ...run, created_at, task_kind }).filter(
				([key]) => !["manifest", "result", "error"].includes(key),
			),
		);
	const client = {
		origin: "https://fixture.invalid",
		isCurrentScope: (v) => v === scope,
		async query(path, body) {
			assert.equal(body.schema_version, 1);
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					pv_modules: [native.module_template],
					products: [],
				};
			if (path === "runs/read")
				return body.run_id === native.report_run.id
					? native.report_run
					: native.run;
			assert.equal(body.project_id, native.project.id);
			if (path === "weather/assets") return native.weather_assets;
			if (path === "assets/read") {
				assert.equal(body.asset_id, native.weather_asset.id);
				return native.weather_asset;
			}
			if (path === "weather/preview") {
				if (body.offset === 0) return native.weather_preview;
				assert.equal(body.offset, 12);
				const row = native.run.result.visibility.rows[1];
				// This bounded page uses the exact same retained weather row as
				// the native daylight witness, not a fabricated visibility value.
				return {
					...native.weather_preview,
					offset: 12,
					rows: [
						Object.fromEntries(
							[
								"source_row_index",
								"interval_start_utc",
								"interval_end_utc",
								"source_label_utc",
								"irradiance_at_utc",
							].map((key) => [key, row[key]]),
						),
					],
					next_offset: 13,
				};
			}
			if (path === "projects/runs")
				return {
					items: [
						summary(native.report_run, 200, "planning_report_v1"),
						summary(native.run, 100, "prepare_direct_beam_visibility_v1"),
					],
					next: null,
				};
			throw new Error("unexpected geometric read " + path);
		},
		async send(path, body, requestedScope) {
			const command = JSON.parse(body);
			assert.equal(requestedScope, scope);
			assert.equal(command.project_id, native.project.id);
			assert.equal(command.expected_revision, 2);
			sent.push({ path, body });
			if (path === "runs/report") {
				submitted = command.options;
				return native.report_run;
			}
			assert.equal(path, "runs/direct-beam");
			return native.run;
		},
	};
	function Harness() {
		const [value, setValue] = useState(current),
			[runtimeSession, setRuntimeSession] = useState(beamSession);
		setHarness = (next, nextSession = beamSession) => {
			current = next;
			setValue(next);
			setRuntimeSession(nextSession);
		};
		return React.createElement(EnergyWorkspace, {
			draft: value,
			session: runtimeSession,
			client,
			locale: "en-GB",
			active: true,
			blocked: false,
			recoveryScopes: [scope],
			onValidity(value) {
				valid = value;
			},
			recheck() {},
			flush: async () => true,
			openProfiles() {},
			openDesign() {},
			sceneModuleUrl: null,
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setValue(current);
				return true;
			},
		});
	}
	await mount(
		t,
		React.createElement(Harness),
		`?project=${native.project.id}&energy_view=direct-beam`,
	);
	const button = (name) =>
		[...document.querySelectorAll("button")].find(
			(b) => b.textContent === name,
		);
	await until(
		() =>
			button("Calculate direct-beam visibility") &&
			!button("Calculate direct-beam visibility").disabled,
	);
	const date = document.querySelector('input[type="datetime-local"]');
	await enter(
		date,
		native.run.result.visibility.rows[1].interval_start_utc.slice(0, 16),
	);
	await act(async () => button("Show interval page").click());
	await until(() =>
		[...document.querySelectorAll('input[type="checkbox"]')].some((input) =>
			input
				.getAttribute("aria-label")
				?.includes(native.run.result.visibility.rows[1].interval_start_utc),
		),
	);
	await act(async () => button("Calculate direct-beam visibility").click());
	await until(
		() =>
			document.querySelector(".lp-run-result h3")?.textContent ===
			"Geometric direct-beam visibility",
	);
	assert.equal(sent[0].path, "runs/direct-beam");
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/Sun at or below horizon/,
	);
	const timestamp = [...document.querySelectorAll("label")]
		.find((label) =>
			label.textContent.includes("Selected source irradiance timestamp"),
		)
		.querySelector("select");
	await act(async () => {
		timestamp.value = "1";
		timestamp.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.match(document.querySelector(".lp-run-result").textContent, /Sampled/);
	assert.ok(
		document
			.querySelector(".lp-run-result")
			.textContent.includes(
				native.run.result.visibility.rows[1].irradiance_at_utc,
			),
	);
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/frozen geometry/,
	);
	await act(async () => button("Planning report").click());
	await until(() =>
		[...document.querySelectorAll(".lp-scenario-fields select")].some(
			(select) => [...select.options].some((o) => o.value === native.run.id),
		),
	);
	const reportChoice = [
		...document.querySelectorAll(".lp-scenario-fields select"),
	].find((select) =>
		[...select.options].some((o) => o.value === native.run.id),
	);
	await act(async () => {
		reportChoice.value = native.run.id;
		reportChoice.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () => button("Generate planning report").click());
	await until(() => submitted !== undefined);
	assert.equal(submitted.direct_beam_run_id, native.run.id);
	assert.equal(submitted.pv_run_id, null);
	await until(
		() =>
			new URL(window.location.href).searchParams.get("run") ===
			native.report_run.id,
	);
	await act(async () => button("Direct-beam visibility").click());
	await until(() => !button("Calculate direct-beam visibility").disabled);
	const fine = [...document.querySelectorAll("label")]
		.find((label) =>
			label.textContent.includes("Fine grid cells per module edge"),
		)
		.querySelector("input");
	await enter(fine, "3");
	assert.equal(button("Calculate direct-beam visibility").disabled, true);
	const pending = prepareSave(current, "30000000-0000-4000-8000-000000000001", {
		maxDepth: 32,
		maxBytes: 1000000,
	});
	assert.equal(
		JSON.parse(pending.pending.body).input_contract,
		projectInputContract,
	);
	assert.equal(
		JSON.parse(pending.pending.body).inputs.direct_beam_visibility.sampling
			.fine_cells_per_edge,
		3,
	);
	// Optional runtime configuration must not invalidate canonical saved data.
	await act(async () => setHarness(beginDraft(native.project), session));
	await until(() =>
		document.body.textContent.includes(
			"unavailable in the current service version",
		),
	);
	assert.equal(valid, true);
	assert.equal(button("Calculate direct-beam visibility").disabled, true);
	// Geometry edits retain old weather; detect that explicit reconciliation
	// is required before the user dispatches another native worker job.
	const moved = structuredClone(native.project);
	moved.inputs.geometry.coordinate_system.anchor.latitude_deg += 1;
	await act(async () => setHarness(beginDraft(moved)));
	await until(() =>
		document.body.textContent.includes(
			"coordinates do not match the saved roof location",
		),
	);
	assert.equal(button("Calculate direct-beam visibility").disabled, true);
	assert.equal(
		sent.filter((request) => request.path === "runs/direct-beam").length,
		1,
	);
});

async function mount(t, component, initialUrl) {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	if (initialUrl) window.history.replaceState(null, "", initialUrl);
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

test("PVGIS method keeps explicit saved choices, recovers its exact request and adopts only AC", async (t) => {
	const original = fixture.pvgis_reference_run;
	assert.equal(
		readRun(original, original.project_id).result.kind,
		"prepare_pvgis_roof_ac_reference_v1",
	);
	const initial = structuredClone(fixture.pvgis_reference_project);
	delete initial.inputs.pvgis_reference;
	let current = beginDraft(initial),
		setter,
		returnedRun,
		attempts = 0;
	const sent = [],
		calls = [],
		task = "prepare_pvgis_roof_ac_reference_v1";
	const referenceSession = {
		...session,
		runtime: { ...session.runtime, models: { pvgis_roof_reference: task } },
	};
	const template =
		original.result.prepared_asset.metadata.woo_module_inputs.module;
	const client = {
		isCurrentScope: (value) => value === scope,
		async query(path, body) {
			calls.push(path);
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					pv_modules: [template],
					products: [],
				};
			if (path === "projects/runs") return { items: [], next: null };
			if (path === "runs/read") return returnedRun;
			if (path === "projects/read") {
				assert.equal(body.revision, 2);
				return current.baseline;
			}
			if (path === "assets/read") return returnedRun.result.prepared_asset;
			throw new Error("Unexpected query " + path);
		},
		async send(path, body) {
			assert.equal(path, "runs/pvgis-reference");
			sent.push(body);
			attempts++;
			if (attempts === 1)
				throw new Error("Synthetic lost response after admission");
			assert.equal(
				body,
				sent[0],
				"durable retry keeps original key/body/revision",
			);
			return returnedRun;
		},
	};
	function Harness() {
		const [draft, setDraft] = useState(current);
		setter = setDraft;
		return React.createElement(EnergyWorkspace, {
			draft,
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
				return true;
			},
			flush: async () => true,
			session: referenceSession,
			client,
			recheck() {
				throw new Error("No identity error expected");
			},
			locale: "en-GB",
			active: true,
			blocked: false,
			onValidity() {},
			openProfiles() {},
		});
	}
	// The existing DOM fixture owns the page; set its initial method on render.
	function MethodHarness() {
		window.history.replaceState(
			null,
			"",
			`?project=${initial.id}&energy_view=pvgis-reference#lp-calculations`,
		);
		return React.createElement(Harness);
	}
	await mount(t, React.createElement(MethodHarness));
	const form = () =>
		[...document.querySelectorAll("section.lp-scenario-block")].find(
			(node) =>
				node.querySelector("h3")?.textContent === "PVGIS annual AC reference",
		);
	await until(() => form() && calls.includes("products/current"));
	assert.ok(
		[...form().querySelectorAll("select,input,textarea")].every(
			(node) => node.value === "",
		),
		"no model choice or numeric assumption is autofilled",
	);
	const byLabel = (label) =>
		[...form().querySelectorAll("label")]
			.find(
				(node) =>
					node.querySelector("span")?.firstChild?.textContent.trim() === label,
			)
			?.querySelector("input,select,textarea");
	async function choose(label, value) {
		await act(async () => {
			const node = byLabel(label);
			node.value = value;
			node.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	await choose("Radiation database", "PVGIS-ERA5");
	await enter(byLabel("Calendar year"), "2020");
	await choose("PV reference technology", "crystSi");
	await choose("PVGIS mounting type", "free");
	await enter(byLabel("PVGIS system loss setting"), "14");
	await choose("Terrain horizon", "true");
	const calculate = () =>
		[...form().querySelectorAll("button")].find(
			(node) => node.textContent === "Calculate annual AC reference",
		);
	assert.equal(
		calculate().disabled,
		true,
		"unsaved choices cannot start a job",
	);
	assert.equal(current.history.current.pvgis_reference.source_note, null);
	const language = projectLanguageUrl(
		"https://fixture.invalid/de/",
		window.location.href,
		initial.id,
	);
	assert.equal(
		new URL(language).searchParams.get("energy_view"),
		"pvgis-reference",
	);
	await act(async () => {
		current = prepareSave(current, crypto.randomUUID(), {
			maxDepth: 32,
			maxBytes: 16777216,
		});
		const intent = current.pending;
		current = acknowledgeSave(current, intent, {
			...current.baseline,
			revision: 2,
			inputs: intent.inputs,
			input_sha256: "d".repeat(64),
		});
		setter(current);
	});
	// Keep the captured native result structure; only this synthetic Save's
	// immutable identity/revision fields change. No numerical values are edited.
	returnedRun = structuredClone(original);
	returnedRun.revision = 2;
	returnedRun.manifest.revision = 2;
	returnedRun.manifest.input_sha256 = current.baseline.input_sha256;
	returnedRun.result.revision = 2;
	returnedRun.result.input_sha256 = current.baseline.input_sha256;
	returnedRun.result.prepared_asset.metadata.derived_from_revision = 2;
	await until(() => calculate() && !calculate().disabled);
	await act(async () => calculate().click());
	const retry = () =>
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent === "Retry original calculation request",
		);
	await until(() => retry() && !retry().disabled);
	assert.equal(attempts, 1);
	await act(async () => retry().click());
	await until(() => selectButton() && !selectButton().disabled);
	assert.equal(attempts, 2);
	assert.equal(JSON.parse(sent[0]).expected_revision, 2);
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/PVGIS-ERA5/,
	);
	assert.match(
		document.querySelector(".lp-run-result").textContent,
		/SARAH3 sample/,
	);
	assert.equal(
		document.querySelector(".lp-run-result pre"),
		null,
		"source details are semantic fields, not an internal JSON dump",
	);
	assert.ok(document.querySelector(".lp-run-result table"));
	await act(async () => selectButton().click());
	assert.equal(
		current.history.current.profile_selections.selected.pv_available_ac,
		returnedRun.result.prepared_asset.id,
	);
	assert.equal(
		current.history.current.profile_selections.selected.pv_reference,
		undefined,
	);
	const before = structuredClone(current.history.current);
	assert.throws(
		() =>
			selectPreparation(
				{ ...before, energy_scenario: { coupling: "shared_dc" } },
				returnedRun,
				current.baseline,
				returnedRun.result.prepared_asset,
			),
		(error) => error.code === "pvgis_reference_dc_conflict",
	);
	assert.deepEqual(
		current.history.current,
		before,
		"DC refusal preserves saved choices",
	);
	assert.ok(
		calls.every((path) =>
			[
				"products/current",
				"projects/runs",
				"runs/read",
				"projects/read",
				"assets/read",
			].includes(path),
		),
	);
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

test("typed rejected official weather explains the source failure, keeps legacy fallback and hides cached details after ownership changes", async (t) => {
	const quality = {
		reason: "negative_wind",
		field: "WS10m",
		row_index: 751,
		source_timestamp_utc: "2006-02-01T07:00:00+00:00",
		value: -0.29,
	};
	const failed = {
		...structuredClone(fixture.weather_run),
		state: "failed",
		result: null,
		result_sha256: null,
		error: {
			code: "weather_source_quality_invalid",
			retryable: false,
			details: {
				...quality,
				private_exception: "PRIVATE_EXCEPTION_DO_NOT_RENDER",
			},
		},
	};
	const rejected = {
		...structuredClone(fixture.weather_status),
		task_state: "failed",
		acquisition_state: "rejected",
		capture_sha256: null,
		diagnostic_retained: true,
		validation_failure: {
			code: "weather_source_quality_invalid",
			...quality,
			private_url: "PRIVATE_URL_DO_NOT_RENDER",
		},
	};
	assert.equal(
		readWeatherStatus(rejected, failed.id).validationFailure.sourceTimestampUtc,
		quality.source_timestamp_utc,
	);
	assert.throws(() =>
		readWeatherStatus(
			{
				...rejected,
				validation_failure: {
					...rejected.validation_failure,
					source_timestamp_utc: "PRIVATE_EXCEPTION_DO_NOT_RENDER",
				},
			},
			failed.id,
		),
	);
	let admitted = true,
		legacy = false,
		update;
	const calls = [];
	const client = {
		isCurrentScope: (value) => admitted && value === scope,
		async query(path, body) {
			calls.push(path);
			assert.equal(path, "runs/weather/status");
			return legacy
				? {
						...fixture.weather_status,
						run_id: body.run_id,
						task_state: "failed",
						acquisition_state: "fetching",
						capture_sha256: null,
					}
				: rejected;
		},
		send() {
			throw new Error(
				"reading rejected weather must never request provider work",
			);
		},
	};
	function Harness() {
		const [, refresh] = useState(0);
		update = () => refresh((value) => value + 1);
		return React.createElement(PreparationResult, {
			run: legacy
				? {
						...failed,
						id: "f".repeat(32),
						error: { code: "invalid_input", retryable: false },
					}
				: failed,
			inputs: fixture.weather_project.inputs,
			edit() {
				throw new Error("a rejected source cannot change project inputs");
			},
			session,
			client,
			recheck: () => {},
			locale: "en-GB",
			blocked: false,
			active: true,
		});
	}
	await mount(t, React.createElement(Harness));
	await until(() =>
		document.body.textContent.includes("negative wind-speed value"),
	);
	assert.equal(
		(document.body.textContent.match(/negative wind-speed value/g) ?? [])
			.length,
		1,
	);
	assert.match(document.body.textContent, /cannot be used for PV calculation/);
	assert.match(document.body.textContent, /Source value: -0\.29 m\/s/);
	assert.match(
		document.body.textContent,
		/No usable weather dataset was created from this response/,
	);
	assert.match(document.body.textContent, /Source timestamp \(UTC\):.*2006/);
	assert.doesNotMatch(
		document.body.textContent,
		/PRIVATE_|Use this weather source|Source ready/,
	);
	assert.equal(calls.length, 1);
	await act(async () => {
		admitted = false;
		update();
	});
	assert.doesNotMatch(
		document.body.textContent,
		/negative wind-speed|2006|PRIVATE_/,
	);
	assert.equal(
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent === "Refresh weather status",
		).disabled,
		true,
	);
	assert.equal(calls.length, 1);
	await act(async () => {
		admitted = true;
		legacy = true;
		update();
	});
	await until(() =>
		document.body.textContent.includes(
			"ended without a validated weather source",
		),
	);
	assert.match(document.body.textContent, /This source could not be prepared/);
	assert.doesNotMatch(
		document.body.textContent,
		/negative wind-speed|2006|PRIVATE_|Source ready/,
	);
	assert.ok(calls.every((path) => path === "runs/weather/status"));
});

test("real saved plant device entries stay optional, preserve per-unit version text and recover through Draft save and undo", async (t) => {
	let current = beginDraft(structuredClone(plantFixture.project)),
		setter,
		valid = true;
	const client = {
		isCurrentScope: (value) => value === scope,
		query() {
			throw new Error("inactive input editor must not acquire a source");
		},
	};
	function Harness() {
		const [draft, setDraft] = useState(current);
		setter = setDraft;
		return React.createElement(DeviceConditionInputs, {
			draft,
			client,
			scope,
			active: false,
			disabled: false,
			onValidity: (value) => {
				valid = value;
			},
			onError(error) {
				if (error) throw error;
			},
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
				return true;
			},
		});
	}
	await mount(t, React.createElement(Harness));
	assert.equal(current.history.current.equipment_condition_inputs, undefined);
	await act(async () =>
		document.querySelector('input[type="checkbox"]').click(),
	);
	assert.deepEqual(current.history.current.equipment_condition_inputs, {
		schema_version: 1,
		devices: [],
	});
	const firmwareFields = [...document.querySelectorAll("label")]
		.filter(
			(node) =>
				node.querySelector("span")?.textContent ===
				"Declared firmware or software",
		)
		.map((node) => node.querySelector("input"));
	assert.equal(firmwareFields.length, 6);
	assert.ok(
		firmwareFields.every((node) => node.value === ""),
		"no Woo model or version is autofilled as a project entry",
	);
	await enter(firmwareFields[0], "001.02-A");
	await enter(firmwareFields[3], "01.2-A");
	const entries = current.history.current.equipment_condition_inputs.devices;
	assert.equal(entries[0].selection_ref.unit_id, "a");
	assert.equal(entries[1].selection_ref.unit_id, "b");
	assert.equal(entries[0].declared_firmware, "001.02-A");
	assert.equal(entries[1].declared_firmware, "01.2-A");
	assert.equal(entries[0].declared_model, null);
	await act(async () => {
		current = prepareSave(current, crypto.randomUUID(), {
			maxDepth: 32,
			maxBytes: 16777216,
		});
		const intent = current.pending;
		current = acknowledgeSave(current, intent, {
			...current.baseline,
			revision: intent.expectedRevision + 1,
			inputs: intent.inputs,
			input_sha256: "e".repeat(64),
		});
		setter(current);
	});
	assert.equal(
		current.baseline.inputs.equipment_condition_inputs.devices[0]
			.declared_firmware,
		"001.02-A",
	);
	await act(async () => {
		const next = structuredClone(current.history.current);
		for (const unit of next.equipment_plant.units)
			unit.selection.product_revisions["4107"] = "a".repeat(64);
		current = editDraft(current, next);
		setter(current);
	});
	assert.equal(valid, false);
	assert.match(
		document.body.textContent,
		/different device, system or product revision/,
	);
	assert.match(document.body.textContent, /001\.02-A/);
	assert.equal(
		current.history.current.equipment_condition_inputs.devices[0]
			.product_revision,
		plantFixture.project.inputs.equipment_plant.units[0].selection
			.product_revisions["4107"],
		"a stale entry is never rebound",
	);
	await act(async () => {
		current = undoDraft(current);
		setter(current);
	});
	assert.equal(valid, true);
	assert.equal(document.querySelector('[role="alert"]'), null);
});

for (const locale of ["en-US", "de-DE"])
	test(`plant string editor excludes other systems' roof modules and retains their independent input and binding: ${locale}`, async (t) => {
		const project = structuredClone(fixture.geometric_pv.project);
		project.inputs.geometry.arrays[0].columns = 3;
		const modules = panelPoses(project.inputs.geometry).filter(
			(p) => p.included,
		);
		assert.ok(modules.length >= 2);
		const selection = {
			...equipmentDraft({}),
			grid_phase: 3,
			operating_mode: "grid_connected",
			inverter_product_id: 1,
			product_revisions: { 1: "a".repeat(64) },
		};
		const units = ["a", "b"].map((id) => ({
			id,
			name: id.toUpperCase(),
			inputs: { equipment_selection: selection },
		}));
		const plan = (id, module) => ({
			schema_version: 1,
			inverter_product_id: 1,
			minimum_ambient_c: null,
			temperature_source: null,
			strings: [{ id, mppt: 1, input: 1, module_ids: [module] }],
		});
		const wiring = {
			schema_version: 1,
			units: units.map((u, i) => ({
				unit_id: u.id,
				inverter_instance_id: "inv_" + u.id,
				plan: plan("s_" + u.id, modules[i].id),
			})),
		};
		project.inputs.pv_plant_string_plan = wiring;
		project.inputs.equipment_candidate = { id: "old" };
		project.inputs.installation = {
			schema_version: 1,
			geometry_sha256: null,
			instances: units.map((u) => ({
				id: "inv_" + u.id,
				name: u.name,
				product_id: 1,
				product_revision: "a".repeat(64),
				source_id: "survey",
				ports: [
					{
						id: "pv",
						name: "PV",
						position: { east_m: 0, north_m: 0, height_m: 1 },
					},
				],
			})),
			circuits: [],
			routes: [],
			cable_runs: [],
		};
		let current = beginDraft(project),
			replace,
			valid;
		const validity = (value) => {
			valid = value;
		};
		function Harness() {
			const [draft, setDraft] = useState(current);
			replace = (next) => {
				current = next;
				setDraft(next);
			};
			window.wp.i18n.__ = (message) =>
				locale.startsWith("de")
					? (plannerGerman.locale_data.messages[message]?.[0] ?? message)
					: message;
			return React.createElement(PlantPvStringSetup, {
				draft,
				unit: units[0],
				locale,
				disabled: false,
				onValidity: validity,
				edit(operation) {
					replace(editDraft(current, operation(current.history.current)));
					return true;
				},
			});
		}
		await mount(t, React.createElement(Harness));
		const checkboxes = [...document.querySelectorAll('input[type="checkbox"]')];
		assert.ok(checkboxes[0].disabled);
		assert.ok(
			checkboxes[1].disabled,
			"unit B's assigned module cannot be reused by A",
		);
		const binding = [...document.querySelectorAll("select")].find((s) =>
			[...s.options].some((o) => o.value === "inv_a"),
		);
		assert.ok(binding);
		assert.ok(
			document.body.textContent.includes(
				locale.startsWith("de")
					? "Wechselrichter in der gespeicherten Installation"
					: "Inverter in the saved installation",
			),
		);
		assert.equal(
			[...binding.options].some((o) => o.value === "inv_b"),
			false,
			"same-model unit B instance remains unavailable",
		);
		await enter(document.querySelector("textarea"), "Documented local minimum");
		assert.deepEqual(
			current.history.current.pv_plant_string_plan.units.find(
				(u) => u.unit_id === "b",
			),
			wiring.units[1],
		);
		assert.equal(current.history.current.equipment_candidate, undefined);
		await act(async () => {
			binding.value = "";
			binding.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
		assert.equal(
			current.history.current.pv_plant_string_plan.units.find(
				(u) => u.unit_id === "a",
			).inverter_instance_id,
			null,
		);
		assert.equal(
			current.history.current.pv_plant_string_plan.units.find(
				(u) => u.unit_id === "b",
			).inverter_instance_id,
			"inv_b",
		);
		await act(async () => {
			units[0] = {
				...units[0],
				inputs: { equipment_setup: { ...selection, inverter_product_id: 2 } },
			};
			replace(editDraft(current, { ...current.history.current, stale: true }));
		});
		assert.ok(
			document.body.textContent.includes(
				window.wp.i18n.__(
					"These strings belong to another inverter. Select that inverter or start a new wiring plan.",
				),
			),
		);
		assert.equal(
			valid,
			true,
			"a stale model is saveable for explicit recovery",
		);
		const remove = [...document.querySelectorAll("button")].find(
			(b) => b.textContent === window.wp.i18n.__("Remove wiring plan"),
		);
		await act(async () => remove.click());
		assert.deepEqual(current.history.current.pv_plant_string_plan.units, [
			wiring.units[1],
		]);
	});
