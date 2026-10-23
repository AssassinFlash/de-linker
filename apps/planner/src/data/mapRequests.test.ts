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
