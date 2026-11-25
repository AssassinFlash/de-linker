import { expect, test, vi } from "vitest";
import { act, createElement } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, enter, until } from "../dom-fixture.mjs";
import { DraftStore } from "../../src/data/DraftStore.ts";

test("the system comparison uses the capacity edited after entering project details", async () => {
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
	const comparedCapacities = [];
	const client = {
		origin: location.origin,
		isCurrentScope: (value) => value === scope,
		bootstrap: async () => session,
		probeScope: async () => scope,
		invalidate() {},
		query: async (operation) => {
			if (operation === "projects/list" || operation === "projects/runs")
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
					revision: (project?.revision ?? 0) + 1,
					title: command.title ?? project.title,
					inputs: command.inputs,
					input_sha256: sha,
				};
				if (operation !== "runs/find-equipment") return project;
				comparedCapacities.push(project.inputs.equipment_setup.pv_dc_kw);
				const kind = "search_woo_equipment_v1";
				run = {
					id: "b".repeat(32),
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
							completion: "complete",
							work_used: 0,
							work_budget: 1000,
							candidates: [],
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
		await until(() => button(name)?.matches(":enabled"));
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
					createElement(Workspace, { session, recheck, client, store, config }),
				),
			),
		);
		await until(() => button("Enter project details"));
		await select("project_start", "known");
		await select("project_country", "IT");
		await enter(page.element.querySelector('[name="annual_load_kwh"]'), "7200");
		await select("annual_load_basis", "user_estimate");
		await enter(page.element.querySelector('[name="site_pv_kw"]'), "11.09");
		await select("grid_phase", "3");
		await select("project_purpose", "self");
		await click("Enter project details");
		await until(() => page.element.querySelector('[name="location_label"]'));
		await enter(
			page.element.querySelector('[name="location_label"]'),
			"Torino",
		);
		await click("Compare systems");
		await until(() => button("Fine-tune (optional)") || button("Roof & PV"));
		if (!button("Roof & PV")) await click("Fine-tune (optional)");
		await click("Roof & PV");
		await until(() => page.element.querySelector(".sc-solar-inputs input"));
		expect(location.hash).toBe("#sc-solar");
		expect(project.inputs.brief.site.country_code).toBe("IT");
		expect(project.inputs.brief.annual_load.kwh).toBe(7200);
		const capacity = page.element.querySelector(".sc-solar-inputs input");
		expect(capacity.value).toBe("11.09");
		await enter(capacity, "13.7");
		await click("Continue with energy use");
		await click("Compare systems");
		await until(() => comparedCapacities.at(-1) === 13.7);
		expect(run.state).toBe("succeeded");
		expect(run.revision).toBe(project.revision);
		expect(comparedCapacities.at(-1)).toBe(13.7);
		expect(project.inputs.equipment_setup.pv_dc_kw).toBe(13.7);
		expect(project.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp).toBe(
			13.7,
		);
	} finally {
		await page.dispose(root);
		vi.unstubAllGlobals();
	}
}, 30_000);
