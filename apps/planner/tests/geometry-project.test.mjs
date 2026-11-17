import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { geometryImportStore } from "../src/data/GeometryImportStore.ts";
import { emptyBrief } from "../src/domain/brief.ts";
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import { workspaceFromHash } from "../src/components/ProjectEditor.tsx";

register("./map-library-loader.mjs", import.meta.url);

test("editing the site address or country drops the old search postcode and retains coordinates", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { BriefForm } = await import("../src/components/BriefForm.tsx");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const brief = {
		...emptyBrief(),
		site: {
			...emptyBrief().site,
			country_code: "DE",
			location_label: "80333 München",
			postal_code: "80333",
			latitude: 48.145,
			longitude: 11.566,
			coordinate_basis: "user_entered",
		},
	};
	const changes = [];
	await act(async () =>
		root.render(
			React.createElement(BriefForm, {
				brief,
				config: {
					locale: "en",
					countries: { DE: "Germany", NL: "Netherlands" },
				},
				onChange: (value) => changes.push(value),
				onValidity: () => {},
				workspace: "site",
			}),
		),
	);
	await enter(
		document.querySelector('#lp-site input[autocomplete="off"]'),
		"10115 Berlin",
	);
	const country = document.querySelector("#lp-site select[aria-labelledby]");
	await act(async () => {
		country.value = "NL";
		country.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(changes.length, 2);
	for (const value of changes) {
		assert.equal(value.site.postal_code, null);
		assert.equal(value.site.latitude, brief.site.latitude);
		assert.equal(value.site.longitude, brief.site.longitude);
	}
});

test("saved roof projects reopen in design while energy projects and explicit routes keep their entry", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const brief = {
		...emptyBrief(),
		site: {
			...emptyBrief().site,
			country_code: "DE",
			location_label: "Synthetic address",
			latitude: 50.94,
			longitude: 6.96,
			coordinate_basis: "user_entered",
		},
	};
	assert.equal(workspaceFromHash({ brief }), "design");
	assert.equal(workspaceFromHash({ brief, geometry: {} }), "design");
	assert.equal(
		workspaceFromHash({ brief: { ...brief, system_scope: "new_pv_storage" } }),
		"design",
	);
	assert.equal(
		workspaceFromHash({ brief: { ...brief, system_scope: "storage_only" } }),
		"site",
	);
	assert.equal(workspaceFromHash({ brief, equipment_setup: {} }), "site");
	assert.equal(workspaceFromHash({ brief: emptyBrief() }), "site");
	location.hash = "#lp-overview";
	assert.equal(workspaceFromHash({ brief }), "site");
	location.hash = "#lp-load";
	assert.equal(workspaceFromHash({ brief }), "energy");
});

test("a failed aerial lookup retries on request without changing saved coordinates or roof geometry", async (t) => {
	const dom = setupDom();
	const previous = new Map();
	for (const name of ["indexedDB", "getComputedStyle"]) {
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value:
				name === "indexedDB"
					? new IDBFactory()
					: window.getComputedStyle.bind(window),
			configurable: true,
		});
	}
	const css = document.createElement("style");
	css.textContent =
		".lp-map-host{--proto-neutral-300:#ccc;--proto-teal-900:#123;--proto-neutral-600:#456;--proto-teal-700:#278;--proto-teal-400:#4bc;--proto-neutral-100:#eee;}";
	document.head.append(css);
	const { createRoot } = await import("react-dom/client");
	const { maps } = await import("./map-library-fixture.mjs");
	const { default: Configurator } =
		await import("../src/components/configurator/Configurator.tsx");
	location.hash = "#lp-map-roof-properties";
	const geometry = JSON.parse(
		readFileSync(
			new URL(
				"../../../fixtures/planning/geometry-import-asset.json",
				import.meta.url,
			),
			"utf8",
		),
	).metadata.geometry_import.geometry;
	const project = {
		id: "1".repeat(32),
		title: "Synthetic aerial retry",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: {
			geometry,
			brief: {
				...emptyBrief(),
				site: {
					...emptyBrief().site,
					country_code: "DE",
					location_label: "Synthetic address",
					postal_code: "50667",
					latitude: 50.94,
					longitude: 6.96,
					coordinate_basis: "user_entered",
				},
			},
		},
	};
	const before = structuredClone(project.inputs);
	const session = {
		query_scope: "3".repeat(64),
		kind: "guest",
		runtime: { limits: { max_page_size: 20 } },
	};
	const imagery = {
		tiles: ["https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}"],
		credit: "Synthetic imagery provider",
		licence: "Synthetic test permission",
		licence_url: "https://fixture.invalid/licence",
	};
	const lookups = [],
		outlines = [],
		writes = [];
	const client = {
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			if (path === "projects/runs") return { items: [], next: null };
			if (path === "products/current") return { items: [] };
			if (path === "places/lookup") {
				lookups.push(command);
				if (lookups.length === 1) throw new Error("Synthetic lookup failure");
				return { imagery, latitude: 51, longitude: 7, country_code: "DE" };
			}
			if (path === "places/outline") {
				outlines.push(command);
				return { found: false };
			}
			throw new Error("Unexpected fixture route " + path);
		},
	};
	const store = {
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async readProfileImports() {
			return [];
		},
		async write(_scope, draft) {
			writes.push(draft);
		},
	};
	const cache = new QueryClient(),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Configurator, {
					project,
					session,
					client,
					store,
					config: { locale: "en-GB", countries: { DE: "Germany" } },
					recheck: () => assert.fail("Unexpected identity error"),
					close: () => true,
				}),
			),
		),
	);
	const retry = () => document.querySelector('.sc-solar [role="alert"] button');
	await until(
		() => retry() && document.querySelector('[data-map-status="ready"]'),
	);
	assert.equal(retry().textContent, "Try again");
	assert.equal(lookups.length, 1, "failure must wait for the visitor to retry");
	const firstMap = maps.findLast((item) => !item.removed);
	const overlay = structuredClone(
		firstMap.getSource("linker-project-geometry").data,
	);
	assert.equal(firstMap.getSource("linker-site-imagery"), undefined);
	await act(async () => retry().click());
	// Imagery tiles load only after the visitor's explicit aerial-map consent.
	const consent = () =>
		[...document.querySelectorAll("button")].find(
			(node) => node.textContent.trim() === "Show aerial map",
		);
	await until(consent);
	await act(async () => consent().click());
	// Granting consent widens the request scope, which recreates the map, so
	// the imagery assertions target the new live instance.
	let map = null;
	await until(() => {
		map = maps.findLast((item) => !item.removed);
		return map !== firstMap && map.getSource("linker-site-imagery");
	});
	assert.deepEqual(lookups, [
		{ schema_version: 1, query: "50667", country: "DE" },
		{ schema_version: 1, query: "50667", country: "DE" },
	]);
	assert.deepEqual(outlines, [
		{
			schema_version: 1,
			query: "Synthetic address",
			country: "DE",
			latitude: 50.94,
			longitude: 6.96,
		},
	]);
	assert.deepEqual(map.getSource("linker-site-imagery").tiles, imagery.tiles);
	assert.deepEqual(map.getSource("linker-project-geometry").data, overlay);
	assert.deepEqual(project.inputs, before);
	assert.deepEqual(writes, [], "Imagery retry must not edit the project draft");
	assert.equal(retry(), null);
});

test("import joins one project history step, guards navigation, and a confirmed save clears its exact original", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	location.hash = "#sc-solar";
	const { default: Configurator } =
		await import("../src/components/configurator/Configurator.tsx");
	const { createRoot } = await import("react-dom/client");
	const asset = JSON.parse(
			readFileSync(
				new URL(
					"../../../fixtures/planning/geometry-import-asset.json",
					import.meta.url,
				),
				"utf8",
			),
		),
		raw = readFileSync(
			new URL(
				"../../../fixtures/planning/source-roof-wgs84.geojson",
				import.meta.url,
			),
		);
	const project = {
		id: asset.project_id,
		title: "Synthetic import workflow",
		revision: 1,
		input_sha256: "1".repeat(64),
		inputs: { ...knownPv.project.inputs },
	};
	const session = {
		schema_version: 1,
		kind: "guest",
		cookie_confirmed: true,
		expires_at: 2000000000,
		query_scope: "3".repeat(64),
		nonce: "abcdefghij",
		claim_pending: false,
		runtime: {
			schema_version: 1,
			runtime_sha256: "4".repeat(64),
			models: {},
			limits: {
				max_body_bytes: 16777216,
				max_csv_bytes: 4194304,
				max_page_size: 20,
				max_json_depth: 32,
			},
		},
	};
	const original = JSON.stringify({
		schema_version: 1,
		project_id: project.id,
		key: crypto.randomUUID(),
		content_base64: raw.toString("base64"),
		options: asset.metadata.geometry_import_options,
	});
	await geometryImportStore.write(session.query_scope, original);
	let local = null,
		saved = null;
	const store = {
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async readProfileImports() {
			return [];
		},
		async write(_scope, value) {
			local = structuredClone(value);
		},
	};
	const json = (value) =>
		new Response(JSON.stringify(value), {
			headers: { "Content-Type": "application/json" },
		});
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url, init) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return json(session);
			if (path.endsWith("/projects/runs"))
				return json({ items: [], next: null });
			if (path.endsWith("/geometry/import")) {
				assert.equal(init.body, original);
				return json(asset);
			}
			if (path.endsWith("/projects/revise")) {
				const command = JSON.parse(init.body);
				saved = {
					...project,
					revision: 2,
					input_sha256: "5".repeat(64),
					inputs: command.inputs,
				};
				return json(saved);
			}
			throw new Error("Unexpected fixture route " + path);
		},
	});
	await client.bootstrap();
	const cache = new QueryClient(),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	const button = (label) =>
		[...document.querySelectorAll("button")].find(
			(node) =>
				(node.getAttribute("aria-label") ?? node.textContent.trim()) === label,
		);
	const click = async (label) => {
		assert.ok(button(label), label);
		await act(async () => button(label).click());
	};
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Configurator, {
					project,
					session,
					client,
					store,
					config: { locale: "en-GB", countries: { DE: "Germany" } },
					recheck: () => assert.fail("Unexpected identity error"),
					close: () => true,
				}),
			),
		),
	);
	await until(
		() =>
			button(asset.metadata.geometry_import_options.source.label) &&
			!button(asset.metadata.geometry_import_options.source.label).closest(
				"fieldset[disabled]",
			),
	);
	await click(asset.metadata.geometry_import_options.source.label);
	assert.equal(button("Save snapshot").disabled, true);
	await act(async () => document.querySelector(".sc-nav button").click());
	assert.equal(location.hash, "#sc-solar");
	assert.match(document.body.textContent, /Finish or cancel roof editing/);
	await click("Check or retry this upload");
	await until(
		() =>
			button("Add roof to current design") &&
			!button("Add roof to current design").disabled,
	);
	await click("Add roof to current design");
	await until(() => local?.history.current.geometry?.roofs.length === 1);
	assert.equal(local.history.past.length, 1);
	assert.equal(local.history.current.geometry.roofs[0].holes_uv.length, 1);
	assert.equal(
		local.history.current.pvgis_reference_setup.model,
		"pvgis_5_3_roof_ac_reference_v1",
	);
	assert.equal(local.history.current.pvgis_reference_setup.arrays, undefined);
	assert.equal(
		local.history.current.pvgis_reference.model,
		"pvgis_5_3_roof_ac_reference_v1",
	);
	assert.equal(
		local.history.current.geometry_imports.selected[
			asset.metadata.geometry_import.geometry.sources[0].id
		],
		asset.id,
	);
	await click("Undo");
	await until(() => local?.history.current.geometry === undefined);
	await click("Redo");
	await until(() => local?.history.current.geometry?.roofs.length === 1);
	await click("Save snapshot");
	await until(
		() =>
			saved &&
			document.body.textContent.includes(
				"The roof import is included in the saved project.",
			),
	);
	await until(() => local?.baseline.revision === 2);
	assert.deepEqual(saved.inputs, local.history.current);
	await until(() => !document.querySelector(".lp-geometry-intake details"));
	assert.deepEqual(
		await geometryImportStore.list([session.query_scope], project.id),
		[],
	);
});
