import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";

const session = {
	query_scope: "3".repeat(64),
	runtime: { limits: { max_json_depth: 32, max_body_bytes: 1000000 } },
};
const imagery = {
	tiles: ["https://aerial.example/{z}/{x}/{y}"],
	credit: "Regional orthophotos",
	licence: "Open imagery",
	licence_url: "https://aerial.example/terms",
};
const button = (label) =>
	[...document.querySelectorAll("button")].find(
		(item) => item.textContent === label,
	);
const field = (name) => document.querySelector(`[name="${name}"]`);

async function fixture(t, search = "", locale = "en", home = false) {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { readEntryHints } = await import("../src/domain/entryHints.ts");
	const requests = [],
		records = [],
		opened = [],
		searches = [],
		offeredAreas = [];
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
		async query(path, input) {
			if (path === "places/lookup") {
				offeredAreas.push(input.query);
				return { imagery };
			}
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
						...(home && {
							homeComparison: {
								picker: null,
								savedProject: "",
								compareSaved: () => assert.fail(),
							},
						}),
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
		offeredAreas,
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
			await until(
				() => field("country") && !field("country").matches(":disabled"),
			);
			if (!home && field("project_title"))
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

test("a roof starts from its country and address and opens directly on the located building", async (t) => {
	const page = await fixture(t, "step=roof", "de-DE");
	await page.fill();
	assert.ok(!field("project_title"), "the address names the roof project");
	assert.ok(!field("system_scope"));
	await page.click("Open aerial map");
	await until(() => page.opened.length === 1);
	assert.equal(page.requests.length, 1);
	assert.equal(page.searches.length, 1);
	assert.equal(page.searches[0].languageCode, "de");
	const { project, destination } = page.opened[0];
	assert.equal(destination, "roof");
	assert.equal(project.title, "Karlstraße 1, 80333 München");
	assert.deepEqual(project.inputs.brief.site, {
		country_code: "DE",
		location_label: project.title,
		postal_code: "80333",
		latitude: 48.145,
		longitude: 11.566,
		coordinate_basis: "user_entered",
		timezone: null,
	});
	assert.equal(project.inputs.brief.system_scope, null);
});

test("a roof visitor can compare options without a drawing, address or map consent", async (t) => {
	const page = await fixture(t, "step=roof");
	await until(() => button("Use a roof plan or measurements"));
	const compare = document.querySelector('a[href="?compare=preliminary"]');
	assert.equal(compare?.textContent.trim(), "Compare options");
	assert.equal(page.searches.length, 0);
	assert.equal(page.opened.length, 0);
});

test("comparing from the roof entry keeps the declared site without looking up its address", async (t) => {
	const page = await fixture(t, "step=roof");
	await page.fill("Bergstraße 7, Berlin");
	await act(async () =>
		document.querySelector('a[href="?compare=preliminary"]').click(),
	);
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].destination, "guided-comparison");
	assert.equal(page.opened[0].project.inputs.brief.site.country_code, "DE");
	assert.equal(
		page.opened[0].project.inputs.brief.site.location_label,
		"Bergstraße 7, Berlin",
	);
	assert.equal(page.searches.length, 0);
});

test("a local roof plan opens without an address, a map lookup or imagery consent", async (t) => {
	const page = await fixture(t, "step=roof");
	await until(() => button("Use a roof plan or measurements"));
	await page.click("Use a roof plan or measurements");
	await until(() => page.opened.length === 1);
	assert.equal(page.searches.length, 0);
	assert.equal(page.offeredAreas.length, 0);
	assert.equal(page.opened[0].project.title, "New project");
	assert.equal(page.opened[0].destination, "roof-plan");
	assert.equal(page.opened[0].project.inputs.brief.site.latitude, null);
});

test("from the homepage a country, street address and provider choice open the roof without a comparison", async (t) => {
	const page = await fixture(t, "", "en", true);
	await page.fill("Platz der Republik 1, 11011 Berlin");
	assert.equal(field("project_title").value, "");
	await until(
		() => page.offeredAreas.includes("11011") && field("roof_imagery_consent"),
	);
	assert.ok(document.body.textContent.includes("Regional orthophotos"));
	await act(async () => field("roof_imagery_consent").click());
	await page.click("Open aerial map");
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].destination, "roof");
	assert.equal(page.requests.length, 1);
	assert.equal(
		page.opened[0].project.title,
		page.opened[0].project.inputs.brief.site.location_label,
	);
	assert.equal(page.opened[0].project.inputs.brief.system_scope, null);
	const { takeRoofImageryConsent } =
		await import("../src/data/roofImageryConsent.ts");
	assert.ok(takeRoofImageryConsent(page.opened[0].project.id, imagery));
	assert.equal(
		takeRoofImageryConsent(page.opened[0].project.id, imagery),
		false,
	);
});

test("changing privacy settings withdraws a roof permission before the homepage submission", async (t) => {
	const page = await fixture(t, "", "en", true);
	await page.fill("Platz der Republik 1, 11011 Berlin");
	await until(() => field("roof_imagery_consent"));
	await act(async () => field("roof_imagery_consent").click());
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	assert.equal(field("roof_imagery_consent").checked, false);
	await page.click("Open aerial map");
	await until(() => page.opened.length === 1);
	const { takeRoofImageryConsent } =
		await import("../src/data/roofImageryConsent.ts");
	assert.equal(
		takeRoofImageryConsent(page.opened[0].project.id, imagery),
		false,
	);
});

test("a different imagery source cannot consume the homepage choice as its own permission", async (t) => {
	const page = await fixture(t, "", "en", true);
	await page.fill("Platz der Republik 1, 11011 Berlin");
	await until(() => field("roof_imagery_consent"));
	await act(async () => field("roof_imagery_consent").click());
	await page.click("Open aerial map");
	await until(() => page.opened.length === 1);
	const { takeRoofImageryConsent } =
		await import("../src/data/roofImageryConsent.ts");
	assert.equal(
		takeRoofImageryConsent(page.opened[0].project.id, {
			...imagery,
			tiles: ["https://other.example/{z}/{x}/{y}"],
		}),
		false,
	);
	assert.equal(
		takeRoofImageryConsent(page.opened[0].project.id, imagery),
		false,
	);
});

test("an address without a match stays editable before creating a roof project", async (t) => {
	const page = await fixture(t, "step=roof");
	await page.fill("Missing");
	page.failLookup();
	await page.click("Open aerial map");
	await until(() =>
		document.body.textContent.includes("The location could not be found"),
	);
	assert.equal(page.requests.length, 0);
	assert.equal(field("country").value, "DE");
	assert.equal(field("location_label").value, "Missing");
	assert.equal(field("location_label").matches(":disabled"), false);
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
	await page.click("Open aerial map");
	await until(() => button("Retry project creation"));
	assert.equal(page.records.length, 1);
	const request = page.requests[0];
	await page.reload();
	await until(
		() =>
			button("Retry project creation") &&
			!button("Retry project creation").disabled,
	);
	assert.equal(field("location_label").value, "Karlstraße 1, 80333 München");
	assert.equal(field("location_label").matches(":disabled"), true);
	page.loseReceipt(false);
	await page.click("Retry project creation");
	await until(() => page.opened.length === 1);
	assert.deepEqual(page.requests, [request, request]);
	assert.equal(page.opened[0].destination, "roof");
	assert.equal(page.searches.length, 1);
	assert.equal(page.records.length, 0);
});
