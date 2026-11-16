import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";

const session = {
	query_scope: "3".repeat(64),
	runtime: { limits: { max_json_depth: 32, max_body_bytes: 1000000 } },
};
const address = "Karlstraße 1, 80333 München, Germany";
const geocoded = (country = "DE") => ({
	formattedAddress: address,
	addressComponents: [
		{ longText: "Germany", shortText: country, types: ["country"] },
		{ longText: "80333", shortText: "80333", types: ["postal_code"] },
	],
	location: { latitude: 48.145, longitude: 11.566 },
});
const button = (label) =>
	[...document.querySelectorAll("button")].find(
		(item) => item.textContent === label,
	);

async function fixture(t, options = {}) {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { readBrief } = await import("../src/domain/brief.ts");
	const requests = [],
		searches = [],
		records = [],
		opened = [];
	let lookup = async () => ({ places: [geocoded()] });
	let createFailure = false;
	const originalFetch = globalThis.fetch;
	globalThis.fetch = async (url, init) => {
		assert.equal(url, "https://places.googleapis.com/v1/places:searchText");
		assert.equal(init.method, "POST");
		assert.equal(init.headers["X-Goog-Api-Key"], "fixture-google-maps-key");
		assert.equal(
			init.headers["X-Goog-FieldMask"],
			"places.formattedAddress,places.location,places.addressComponents",
		);
		const request = JSON.parse(init.body);
		searches.push(request);
		const result = await lookup(request);
		if (result instanceof Response) return result;
		return new Response(JSON.stringify(result), {
			headers: { "Content-Type": "application/json" },
		});
	};
	t.after(() => {
		globalThis.fetch = originalFetch;
	});
	const client = {
		isCurrentScope: (scope) => scope === session.query_scope,
		async send(path, body, scope) {
			assert.equal(path, "projects/create");
			assert.equal(scope, session.query_scope);
			assert.equal(records[0].body, body, "recovery is written before sending");
			requests.push(body);
			if (createFailure) throw new Error("response_lost");
			const command = JSON.parse(body);
			readBrief(command.inputs.brief);
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
			const command = JSON.parse(body);
			if (!records.some((record) => record.body === body))
				records.push({
					key: command.key,
					title: command.title,
					body,
					destination,
					createdAt: 1,
				});
		},
		async clearCreation(scope, body) {
			assert.equal(scope, session.query_scope);
			const index = records.findIndex((record) => record.body === body);
			assert.notEqual(index, -1);
			records.splice(index, 1);
		},
	};
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
	});
	async function render() {
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: queryClient },
					React.createElement(NewProject, {
						session,
						client,
						store,
						openOnLoad: true,
						roofStart: {
							locale: "en",
							countries: { DE: "Germany", FR: "France" },
							googleMapsApiKey: "fixture-google-maps-key",
						},
						created: (project, destination) => {
							opened.push({ project, destination });
							return true;
						},
						recheck: () => assert.fail("unexpected session recheck"),
						...options,
					}),
				),
			),
		);
	}
	await render();
	return {
		requests,
		searches,
		records,
		opened,
		setLookup: (next) => {
			lookup = next;
		},
		setCreateFailure: (next) => {
			createFailure = next;
		},
		async fill(country = "DE", value = "Karlstraße 1, München") {
			await act(async () => {
				const select = document.querySelector(".lp-roof-start select");
				select.value = country;
				select.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
			await enter(document.querySelector(".lp-roof-start input"), value);
			await until(() => !button("Open roof map").disabled);
		},
		async submit() {
			await act(async () =>
				document
					.querySelector("form")
					.dispatchEvent(
						new window.Event("submit", { bubbles: true, cancelable: true }),
					),
			);
		},
		async reload() {
			await act(async () => root.render(null));
			await render();
		},
	};
}

test("country and real address create a roof project without sizing inputs", async (t) => {
	const page = await fixture(t);
	assert.equal(button("Open roof map").disabled, true);
	await page.submit();
	assert.equal(page.requests.length, 0);
	assert.equal(page.searches.length, 0);
	await page.fill();
	await page.submit();
	await until(() => page.opened.length === 1);
	assert.deepEqual(page.searches, [
		{
			textQuery: "Karlstraße 1, München",
			languageCode: "en",
			regionCode: "DE",
		},
	]);
	assert.equal(page.opened[0].destination, "design");
	assert.equal(page.opened[0].project.title, address);
	assert.deepEqual(page.opened[0].project.inputs.brief.site, {
		country_code: "DE",
		location_label: address,
		latitude: 48.145,
		longitude: 11.566,
		coordinate_basis: "user_entered",
		timezone: null,
	});
	assert.deepEqual(Object.keys(page.opened[0].project.inputs), ["brief"]);
	assert.equal(page.opened[0].project.inputs.brief.annual_load.kwh, null);
	assert.equal(page.records.length, 0);
});

test("German roof entry requests German addresses for the saved title and location", async (t) => {
	const page = await fixture(t, {
		roofStart: {
			locale: "de-DE",
			countries: { DE: "Deutschland" },
			googleMapsApiKey: "fixture-google-maps-key",
		},
	});
	const germanAddress = "Karlstraße 1, 80333 München, Deutschland";
	page.setLookup(async ({ languageCode }) => {
		assert.equal(languageCode, "de");
		return { places: [{ ...geocoded(), formattedAddress: germanAddress }] };
	});
	await page.fill();
	await page.submit();
	await until(() => page.opened.length === 1);
	assert.equal(page.opened[0].project.title, germanAddress);
	assert.equal(
		page.opened[0].project.inputs.brief.site.location_label,
		germanAddress,
	);
});

test("address failures keep the input editable and do not create a project", async (t) => {
	const page = await fixture(t);
	await page.fill();
	page.setLookup(async () => ({ places: [geocoded("FR")] }));
	await page.submit();
	await until(() =>
		document.body.textContent.includes("We could not find that address"),
	);
	assert.equal(page.requests.length, 0);
	assert.equal(
		document.querySelector(".lp-roof-start input").value,
		"Karlstraße 1, München",
	);
	page.setLookup(async () => {
		return new Response(
			JSON.stringify({ error: { status: "REQUEST_DENIED" } }),
			{ status: 403 },
		);
	});
	await page.submit();
	await until(() =>
		document.body.textContent.includes("Address search is unavailable"),
	);
	assert.equal(page.requests.length, 0);
	page.setLookup(async () => ({ places: [] }));
	await page.submit();
	await until(() =>
		document.body.textContent.includes("We could not find that address"),
	);
	assert.equal(page.requests.length, 0);
	page.setLookup(async () => ({ places: [geocoded()] }));
	await page.fill("DE", "Karlstraße 1, 80333 München");
	await page.submit();
	await until(() => page.opened.length === 1);
});

test("a lost creation reply reloads and retries the same project and roof destination", async (t) => {
	const page = await fixture(t);
	page.setCreateFailure(true);
	await page.fill();
	await page.submit();
	await until(() => button("Retry project creation"));
	assert.equal(page.records.length, 1);
	assert.equal(page.records[0].destination, "design");
	assert.equal(page.opened.length, 0);
	const originalRequest = page.requests[0];
	await page.reload();
	await until(
		() =>
			button("Retry project creation") &&
			!button("Retry project creation").disabled,
	);
	assert.equal(document.querySelector("input").value, address);
	assert.equal(document.querySelector("input").readOnly, true);
	page.setCreateFailure(false);
	await page.submit();
	await until(() => page.opened.length === 1);
	assert.deepEqual(page.requests, [originalRequest, originalRequest]);
	assert.equal(
		page.searches.length,
		1,
		"retry must not relocate the saved site",
	);
	assert.equal(page.opened[0].destination, "design");
	assert.equal(page.records.length, 0);
});
