import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { IDBFactory } from "fake-indexeddb";
import React, { act } from "react";
import { setupDom, until, enter } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

const projectId = "7".repeat(32);
const session = {
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
			equipment_search: "search_woo_equipment_v1",
			report: "planning_report_v1",
		},
		limits: {
			max_body_bytes: 1000000,
			max_csv_bytes: 100000,
			max_page_size: 30,
			max_json_depth: 32,
		},
	},
};

for (const target of ["compare", "retry", "profile"])
	test(`project setup retains its inputs when opening saved projects and continuing via ${target}`, async (t) => {
		const fixture = setupDom();
		// The shared fixture opens a project from its URL; this test starts at the
		// empty index, which is where the one-screen start lives.
		window.history.replaceState({}, "", "/workspace/");
		const globals = new Map();
		for (const [name, value] of Object.entries({
			indexedDB: new IDBFactory(),
			MutationObserver: window.MutationObserver,
			getComputedStyle: window.getComputedStyle.bind(window),
			requestAnimationFrame: (callback) =>
				setTimeout(() => callback(Date.now()), 0),
			cancelAnimationFrame: clearTimeout,
		})) {
			globals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
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

		let listed = [];
		const creates = [],
			searches = [],
			destinations = [];
		let run;
		let accepted;
		const client = {
			async send(path, body) {
				const command = JSON.parse(body);
				if (path === "runs/find-equipment") {
					searches.push(command);
					assert.equal(command.project_id, projectId);
					assert.equal(command.expected_revision, 1);
					accepted = {
						...accepted,
						inputs: command.inputs,
						revision: 2,
						input_sha256: "8".repeat(64),
					};
					const kind = "search_woo_equipment_v1";
					run = {
						id: "9".repeat(32),
						project_id: projectId,
						revision: 2,
						manifest_sha256: "a".repeat(64),
						result_sha256: null,
						state: "queued",
						is_current: true,
						manifest: {
							schema: 1,
							project_id: projectId,
							revision: 2,
							input_sha256: accepted.input_sha256,
							context: {
								code_sha256: "4".repeat(64),
								models: { task: kind },
								assets: { "woo.equipment_inputs": "5".repeat(64) },
								parameters: { kind },
							},
						},
						result: null,
						error: null,
					};
					return { schema_version: 1, project: accepted, run };
				}
				assert.equal(path, "projects/create");
				creates.push(body);
				if (!accepted)
					accepted = {
						id: projectId,
						revision: 1,
						title: command.title,
						inputs: command.inputs,
						input_sha256: "2".repeat(64),
					};
				if (target === "retry" && creates.length === 1)
					throw new Error("lost creation response");
				return accepted;
			},
			invalidate() {},
			async bootstrap() {
				return session;
			},
			async probeScope() {
				return session.query_scope;
			},
			isCurrentScope(scope) {
				return scope === session.query_scope;
			},
			async query(path, body) {
				if (path === "profiles/standard" || path === "assets/read") {
					assert.equal(body.project_id, projectId);
					return {
						id: "2".repeat(32),
						project_id: projectId,
						content_sha256: "a".repeat(64),
						metadata_sha256: "b".repeat(64),
						media_type: "application/json",
						purpose: "csv_profile_v1",
						metadata: {},
					};
				}
				if (path === "profiles/preview")
					return {
						schema_version: 1,
						evaluation_scope: "profile_interpretation",
						project_id: projectId,
						asset_id: "2".repeat(32),
						content_sha256: "a".repeat(64),
						metadata_sha256: "b".repeat(64),
						measurement: "gross_load",
						source: {},
						transformations: [],
						summary: {
							start_utc: "2026-01-01T00:00:00Z",
							end_utc: "2026-01-01T00:15:00Z",
							interval_count: 1,
							covered_seconds: 900,
							span_seconds: 900,
							gap_seconds: 0,
							gap_count: 0,
							energy_kwh: 1,
							min_interval_mean_kw: 4,
							max_interval_mean_kw: 4,
							native_max_interval_seconds: 900,
							effective_max_interval_seconds: 900,
							reconstructed_means: false,
						},
						rows: [
							{
								interval_index: 0,
								start_utc: "2026-01-01T00:00:00Z",
								end_utc: "2026-01-01T00:15:00Z",
								interval_mean_kw: 4,
							},
						],
						first_gaps: [],
						gaps_truncated: false,
						next_offset: null,
					};
				if (path === "projects/list")
					return { schema_version: 1, items: listed, next: null };
				if (path === "projects/runs") return { items: [], next: null };
				if (path === "runs/read") return run;
				if (path === "projects/read") return accepted;
				throw new Error("unexpected command " + path);
			},
		};
		const store = {
			async writeCreation(_scope, _body, destination) {
				destinations.push(destination);
			},
			async clearCreation() {},
			async readCreations() {
				return [];
			},
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
		const config = {
			baseUrl: location.origin + "/api/",
			nonceUrl: location.origin + "/nonce",
			locale: "en-US",
			countries: { NO: "Norway" },
		};
		const root = createRoot(fixture.element);
		t.after(async () => {
			await fixture.dispose(root);
			for (const [name, descriptor] of globals) {
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
		const start = () => document.querySelector("form");
		await until(() => document.querySelector('select[name="system_scope"]'));
		const reviewStep = () =>
			[...document.querySelectorAll("nav button")].find((button) =>
				button.textContent.includes("Review & inquire"),
			);
		assert.equal(
			document.querySelector("#sc-solar"),
			null,
			"unselected project does not ask for solar inputs",
		);
		await act(async () => reviewStep().click());
		assert.equal(creates.length, 0);
		const choose = async (select, value) =>
			act(async () => {
				select.value = value;
				select.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
		await choose(
			document.querySelector('[name="system_scope"]'),
			"new_pv_storage",
		);
		assert.ok(
			document.querySelector("#sc-solar"),
			"solar is editable without creating a project",
		);
		await choose(
			document.querySelector('[name="system_scope"]'),
			"storage_only",
		);
		assert.equal(
			document.querySelector("#sc-solar"),
			null,
			"storage does not ask for a roof",
		);
		await enter(document.querySelector('[name="location_label"]'), "Oslo");

		listed = [
			{
				id: projectId,
				title: "Residential · 10 kWp · 10115 Berlin",
				revision: 1,
				input_sha256: "8".repeat(64),
				updated_at: 1763200000,
			},
		];
		const refresh = () =>
			[...document.querySelectorAll("button")].find(
				(button) => button.getAttribute("aria-label") === "Refresh projects",
			);
		const toolbarButton = (name) =>
			[...document.querySelectorAll("header button")].find(
				(button) => button.textContent === name,
			);
		await act(async () => toolbarButton("Saved projects").click());
		assert.ok(start().closest("[hidden]"));
		await act(async () => refresh().click());
		await until(
			() => document.querySelectorAll('[role="listitem"]').length === 1,
		);
		await act(async () => toolbarButton("Back to project").click());
		assert.equal(start().closest("[hidden]"), null);
		assert.equal(
			document.querySelector('input[name="location_label"]').value,
			"Oslo",
		);
		assert.equal(
			document.querySelector('select[name="system_scope"]').value,
			"storage_only",
		);
		const purpose = document.querySelector('select[name="project_purpose"]');
		assert.ok(purpose, "purpose belongs to the initial Project page");
		await act(async () => {
			purpose.value = "self";
			purpose.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
		const grid = [...document.querySelectorAll("label")].find(
			(el) =>
				el.textContent.includes("Grid connection") &&
				el.querySelector("select"),
		);
		await choose(grid.querySelector("select"), "3");
		const annual = [...document.querySelectorAll("label")].find((el) =>
			el.textContent.includes("Annual electricity use"),
		);
		await enter(annual.querySelector("input"), "6400");
		const button = (name) =>
			[...document.querySelectorAll("button")].find(
				(el) => el.textContent === name,
			);
		assert.equal(creates.length, 0);
		if (target === "profile") {
			const panel = [...document.querySelectorAll("summary")].find(
				(el) => el.textContent === "Electricity use over time",
			);
			await act(async () => panel.click());
			await enter(
				document.querySelector('input[placeholder="Europe/Berlin"]'),
				"Europe/Oslo",
			);
			await choose(document.querySelector('[name="load-pattern"]'), "H0");
			await act(async () => button("Use this load profile").click());
			await until(
				() => document.querySelector('input[name="project_title"]').readOnly,
			);
			assert.equal(
				new URL(location.href).searchParams.get("project"),
				projectId,
			);
			assert.equal(searches.length, 0);
			await enter(annual.querySelector("input"), "7100");
		}
		assert.ok(!button("Compare systems").disabled);
		await act(async () => {
			button("Compare systems").click();
			button("Compare systems").click();
		});
		if (target === "retry") {
			await until(() => button("Retry project creation"));
			assert.equal(searches.length, 0);
			await act(async () => button("Retry project creation").click());
		}
		await until(() => location.hash === "#sc-system");
		assert.equal(new Set(creates).size, 1);
		assert.equal(creates.length, target === "retry" ? 2 : 1);
		assert.ok(
			destinations.every(
				(destination) =>
					destination === (target === "profile" ? "edit" : "compare"),
			),
		);
		assert.equal(searches.length, 1);
		assert.equal(JSON.parse(creates[0]).inputs.brief.annual_load.kwh, 6400);
		assert.equal(searches[0].inputs.equipment_setup.grid_phase, 3);
		assert.equal(accepted.title, "Oslo");
		if (target === "profile") {
			assert.equal(searches[0].inputs.brief.annual_load.kwh, 7100);
			assert.equal(
				searches[0].inputs.profile_selections.selected.gross_load,
				"2".repeat(32),
			);
		}
		assert.match(
			document.querySelector("nav [aria-current=step]").textContent,
			/Choose a solution/,
		);
	});
