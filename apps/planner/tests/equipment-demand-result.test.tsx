import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EquipmentSearchResult } from "../src/components/equipment/EquipmentSearchResult.tsx";
import { setupDom, until } from "./dom-fixture.mjs";

// Two configurations share their compatibility status but meet different loads.
test("customers can filter demand results independently of equipment compatibility", async () => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	const query = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const candidate = (id, capacity, unmet) => ({
		id: id.repeat(64),
		assessment_sha256: "a".repeat(64),
		status: "unresolved",
		violated_checks: 0,
		unresolved_checks: 1,
		usable_energy_kwh: capacity,
		selection: { inverter_product_id: 1, battery_product_id: 2 },
		demand: {
			status: unmet ? "violated" : "satisfied",
			reason: unmet ? "unserved_load_exceeds_target" : "target_met",
			metrics: {
				unserved_load_kwh: unmet,
				maximum_interval_average_import_kw: 0,
				load_demand_kwh: 8,
			},
			equipment: { assessment: { overall_status: "unresolved", checks: [] } },
		},
	});
	const run = {
		id: "1".repeat(32),
		project_id: "2".repeat(32),
		revision: 2,
		state: "succeeded",
		kind: "search_woo_equipment_v1",
		is_current: true,
		manifest: { context: { parameters: { kind: "search_woo_equipment_v1" } } },
		result: {
			search: {
				coverage: {
					template: "one_converter_one_external_battery_assembly",
					gaps: {},
				},
				completion: "exhausted_supported_domain",
				products: [
					{ canonical_product_id: 1, brand: "Fixture", model: "Converter" },
					{ canonical_product_id: 2, brand: "Fixture", model: "Battery" },
				],
				candidates: [candidate("b", 5, 3), candidate("c", 10, 0)],
				demand: {
					model: "single_ac_equipment_demand_v1",
					completion: "complete",
					interval_count: 3,
					work_used: 6,
					work_budget: 100,
				},
			},
		},
	};
	try {
		await act(async () =>
			root.render(
				<QueryClientProvider client={query}>
					<EquipmentSearchResult
						run={run}
						locale="en"
						dirty={false}
						confirmedRevision={2}
						client={{ isCurrentScope: () => false }}
						scope="fixture"
						disabled={false}
						apply={async () => {}}
						onError={() => {}}
					/>
				</QueryClientProvider>,
			),
		);
		await until(() =>
			dom.element.textContent.includes("Equipment combination"),
		);
		const filter = [...dom.element.querySelectorAll("label")]
			.find((label) => label.textContent.includes("Demand results"))
			?.querySelector("select");
		assert.ok(
			filter,
			"customers can narrow candidates by their actual demand result",
		);
		assert.match(dom.element.textContent, /Unserved load[^]*3 kWh/);
		await act(async () => {
			filter.value = "satisfied";
			filter.dispatchEvent(new Event("change", { bubbles: true }));
		});
		const picker = [...dom.element.querySelectorAll("label")]
			.find(
				(label) =>
					label.querySelector("span")?.textContent === "Equipment combination",
			)
			?.querySelector("select");
		assert.equal(picker.options.length, 1);
		assert.match(picker.options[0].textContent, /10 kWh/);
		assert.match(dom.element.textContent, /Unserved load[^]*0 kWh/);
		assert.match(
			dom.element.textContent,
			/Equipment evidence remains unresolved/,
		);
	} finally {
		await act(async () => root.unmount());
		query.clear();
		await dom.dispose({ unmount: async () => {} });
	}
});
