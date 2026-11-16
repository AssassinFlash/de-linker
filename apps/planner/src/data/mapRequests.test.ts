import assert from "node:assert/strict";
import test from "node:test";
import { MapRequestScope } from "./mapRequests.ts";

test("a map view cannot infer an external request grant or widen its provider origin", () => {
	const local = new MapRequestScope(false),
		external = new MapRequestScope(true);
	assert.throws(
		() => local.transform("https://tiles.openfreemap.org/styles/liberty"),
		/not_authorized/,
	);
	for (const url of [
		"http://tiles.openfreemap.org/planet",
		"https://tiles.openfreemap.org.attacker.invalid/tile",
		"https://attacker.invalid/tile",
		"https://credentials@tiles.openfreemap.org/planet",
		"https://tiles.openfreemap.org:444/planet",
		"data:text/plain,content",
	])
		assert.throws(() => external.transform(url), /not_authorized/);
	assert.deepEqual(
		external.transform("https://tiles.openfreemap.org/fonts/font/0-255.pbf"),
		{
			url: "https://tiles.openfreemap.org/fonts/font/0-255.pbf",
			credentials: "same-origin",
			referrerPolicy: "no-referrer",
		},
	);
});

test("an old library callback remains refused after release and a different view's explicit grant", () => {
	const first = new MapRequestScope(true),
		delayed = first.transform;
	first.release();
	first.release();
	const second = new MapRequestScope(true);
	assert.throws(
		() => delayed("https://tiles.openfreemap.org/planet"),
		/not_authorized/,
	);
	assert.equal(
		second.transform("https://tiles.openfreemap.org/planet").credentials,
		"same-origin",
	);
	second.release();
	assert.throws(
		() => second.transform("https://tiles.openfreemap.org/planet"),
		/not_authorized/,
	);
});

test("the site's declared mosaic origin is the only other origin granted", () => {
	const scoped = new MapRequestScope(true, ["https://geoservices.bayern.de"]);
	assert.equal(
		scoped.transform("https://geoservices.bayern.de/od/wms/dop/v1/dop20")
			.credentials,
		"same-origin",
	);
	// A longer host that merely starts with the granted name is a different origin.
	for (const url of [
		"https://geoservices.bayern.de.attacker.invalid/tile",
		"https://evil.invalid/tile",
		"http://geoservices.bayern.de/tile",
		"https://geoservices.bayern.de:444/tile",
		"https://user:pw@geoservices.bayern.de/tile",
	])
		assert.throws(() => scoped.transform(url), /not_authorized/, url);
});

test("an origin the caller did not declare stays refused", () => {
	const scoped = new MapRequestScope(true, []);
	assert.throws(
		() => scoped.transform("https://geoservices.bayern.de/tile"),
		/not_authorized/,
	);
	// A malformed declaration cannot widen the grant.
	const malformed = new MapRequestScope(true, [
		"javascript:alert(1)",
		"",
		"nonsense",
	]);
	assert.throws(
		() => malformed.transform("https://geoservices.bayern.de/tile"),
		/not_authorized/,
	);
	// The style provider is granted regardless; only the extra grants are dropped.
	assert.equal(
		malformed.transform("https://tiles.openfreemap.org/x").credentials,
		"same-origin",
	);
});

test("updating the mosaic grant swaps the allowed aerial origin without reviving a released scope", () => {
	const scoped = new MapRequestScope(true, []);
	assert.throws(
		() => scoped.transform("https://image.discomap.eea.europa.eu/tile"),
		/not_authorized/,
	);
	scoped.setAerialOrigins(["https://image.discomap.eea.europa.eu"]);
	assert.equal(
		scoped.transform("https://image.discomap.eea.europa.eu/tile").credentials,
		"same-origin",
	);
	scoped.setAerialOrigins(["https://data.geopf.fr", "http://insecure.invalid"]);
	assert.throws(
		() => scoped.transform("https://image.discomap.eea.europa.eu/tile"),
		/not_authorized/,
	);
	assert.equal(
		scoped.transform("https://data.geopf.fr/wms-r").credentials,
		"same-origin",
	);
	scoped.release();
	scoped.setAerialOrigins(["https://geoservices.bayern.de"]);
	assert.throws(
		() => scoped.transform("https://geoservices.bayern.de/tile"),
		/not_authorized/,
	);
});

test("Google tile requests send the site origin as Referer while other origins send no referrer", () => {
	const scoped = new MapRequestScope(true, [
		"https://tile.googleapis.com",
		"https://geoservices.bayern.de",
	]);
	assert.deepEqual(
		scoped.transform(
			"https://tile.googleapis.com/v1/2dtiles/18/140000/95000?session=s&key=k",
		),
		{
			url: "https://tile.googleapis.com/v1/2dtiles/18/140000/95000?session=s&key=k",
			credentials: "same-origin",
			referrerPolicy: "origin",
		},
	);
	assert.deepEqual(
		scoped.transform("https://geoservices.bayern.de/od/wms/dop/v1/dop20"),
		{
			url: "https://geoservices.bayern.de/od/wms/dop/v1/dop20",
			credentials: "same-origin",
			referrerPolicy: "no-referrer",
		},
	);
	assert.deepEqual(
		scoped.transform("https://tiles.openfreemap.org/styles/liberty"),
		{
			url: "https://tiles.openfreemap.org/styles/liberty",
			credentials: "same-origin",
			referrerPolicy: "no-referrer",
		},
	);
	for (const url of [
		"https://tile.googleapis.com.attacker.invalid/v1/2dtiles/0/0/0",
		"http://tile.googleapis.com/v1/2dtiles/0/0/0",
	])
		assert.throws(() => scoped.transform(url), /not_authorized/, url);
});
