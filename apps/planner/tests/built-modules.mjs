import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { JSDOM } from "jsdom";

// Exercise the real emitted ESM graph, including WP's versioned entry identity.
// No application DOM, API, Canvas or GPU substitute is presented as native proof.
test("a lazy built chunk never executes the versioned WordPress entry again", async (t) => {
	const dom = new JSDOM("<!doctype html><body></body>", {
		url: "https://fixture.invalid/workspace/",
	});
	const previous = new Map();
	// JSDOM omits Blob URLs. MapLibre creates its local worker URL at module
	// import, before a map exists. Use Node's real Blob registry for this import
	// identity test; no Worker, WebGL or browser/provider result is simulated.
	const blobUrls = new Set();
	dom.window.URL.createObjectURL = (blob) => {
		const url = URL.createObjectURL(blob);
		blobUrls.add(url);
		return url;
	};
	dom.window.URL.revokeObjectURL = (url) => {
		URL.revokeObjectURL(url);
		blobUrls.delete(url);
	};
	for (const name of [
		"window",
		"document",
		"navigator",
		"location",
		"MutationObserver",
	]) {
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value: dom.window[name],
			configurable: true,
		});
	}
	t.after(() => {
		for (const url of blobUrls) URL.revokeObjectURL(url);
		dom.window.close();
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	let starts = 0;
	const query = document.querySelectorAll.bind(document);
	document.querySelectorAll = (selector) => {
		if (selector === "[data-linker-planner]") starts++;
		return query(selector);
	};
	const directory = new URL(
		"../../../plugins/linker-tools/build/planner/",
		import.meta.url,
	);
	const manifest = JSON.parse(
		await readFile(new URL("vite-manifest.json", directory), "utf8"),
	);
	assert.ok(
		manifest["src/components/design/SceneViewport.tsx"]?.isDynamicEntry,
	);
	assert.ok(manifest["src/components/design/MapViewport.tsx"]?.isDynamicEntry);
	await import(
		new URL(manifest["src/main.tsx"].file + "?ver=wordpress-version", directory)
	);
	assert.equal(starts, 1);
	for (const chunk of Object.values(manifest).filter(
		(entry) => entry.isDynamicEntry,
	)) {
		const module = await import(new URL(chunk.file, directory));
		assert.equal(typeof module.default, "function");
		assert.equal(
			starts,
			1,
			"A lazy chunk executed the application entry a second time",
		);
	}
});
