import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("the WindPress map stylesheet is the pinned licensed vendor source inside the component scope", async () => {
	const pkg = JSON.parse(
		await readFile(
			new URL("../node_modules/maplibre-gl/package.json", import.meta.url),
			"utf8",
		),
	);
	const original = await readFile(
		new URL(
			"../node_modules/maplibre-gl/dist/maplibre-gl.css",
			import.meta.url,
		),
		"utf8",
	);
	const licence = await readFile(
		new URL("../node_modules/maplibre-gl/LICENSE.txt", import.meta.url),
		"utf8",
	);
	const installed = await readFile(
		new URL(
			"../../../plugins/linker-commerce/content/windpress/planner-maplibre.css",
			import.meta.url,
		),
		"utf8",
	);
	const open = "@layer components {\n@scope ([data-linker-planner]) {\n",
		close = "\n}\n}\n";
	assert.ok(
		installed.includes(`MapLibre GL JS ${pkg.version} vendor stylesheet.`),
	);
	assert.ok(
		installed.includes(
			`Source SHA256: ${createHash("sha256").update(original).digest("hex")}`,
		),
	);
	assert.ok(installed.includes(licence));
	assert.ok(installed.endsWith(close));
	assert.equal(
		installed.slice(installed.indexOf(open) + open.length, -close.length),
		original,
	);
	// SVG data URLs contain the W3C namespace URI. That text is not a fetch.
	// Check actual CSS URL tokens in this fixed, digest-verified vendor file.
	assert.ok(!/@import\s/.test(original));
	const urls = [...original.matchAll(/url\(\s*["']?([^"')\s]+)/g)];
	assert.ok(urls.length > 0);
	assert.ok(
		urls.every((match) => match[1].startsWith("data:")),
		"vendor CSS assets must stay inline before the map action",
	);
});
