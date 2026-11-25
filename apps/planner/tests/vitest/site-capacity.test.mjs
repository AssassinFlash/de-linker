import { authoredDiscoveryInputs } from "../../src/domain/currentCalculation.ts";
import { expect, test, vi } from "vitest";
import { act, createElement } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, enter } from "../dom-fixture.mjs";
import { DraftStore } from "../../src/data/DraftStore.ts";

async function until(label, predicate) {
	await vi.waitFor(
		async () => {
			await act(async () => {
				await new Promise((resolve) => setTimeout(resolve, 0));
			});
			expect(Boolean(predicate()), label).toBe(true);
		},
		{ timeout: 10_000 },
	);
}

test.each(["result shown", "result in flight"])(
	"the edited solar capacity reaches comparison after project details (%s)",
	async (timing) => {
		const page = setupDom();
		vi.stubGlobal("indexedDB", new IDBFactory());
		vi.stubGlobal("requestAnimationFrame", window.requestAnimationFrame);
		vi.stubGlobal("cancelAnimationFrame", window.cancelAnimationFrame);
		vi.stubGlobal("getComputedStyle", window.getComputedStyle.bind(window));
		history.replaceState({}, "", "/solution-configurator/");
		const { createRoot } = await import("react-dom/client");
		const { SessionBoundary } =
			await import("../../src/components/SessionBoundary.tsx");
		const { Workspace } = await import("../../src/components/Workspace.tsx");
		const root = createRoot(page.element);
		const scope = "1".repeat(64);
		const id = "a".repeat(32);
		const sha = "2".repeat(64);
		const session = {
			schema_version: 1,
			kind: "guest",
			cookie_confirmed: true,
			expires_at: 2000000000,
			query_scope: scope,
			nonce: "abcdefghij",
			claim_pending: false,
			runtime: {
				schema_version: 1,
				runtime_sha256: sha,
				models: {},
				limits: {
					max_body_bytes: 1000000,
					max_csv_bytes: 100000,
					max_page_size: 30,
					max_json_depth: 32,
				},
			},
		};
		let project, run;
		let inFlight = false;
		const initialReply = Promise.withResolvers();
		let comparedCapacity;
		const client = {
			origin: location.origin,
			isCurrentScope: (value) => value === scope,
			bootstrap: async () => session,
			probeScope: async () => scope,
			invalidate() {},
			query: async (operation) => {
				if (operation === "projects/runs") return { items: [], next: null };
				if (operation === "projects/list")
					return { schema_version: 1, items: [], next: null };
				if (operation === "projects/read") return project;
				if (operation === "products/current")
					return {
						schema_version: 1,
						provider: "woocommerce",
						products: [],
						battery_assemblies: {},
						dc_battery_ports: {},
						parallel_controller_product_ids: [],
						cable_references: [],
						figure_projection_version: 2,
						compatibility_origin: "woocommerce",
					};
				if (operation === "places/lookup")
					return { imagery: null, viewing_imagery: null };
				if (operation === "runs/read") return run;
				if (operation === "runs/inputs")
					return {
						schema_version: 1,
						project_id: id,
						run_id: run.id,
						manifest_sha256: sha,
						inputs: project.inputs,
					};
				throw new Error(operation);
			},
			send: async (operation, body) => {
				const command = JSON.parse(body);
				if (
					operation === "projects/create" ||
					operation === "projects/revise" ||
					operation === "runs/find-equipment"
				) {
					project = {
						id,
						revision: command.expected_revision
							? command.expected_revision + 1
							: 1,
						title: command.title ?? project.title,
						inputs:
							operation === "runs/find-equipment"
								? authoredDiscoveryInputs(command.inputs)
								: command.inputs,
						input_sha256: sha,
					};
					if (operation !== "runs/find-equipment") return project;
					if (timing === "result in flight" && !inFlight) {
						inFlight = true;
						await initialReply.promise;
					}
					comparedCapacity = project.inputs.equipment_setup.pv_dc_kw;
					const kind = "search_woo_equipment_v1";
					run = {
						id: project.revision.toString(16).padStart(32, "0"),
						project_id: id,
						revision: project.revision,
						state: "succeeded",
						is_current: true,
						manifest_sha256: sha,
						result_sha256: sha,
						manifest: {
							schema: 1,
							project_id: id,
							revision: project.revision,
							input_sha256: sha,
							context: {
								code_sha256: sha,
								models: { task: kind },
								assets: { "woo.equipment_inputs": sha },
								parameters: { kind },
							},
						},
						result: {
							schema: 1,
							kind,
							project_id: id,
							revision: project.revision,
							input_sha256: sha,
							manifest_sha256: sha,
							runtime_sha256: sha,
							pinned_assets: { "woo.equipment_inputs": sha },
							search: {
								coverage: {
									template: "one_converter_one_external_battery_assembly",
									gaps: {},
								},
								completion: "exhausted_supported_domain",
								work_used: 0,
								work_budget: 1000,
								candidates: [],
								qualified_count: 0,
								products: [],
								ranking: "not_performed_before_qualification",
							},
						},
						error: null,
					};
					return { schema_version: 1, project, run };
				}
				throw new Error(operation);
			},
		};
		const button = (name) =>
			[...page.element.querySelectorAll("button")].find(
				(b) =>
					(b.textContent.replace(/^\d+/, "").trim() === name ||
						b.getAttribute("aria-label") === name) &&
					!b.closest("[hidden]"),
			);
		const click = async (name) => {
			await until(name, () => button(name)?.matches(":enabled"));
			await act(async () => button(name).click());
		};
		const select = async (name, value) => {
			const el = page.element.querySelector("select[name=" + name + "]");
			await act(async () => {
				el.value = value;
				el.dispatchEvent(new Event("change", { bubbles: true }));
			});
		};
		const config = {
			baseUrl: location.origin + "/api/",
			nonceUrl: location.origin + "/nonce",
			locale: "en",
			countries: { IT: "Italy" },
		};
		const store = new DraftStore();
		try {
			await act(async () =>
				root.render(
					createElement(SessionBoundary, { client }, (session, recheck) =>
						createElement(Workspace, {
							session,
							recheck,
							client,
							store,
							config,
						}),
					),
				),
			);
			await until("intake", () => button("Enter project details"));
			await select("project_start", "known");
			await select("project_country", "IT");
			await enter(
				page.element.querySelector('[name="annual_load_kwh"]'),
				"7200",
			);
			await select("annual_load_basis", "user_estimate");
			await enter(page.element.querySelector('[name="site_pv_kw"]'), "11.09");
			await select("grid_phase", "3");
			await select("project_purpose", "self");
			await click("Enter project details");
			await until("project details", () =>
				page.element.querySelector('[name="location_label"]'),
			);
			await enter(
				page.element.querySelector('[name="location_label"]'),
				"Torino",
			);
			await click("Compare systems");
			if (timing === "result in flight")
				await until("first comparison in flight", () => inFlight);
			else {
				await until("initial results shown", () =>
					page.element.textContent.includes(
						"No configurations were found using the available product data.",
					),
				);
				expect(comparedCapacity).toBe(11.09);
			}
			await until(
				"workbench navigation",
				() => button("Fine-tune (optional)") || button("Roof & PV"),
			);
			if (!button("Roof & PV")) await click("Fine-tune (optional)");
			await click("Roof & PV");
			await until("solar capacity field", () =>
				page.element.querySelector(".sc-solar-inputs input"),
			);
			if (timing === "result in flight") {
				initialReply.resolve();
				await until(
					"solar field ready after comparison",
					() =>
						page.element
							.querySelector(".sc-solar-inputs input")
							?.matches(":enabled") && comparedCapacity === 11.09,
				);
			}
			expect(location.hash).toBe("#sc-solar");
			expect(project.inputs.brief.site.country_code).toBe("IT");
			expect(project.inputs.brief.annual_load.kwh).toBe(7200);
			const capacity = page.element.querySelector(".sc-solar-inputs input");
			expect(capacity.value).toBe("11.09");
			const sidebarCapacity = () =>
				[...page.element.querySelectorAll("aside dt")].find(
					(dt) => dt.textContent === "Solar capacity",
				)?.nextElementSibling?.textContent;
			expect(sidebarCapacity()).toBe("11.09 kWp");
			await enter(capacity, "13.7");
			expect(sidebarCapacity()).toBe("13.7 kWp");
			await click("Continue with energy use");
			await click("Compare systems");
			await until("accepted equipment comparison", () =>
				page.element.textContent.includes(
					"No configurations were found using the available product data.",
				),
			);
			expect(run.state).toBe("succeeded");
			expect(run.revision).toBe(project.revision);
			expect(comparedCapacity).toBe(13.7);
			expect(project.inputs.equipment_setup.pv_dc_kw).toBe(13.7);
			expect(
				project.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp,
			).toBe(13.7);
		} finally {
			initialReply.resolve();
			await page.dispose(root);
			vi.unstubAllGlobals();
		}
	},
	30_000,
);
