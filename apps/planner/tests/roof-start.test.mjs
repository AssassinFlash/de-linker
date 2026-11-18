import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";

register("./map-library-loader.mjs", import.meta.url);

const session = {
	query_scope: "3".repeat(64),
	runtime: { limits: { max_json_depth: 32, max_body_bytes: 1000000 } },
};
const button = (label) =>
	[...document.querySelectorAll("button")].find(
		(item) => item.textContent === label,
	);
const field = (name) => document.querySelector(`[name="${name}"]`);

async function fixture(t, search = "", locale = "en") {
	const dom = setupDom();
	window.history.replaceState(
		{},
		"",
		`/workspace/${search ? `?${search}` : ""}`,
	);
	const { createRoot } = await import("react-dom/client");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { readEntryHints } = await import("../src/domain/entryHints.ts");
	const requests = [],
		records = [],
		opened = [],
		searches = [];
	let createFailure = false,
		lookupFailure = false;
	const originalFetch = globalThis.fetch;
	globalThis.fetch = async (url, init) => {
		assert.equal(url, "https://places.googleapis.com/v1/places:searchText");
		searches.push(JSON.parse(init.body));
		return Response.json({
			places: lookupFailure
				? []
				: [
						{
							formattedAddress: "Karlstraße 1, 80333 München",
							addressComponents: [
								{ shortText: "DE", types: ["country"] },
								{ shortText: "80333", types: ["postal_code"] },
							],
							location: { latitude: 48.145, longitude: 11.566 },
						},
					],
		});
	};
	t.after(() => {
		globalThis.fetch = originalFetch;
	});
	const client = {
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path) {
			assert.equal(path, "products/current");
			return {
				schema_version: 1,
				provider: "woocommerce",
				figure_projection_version: 2,
				compatibility_origin: "woocommerce",
				products: [
					{
						id: 42,
						canonical_product_id: 42,
						product_revision: "a".repeat(64),
						brand: "Fixture",
						model: "PV 42",
						device_class: "inverters",
						figures: {},
					},
				],
			};
		},
		async send(path, body, scope) {
			assert.equal(path, "projects/create");
			assert.equal(scope, session.query_scope);
			assert.equal(records[0].body, body, "persist recovery before sending");
			requests.push(body);
			if (createFailure) throw new Error("response_lost");
			const command = JSON.parse(body);
			return {
				id: "1".repeat(32),
				revision: 1,
				input_sha256: "2".repeat(64),
				title: command.title,
				inputs: command.inputs,
			};
		},
	};
	const store = {
		async readCreations() {
			return [...records];
		},
		async writeCreation(scope, body, destination) {
			assert.equal(scope, session.query_scope);
			const { key, title } = JSON.parse(body);
			if (!records.some((entry) => entry.body === body))
				records.push({ key, title, body, destination, createdAt: 1 });
		},
		async clearCreation(scope, body) {
			assert.equal(scope, session.query_scope);
			const index = records.findIndex((entry) => entry.body === body);
			assert.notEqual(index, -1);
			records.splice(index, 1);
		},
	};
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
	});
	const render = () =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(NewProject, {
						session,
						client,
						store,

						config: {
							locale,
							countries: { DE: "Germany" },
							googleMapsApiKey: "fixture-google-maps-key",
						},
						entryHints: readEntryHints(new URLSearchParams(location.search)),
						created: (project, destination) => {
							opened.push({ project, destination });
							return true;
						},
						recheck: () => assert.fail("unexpected session recheck"),
					}),
				),
			),
		);
	await render();
	return {
		requests,
		records,
		opened,
		searches,
		loseReceipt: (value) => {
			createFailure = value;
		},
		failLookup: () => {
			lookupFailure = true;
		},
		async fill(site = "Karlstraße 1, München") {
			const dialog = document.querySelector("dialog[open]");
			if (dialog) await act(async () => button("Close").click());
			await act(async () =>
				field("project_title")
					.closest("details")
					.querySelector("summary")
					.click(),
			);
			await until(() => !field("project_title").matches(":disabled"));
			await enter(field("project_title"), "Munich PV");
			await act(async () => {
				const country = field("country");
				country.value = "DE";
				country.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
			await enter(field("location_label"), site);
		},
		async compare() {
			async function choose(select, value) {
				await act(async () => {
					select.value = value;
					select.dispatchEvent(new window.Event("change", { bubbles: true }));
				});
			}
			if (!field("system_scope").value)
				await choose(field("system_scope"), "new_pv_storage");
			await choose(field("project_purpose"), "self");
			const phase = [...document.querySelectorAll("label")].find(
				(label) =>
					label.querySelector("span")?.textContent === "Grid connection",
			);
			await choose(phase.querySelector("select"), "3");
			const compare = button("Compare systems");
			assert.ok(compare && !compare.disabled);
			await act(async () => compare.click());
		},
		async click(label) {
			await act(async () => button(label).click());
		},
		async reload() {
			await act(async () => root.render(null));
			await render();
		},
	};
}

test("the old roof link uses the Project form and opens roof design before creation without geocoding", async (t) => {
	const page = await fixture(t, "step=roof");
	await until(() => button("Coordinate references"));
	assert.ok(
		button("Coordinate references").closest(
			'#sc-solar dialog[open][aria-label="Roof design"]',
		),
	);
	assert.equal(page.requests.length, 0);
	await page.fill();
	await page.compare();
	await until(() => page.opened.length === 1);
	assert.equal(page.requests.length, 1);
	assert.equal(page.searches.length, 0);
	assert.equal(page.opened[0].destination, "compare");
	assert.equal(page.opened[0].project.title, "Munich PV");
	assert.equal(
		page.opened[0].project.inputs.brief.site.location_label,
		"Karlstraße 1, München",
	);
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, null);
});

test("the old product link carries a current product into the same Project form", async (t) => {
	const page = await fixture(t, "step=equipment&product_id=42&plz=80333");
	await until(() => document.body.textContent.includes("Fixture PV 42"));
	assert.equal(field("location_label").value, "80333");
	await page.fill();
	await page.compare();
	await until(() => page.opened.length === 1);
	assert.equal(page.requests.length, 1);
	assert.equal(
		page.opened[0].project.inputs.equipment_setup.inverter_product_id,
		42,
	);
	assert.equal(page.opened[0].destination, "compare");
});

test("coordinates can be looked up in German from the shared Project form", async (t) => {
	const page = await fixture(t, "", "de-DE");
	await page.fill();
	await page.click("Find site coordinates");
	await until(() =>
		document.body.textContent.includes("Site coordinates found"),
	);
	assert.equal(page.searches[0].languageCode, "de");
	assert.equal(page.requests.length, 0);
	await page.compare();
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, 48.145);
	assert.equal(page.opened[0].project.inputs.brief.site.longitude, 11.566);
});

test("an unsuccessful optional coordinate search still lets the customer compare", async (t) => {
	const page = await fixture(t);
	await page.fill();
	page.failLookup();
	await page.click("Find site coordinates");
	await until(() =>
		document.body.textContent.includes("The location could not be found"),
	);
	await page.compare();
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, null);
});

test("a lost creation reply is retried using the original request after reload", async (t) => {
	const page = await fixture(t, "step=roof");
	page.loseReceipt(true);
	await page.fill();
	await page.compare();
	await until(() => button("Retry project creation"));
	assert.equal(page.records.length, 1);
	const request = page.requests[0];
	await page.reload();
	await until(
		() =>
			button("Retry project creation") &&
			!button("Retry project creation").disabled,
	);
	assert.equal(field("project_title").value, "Munich PV");
	assert.equal(field("project_title").readOnly, true);
	assert.deepEqual(page.requests, [request], "reload must not send again");
	page.loseReceipt(false);
	await page.click("Retry project creation");
	await until(() => page.opened.length === 1);
	assert.deepEqual(page.requests, [request, request]);
	assert.equal(page.opened[0].destination, "compare");
	assert.equal(page.records.length, 0);
});
