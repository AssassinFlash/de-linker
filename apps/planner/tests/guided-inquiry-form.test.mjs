import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";

test("a selected report shows the quantities to send in the only inquiry form", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const { ReviewInquiry } =
		await import("../src/components/configurator/ReviewInquiry.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const brief = emptyBrief();
	const project = {
		id: "2".repeat(32),
		revision: 3,
		inputs: {
			existing_system: {
				schema_version: 1,
				name: "Installed inverter",
				inverter_power_kw: 3,
				keep_inverter: true,
			},
			brief: {
				...brief,
				system_scope: "storage_addition",
				site: { ...brief.site, country_code: "NL", location_label: "Utrecht" },
				annual_load: { ...brief.annual_load, kwh: 6412 },
			},
		},
	};
	const reportRunId = "3".repeat(32);
	const binding =
		reportRunId +
		":" +
		"4".repeat(32) +
		":11111111-1111-4111-8111-111111111111:" +
		"5".repeat(64);
	const requests = [];
	const client = {
		origin: "https://fixture.invalid",
		isCurrentScope: () => true,
		async query(path, input) {
			requests.push([path, input]);
			return {
				schema_version: 1,
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php">
					<input type="hidden" name="linker_preliminary_project" value="${project.id}:3">
					<input type="hidden" name="linker_report_transfer" value="${binding}">
					<button type="submit">Send inquiry</button></form>`,
				inquiry_project_facts: [
					{ label: "Location", value: "Utrecht, NL" },
					{ label: "Annual electricity use", value: "6412 kWh" },
					{ label: "Continuous discharge power", value: "5 kW" },
				],
				inquiry_lines: [
					{
						product_id: 42,
						label: "Selected inverter",
						quantity: 4,
						project_id: project.id,
					},
					{
						product_id: 55,
						label: "Existing draft cable",
						product_url: "https://fixture.invalid/product/cable/",
						image_url: "https://fixture.invalid/uploads/cable.png",
						highlight: "Outdoor DC cable",
						quantity: 2,
						project_id: null,
					},
				],
				inquiry_changes: [
					{ product_id: 42, label: "Selected inverter", before: 2, after: 4 },
				],
			};
		},
	};
	await act(async () =>
		root.render(
			React.createElement(ReviewInquiry, {
				project,
				reportRunId,
				direction: "storage_addition",
				client,
				scope: "owned",
				locale: "en",
				active: true,
				changeSelection() {},
				recheck() {},
			}),
		),
	);
	await until(() => fixture.element.querySelector(".linker-inquiry-form"));
	assert.deepEqual(requests, [
		[
			"inquiry/form",
			{
				schema_version: 1,
				lang: "en",
				project_id: project.id,
				revision: 3,
				report_run_id: reportRunId,
			},
		],
	]);
	const cable = fixture.element.querySelector(
		'a[href="https://fixture.invalid/product/cable/"]',
	);
	assert.match(cable?.textContent ?? "", /Existing draft cable/);
	assert.equal(
		cable
			.closest(".linker-inquiry-line")
			.querySelector(".linker-inquiry-line-controls")
			.textContent.trim(),
		"× 2",
	);
	assert.equal(
		cable.querySelector("img")?.getAttribute("src"),
		"https://fixture.invalid/uploads/cable.png",
	);
	assert.equal(cable.title, "Outdoor DC cable");
	assert.match(
		fixture.element.querySelector("aside .sc-review-choice").textContent,
		/Keep the existing inverter/,
	);
	const summary = fixture.element.querySelector("aside details");
	assert.equal(
		summary?.querySelector("summary")?.textContent.trim(),
		"Project details",
	);
	assert.equal(
		fixture.element.querySelectorAll("form .sc-project-facts").length,
		0,
	);
	const projectDetails = summary.querySelector("dl.sc-project-facts");
	assert.match(projectDetails.textContent, /Continuous discharge power5 kW/);
	assert.match(projectDetails?.textContent ?? "", /Utrecht/);
	assert.match(projectDetails?.textContent ?? "", /6412 kWh/);
	const row = Array.from(fixture.element.querySelectorAll("tbody tr")).find(
		(r) => r.textContent.includes("Selected inverter"),
	);
	assert.deepEqual(
		Array.from(row.cells, (cell) => cell.textContent),
		["Selected inverter", "2", "4"],
	);
	assert.equal(
		fixture.element.querySelectorAll("button[type=submit]").length,
		1,
	);
	assert.equal(
		fixture.element.querySelector("button[type=submit]").textContent,
		"Send inquiry",
	);
});
