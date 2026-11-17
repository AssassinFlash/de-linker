import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";

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
						openOnLoad: true,
						config: {
							locale,
							countries: { DE: "Germany" },
							googleMapsApiKey: "fixture-google-maps-key",
						},
						entryHints: readEntryHints(new URLSearchParams(search)),
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
			await until(() => !field("project_title").matches(":disabled"));
			await enter(field("project_title"), "Munich PV");
			await act(async () => {
				const country = field("country");
				country.value = "DE";
				country.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
			await enter(field("location_label"), site);
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

test("the old roof link uses the Project form and opens Solar without geocoding", async (t) => {
	const page = await fixture(t, "step=roof");
	await page.fill();
	await page.click("Continue with solar");
	await until(() => page.opened.length === 1);
	assert.equal(page.requests.length, 1);
	assert.equal(page.searches.length, 0);
	assert.equal(page.opened[0].destination, "design");
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
	await page.click("Continue with solar");
	await until(() => page.opened.length === 1);
	assert.equal(page.requests.length, 1);
	assert.equal(
		page.opened[0].project.inputs.equipment_setup.inverter_product_id,
		42,
	);
	assert.equal(page.opened[0].destination, "design");
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
	await page.click("Continue with solar");
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, 48.145);
});

test("an unsuccessful optional coordinate search leaves Continue usable", async (t) => {
	const page = await fixture(t);
	await page.fill();
	page.failLookup();
	await page.click("Find site coordinates");
	await until(() =>
		document.body.textContent.includes("The location could not be found"),
	);
	await page.click("Continue with solar");
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, null);
});

test("a lost creation reply is retried using the original request after reload", async (t) => {
	const page = await fixture(t, "step=roof");
	page.loseReceipt(true);
	await page.fill();
	await page.click("Continue with solar");
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
	page.loseReceipt(false);
	await page.click("Retry project creation");
	await until(() => page.opened.length === 1);
	assert.deepEqual(page.requests, [request, request]);
	assert.equal(page.opened[0].destination, "design");
	assert.equal(page.records.length, 0);
});
