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

for (const target of [
	"preliminary",
	"partial",
	"saved",
	"compare",
	"retry",
	"profile",
	"profile-preliminary",
	"csv",
]) {
	const saved = target === "saved";
	const csv = "time;power\n2026-01-01T00:00Z;4\n";
	const name =
		{
			partial:
				"A guest with a site and storage direction can compare without a grid phase",
			preliminary:
				"A guest can compare preliminary options from a blank project and review their chosen direction",
			csv: "a fresh PV project can import a CSV with an invalid coordinate and compare after correction",
			saved:
				"An account owner can reopen a Genie equipment list and carry the original quantities into the project",
		}[target] ??
		`project setup retains its inputs when opening saved projects and continuing via ${target}`;
	test(name, async (t) => {
		const fixture = setupDom();
		// The shared fixture opens a project from its URL; this test starts at the
		// empty index, which is where the one-screen start lives.
		window.history.replaceState(
			{},
			"",
			saved
				? "/workspace/?saved_solution=45"
				: target === "preliminary"
					? "/workspace/#sc-preliminary-options"
					: "/workspace/",
		);
		const recordedItems = [
			{ product_id: 4107, quantity: 2 },
			{ product_id: 1946, quantity: 4 },
		];
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
			origin: location.origin,
			async send(path, body) {
				const command = JSON.parse(body);
				if (target === "profile-preliminary" && path === "projects/revise") {
					assert.equal(command.project_id, projectId);
					assert.equal(command.expected_revision, accepted.revision);
					accepted = {
						...accepted,
						revision: accepted.revision + 1,
						inputs: command.inputs,
						input_sha256: "6".repeat(64),
					};
					return accepted;
				}
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
				return saved ? { ...session, kind: "user" } : session;
			},
			async probeScope() {
				return session.query_scope;
			},
			isCurrentScope(scope) {
				return scope === session.query_scope;
			},
			async query(path, body) {
				if (path === "inquiry/form")
					return {
						schema_version: 1,
						inquiry_lines: [],
						inquiry_form_html: `<form method="post" action="/wp-admin/admin-post.php"><input type="hidden" name="linker_preliminary_project" value="${body.project_id}:${body.revision}"><textarea name="message"></textarea><button type="submit">Send inquiry</button></form>`,
					};
				if (path === "recovery/scopes")
					return { schema_version: 1, scopes: [], next: null };
				if (saved && path === "sources/saved-solution") {
					assert.equal(body.solution_id, 45);
					return {
						schema_version: 1,
						solution_id: 45,
						title: "Saved equipment",
						kind: "genie",
						input: {},
						recorded_items: recordedItems,
						source_sha256: "a".repeat(64),
					};
				}
				if (path === "profiles/inspect" || path === "profiles/csv") {
					assert.equal(body.project_id, projectId);
					assert.equal(
						Buffer.from(body.content_base64, "base64").toString(),
						csv,
					);
					if (path === "profiles/inspect")
						return {
							schema_version: 1,
							evaluation_scope: "csv_structure_only",
							content_sha256: "a".repeat(64),
							delimiter: ";",
							columns: ["time", "power"],
							record_count: 1,
							rows: [{ line: 2, cells: ["2026-01-01T00:00Z", "4"] }],
							rows_truncated: false,
						};
					assert.equal(body.source_label, "meter.csv");
				}
				if (
					["profiles/csv", "profiles/standard", "assets/read"].includes(path)
				) {
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
		let pending = null;
		const store = {
			async writeCreation(_scope, body, destination) {
				const { title, key } = JSON.parse(body);
				pending = { title, key, body, destination, createdAt: 1 };
				destinations.push(destination);
			},
			async clearCreation() {
				pending = null;
			},
			async readCreations() {
				return pending ? [pending] : [];
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
		const mount = () =>
			act(async () =>
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
		await mount();
		const start = () => document.querySelector("form");
		await until(() => document.querySelector('select[name="system_scope"]'));
		if (target === "preliminary" || target === "partial" || saved) {
			if (target === "partial") {
				await enter(document.querySelector('[name="location_label"]'), "Oslo");
				for (const [name, value] of [
					["system_scope", "storage_addition"],
					["project_purpose", "self"],
				]) {
					const select = document.querySelector(`select[name="${name}"]`);
					await act(async () => {
						select.value = value;
						select.dispatchEvent(new window.Event("change", { bubbles: true }));
					});
				}
			}
			if (saved) {
				assert.equal(
					document.querySelector('[name="project_title"]').value,
					"Saved equipment",
				);
				assert.doesNotMatch(
					document.body.textContent,
					/Some saved inputs cannot be carried over/,
				);
			}
			const compare = [...document.querySelectorAll("button")].find(
				(button) => button.textContent === "Compare preliminary options",
			);
			assert.ok(
				compare,
				"preliminary options are available with incomplete inputs",
			);
			await until(() => !compare.disabled);
			if (target === "partial") {
				assert.equal(compare.form, start());
				await act(async () => start().requestSubmit());
			} else if (target !== "preliminary")
				await act(async () => compare.click());
			const options = [...document.querySelectorAll("article")].filter(
				(card) =>
					card.querySelector("button")?.textContent === "Choose this option",
			);
			assert.deepEqual(
				options.map((card) => card.querySelector("h3").textContent),
				["Solar and storage", "Storage for existing PV", "Solar", "Storage"],
			);
			assert.match(options[1].textContent, /existing inverter/i);
			assert.match(document.body.textContent, /equipment compatibility/i);
			assert.equal(creates.length, 0);
			await act(async () => options[1].querySelector("button").click());
			await until(() => location.hash === "#sc-preliminary-review");
			assert.deepEqual(destinations, ["review"]);
			assert.equal(creates.length, 1);
			await until(() =>
				document.querySelector(".sc-draft-transfer form textarea"),
			);
			assert.match(
				document.querySelector(".sc-draft-transfer").textContent,
				/Planned system: Storage for existing PV/,
			);
			const inputs = JSON.parse(creates[0]).inputs;
			if (target === "partial") {
				assert.equal(inputs.brief.site.location_label, "Oslo");
				assert.equal(inputs.equipment_setup.grid_phase, null);
				assert.equal(inputs.equipment_setup.operating_mode, "grid_connected");
			} else
				assert.deepEqual(
					Object.keys(inputs),
					saved ? ["brief", "saved_solution_reference"] : ["brief"],
				);
			if (saved) {
				assert.equal(inputs.saved_solution_reference.solution_id, 45);
				assert.deepEqual(
					inputs.saved_solution_reference.recorded_items,
					recordedItems,
				);
			}
			assert.equal(inputs.brief.system_scope, "storage_addition");
			assert.equal(inputs.brief.project_use, null);
			assert.equal(inputs.brief.annual_load.kwh, null);
			assert.equal(inputs.brief.site.country_code, null);
			assert.equal(searches.length, 0);
			return;
		}
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
		if (target === "csv") {
			await choose(
				document.querySelector('[name="system_scope"]'),
				"new_pv_storage",
			);
			const field = (label) =>
				[...document.querySelectorAll("label")]
					.find((el) =>
						el.querySelector("span")?.textContent.trim().startsWith(label),
					)
					?.querySelector("input,select,textarea");
			const openSection = async (title) => {
				const summary = [...document.querySelectorAll("summary")].find(
					(el) => el.textContent === title,
				);
				await act(async () => summary.click());
			};
			await openSection("Solar installation and roof layout");
			await openSection("Solar generation estimate");
			const latitude = field("Latitude");
			await enter(latitude, "1.234,5");
			assert.equal(button("Compare systems").disabled, true);
			await act(async () => start().requestSubmit());
			assert.equal(creates.length, 0);
			assert.equal(searches.length, 0);
			await openSection("Electricity use over time");
			await act(async () => button("Import CSV").click());
			await enter(
				document.querySelector('input[placeholder="Europe/Berlin"]'),
				"Europe/Oslo",
			);
			const file = new File([csv], "meter.csv", { type: "text/csv" });
			await act(async () => {
				const input = field("CSV file");
				Object.defineProperty(input, "files", { value: [file] });
				input.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
			await until(() => !button("Read CSV columns").disabled);
			await act(async () => button("Read CSV columns").click());
			await until(() => field("Timestamp column"));
			for (const [label, value] of [
				["Timestamp column", "time"],
				["Consumption column", "power"],
				["Values represent", "interval_average_kw"],
				["Timestamp marks", "start"],
				["Decimal separator", "."],
				["Data source", "measured"],
			])
				await choose(field(label), value);
			await enter(field("Interval length"), "15");
			await enter(
				field("Source and permission to store privately"),
				"My meter readings",
			);
			assert.equal(button("Use CSV consumption").disabled, false);
			await act(async () => button("Use CSV consumption").click());
			await until(() => !field("Timestamp column"));
			assert.equal(field("Latitude"), latitude);
			assert.equal(latitude.value, "1.234,5");
			assert.equal(button("Compare systems").disabled, true);
			assert.equal(searches.length, 0);
			await enter(latitude, "59,91");
		}
		if (target === "profile" || target === "profile-preliminary") {
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
			if (target === "profile-preliminary") {
				await choose(grid.querySelector("select"), "");
				await act(async () => button("Compare preliminary options").click());
				const storage = [
					...document.querySelectorAll("article.sc-package"),
				].find((card) => card.querySelector("h3")?.textContent === "Storage");
				await act(async () => storage.querySelector("button").click());
				await until(() =>
					document.querySelector(".sc-draft-transfer form textarea"),
				);
				assert.equal(location.hash, "#sc-preliminary-review");
				assert.equal(creates.length, 1);
				assert.equal(searches.length, 0);
				assert.equal(accepted.id, projectId);
				assert.equal(accepted.inputs.brief.annual_load.kwh, 7100);
				assert.equal(accepted.inputs.equipment_setup.grid_phase, null);
				assert.equal(
					accepted.inputs.profile_selections.selected.gross_load,
					"2".repeat(32),
				);
				return;
			}
		}
		assert.ok(!button("Compare systems").disabled);
		await act(async () => {
			button("Compare systems").click();
			button("Compare systems").click();
		});
		if (target === "retry") {
			await until(() => button("Retry project creation"));
			assert.equal(searches.length, 0);
			await act(async () => root.render(null));
			await mount();
			await until(() => button("Retry project creation")?.matches(":enabled"));
			assert.equal(
				creates.length,
				1,
				"a new visit discovers but does not resubmit the command",
			);
			await act(async () => button("Retry project creation").click());
		}
		await until(() => location.hash === "#sc-system");
		assert.equal(new Set(creates).size, 1);
		assert.equal(creates.length, target === "retry" ? 2 : 1);
		assert.ok(
			destinations.every(
				(destination) =>
					destination ===
					(["csv", "profile"].includes(target) ? "edit" : "compare"),
			),
		);
		assert.equal(searches.length, 1);
		assert.equal(JSON.parse(creates[0]).inputs.brief.annual_load.kwh, 6400);
		assert.equal(searches[0].inputs.equipment_setup.grid_phase, 3);
		assert.equal(accepted.title, "Oslo");
		if (target === "csv") {
			assert.equal(
				searches[0].inputs.profile_selections.selected.gross_load,
				"2".repeat(32),
			);
			assert.equal(searches[0].inputs.brief.site.latitude, 59.91);
		}
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
}
