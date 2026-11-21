import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import { setupDom } from "./dom-fixture.mjs";

const config = { googleMapsApiKey: "fixture-key", locale: "de-DE" };
const street = "Am Sandtorkai 1, Hamburg";

function place(country, location, formattedAddress) {
	return {
		formattedAddress,
		location,
		addressComponents: [
			{ shortText: country, types: ["country"] },
			{ shortText: "20457", types: ["postal_code"] },
		],
	};
}

test("one homepage comparison resolves the disclosed street address within the chosen country", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const {
		HomepagePvReference,
		isHomepagePvReferenceReady,
		prepareHomepagePvReference,
	} = await import("../src/components/configurator/HomepagePvReference.tsx");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));

	const inputs = structuredClone(knownPv.project.inputs);
	Object.assign(inputs.brief.site, {
		country_code: "DE",
		location_label: street,
		coordinate_basis: "not_provided",
		latitude: null,
		longitude: null,
	});
	const requests = [];
	const foreign = place("NL", { latitude: 52.1, longitude: 5.1 }, "Utrecht");
	const hamburg = place(
		"DE",
		{ latitude: 53.5431, longitude: 9.9977 },
		"Am Sandtorkai 1, 20457 Hamburg, Germany",
	);
	t.mock.method(globalThis, "fetch", async (url, options) => {
		requests.push({ url, body: JSON.parse(options.body) });
		return Response.json({ places: [foreign, hamburg] });
	});
	let submitted;
	await act(async () =>
		root.render(
			React.createElement(
				"form",
				{
					onSubmit: (event) => {
						event.preventDefault();
						const useAddress = new window.FormData(event.currentTarget).has(
							"pvgis_use_address",
						);
						assert.ok(
							isHomepagePvReferenceReady(inputs, inputs.brief, useAddress),
						);
						submitted = prepareHomepagePvReference(inputs, config, useAddress);
					},
				},
				React.createElement(HomepagePvReference, {
					inputs,
					brief: inputs.brief,
					power: 6.4,
					addressLookup: true,
					locale: config.locale,
					onCoordinateValidity() {},
					edit: () => true,
				}),
				React.createElement("button", { type: "submit" }, "Compare systems"),
			),
		),
	);
	const form = dom.element.querySelector("form");
	const consent = form.elements.namedItem("pvgis_use_address");
	assert.ok(consent, "The form offers an explicit address lookup choice");
	assert.equal(consent.checked, false);
	assert.match(consent.closest("label").textContent, /Google Maps/);
	assert.equal(form.elements.namedItem("latitude").required, true);
	await act(async () => consent.click());
	assert.equal(form.elements.namedItem("latitude"), null);
	assert.equal(form.elements.namedItem("longitude"), null);
	assert.deepEqual(requests, []);

	await act(async () => form.querySelector('button[type="submit"]').click());
	assert.ok(submitted, "The first compare submission can use the address");
	const prepared = await submitted;
	assert.deepEqual(requests, [
		{
			url: "https://places.googleapis.com/v1/places:searchText",
			body: { textQuery: street, languageCode: "de", regionCode: "DE" },
		},
	]);
	assert.deepEqual(prepared.brief.site, {
		...inputs.brief.site,
		coordinate_basis: "user_entered",
		latitude: 53.5431,
		longitude: 9.9977,
		location_label: "Am Sandtorkai 1, 20457 Hamburg, Germany",
		postal_code: "20457",
	});
	assert.deepEqual(prepared.pvgis_reference, inputs.pvgis_reference);
});

test("manual coordinates remain usable without sending the project address to Google Maps", async (t) => {
	const { prepareHomepagePvReference, isHomepagePvReferenceReady } =
		await import("../src/components/configurator/HomepagePvReference.tsx");
	const inputs = knownPv.project.inputs;
	const fetch = t.mock.method(globalThis, "fetch", async () => {
		assert.fail("Manual coordinates do not need an address lookup");
	});
	assert.equal(isHomepagePvReferenceReady(inputs, inputs.brief), true);
	assert.strictEqual(
		await prepareHomepagePvReference(inputs, config, false),
		inputs,
	);
	assert.equal(fetch.mock.callCount(), 0);
});

test("an address result from another country cannot supply the site's coordinates", async (t) => {
	const { prepareHomepagePvReference } =
		await import("../src/components/configurator/HomepagePvReference.tsx");
	const inputs = structuredClone(knownPv.project.inputs);
	Object.assign(inputs.brief.site, {
		country_code: "DE",
		location_label: street,
		coordinate_basis: "not_provided",
		latitude: null,
		longitude: null,
	});
	t.mock.method(globalThis, "fetch", async () =>
		Response.json({
			places: [place("NL", { latitude: 52.1, longitude: 5.1 }, "Utrecht")],
		}),
	);
	await assert.rejects(prepareHomepagePvReference(inputs, config, true), {
		code: "pvgis_reference_site_required",
	});
});
