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
import geometryAsset from "../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };

register("./map-library-loader.mjs", import.meta.url);

test("changing the site clears its previous geocoding while keeping roof and interval data", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ProjectDetails } =
		await import("../src/components/configurator/ProjectDetails.tsx");
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
	const inputs = {
		brief,
		geometry: geometryAsset.metadata.geometry_import.geometry,
		profile_selections: {
			schema_version: 1,
			selected: { gross_load: "d".repeat(32) },
		},
	};
	const changes = [];
	await act(async () =>
		root.render(
			React.createElement(ProjectDetails, {
				inputs,
				disabled: false,
				config: {
					locale: "en",
					countries: { DE: "Germany", NL: "Netherlands" },
				},
				edit: (apply) => {
					changes.push(apply(inputs));
					return true;
				},
			}),
		),
	);
	await enter(
		document.querySelector('input[name="location_label"]'),
		"10115 Berlin",
	);
	const country = document.querySelector('select[name="country"]');
	await act(async () => {
		country.value = "NL";
		country.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(changes.length, 2);
	for (const value of changes) {
		assert.equal(value.brief.site.postal_code, null);
		assert.equal(value.brief.site.latitude, null);
		assert.equal(value.brief.site.longitude, null);
		assert.equal(value.brief.site.coordinate_basis, "not_provided");
		assert.deepEqual(value.geometry, inputs.geometry);
		assert.deepEqual(value.profile_selections, inputs.profile_selections);
	}
});

test("opening a saved project honors the requested workspace and sends storage-only projects to energy use", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { default: Configurator } =
		await import("../src/components/configurator/ProjectWorkbench.tsx");
	const root = createRoot(dom.element);
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	globalThis.indexedDB = new IDBFactory();
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	const client = {
		isCurrentScope: () => true,
		async query(path) {
			assert.equal(path, "projects/runs");
			return { items: [], next: null };
		},
	};
	const store = {
		read: async () => null,
		candidates: async () => [],
		readProfileImports: async () => [],
	};
	const session = {
		query_scope: "3".repeat(64),
		kind: "guest",
		runtime: { limits: { max_page_size: 20 }, models: {} },
	};
	for (const [systemScope, hash, label] of [
		["new_pv_storage", "", "Project & direction"],
		["new_pv_storage", "#sc-solar", "Roof & PV"],
		["new_pv_storage", "#sc-energy", "Energy profile & CSV"],
		["storage_only", "#sc-solar", "Energy profile & CSV"],
	]) {
		const project = {
			...knownPv.project,
			inputs: { brief: { ...emptyBrief(), system_scope: systemScope } },
		};
		window.history.replaceState(null, "", "?project=" + project.id + hash);
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						key: systemScope + hash,
						project,
						session,
						client,
						store,
						config: { locale: "en-GB", countries: { DE: "Germany" } },
						recheck() {},
						close: () => true,
					}),
				),
			),
		);
		await until(() =>
			(
				document.querySelector('.sc-refinement-tabs [aria-current="page"]') ??
				document.querySelector('nav [aria-current="step"]')
			)?.textContent.endsWith(label),
		);
		assert.equal(location.hash, hash);
	}
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
		".sc-map-host{--proto-neutral-300:#ccc;--proto-teal-900:#123;--proto-neutral-600:#456;--proto-teal-700:#278;--proto-teal-400:#4bc;--proto-neutral-100:#eee;}";
	document.head.append(css);
	const { createRoot } = await import("react-dom/client");
	const { maps } = await import("./map-library-fixture.mjs");
	const { default: Configurator } =
		await import("../src/components/configurator/ProjectWorkbench.tsx");
	location.hash = "#sc-roof";
	const geometry = geometryAsset.metadata.geometry_import.geometry;
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
			query: "50667",
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

test("import and history changes save their roof revision and release the exact original", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	location.hash = "#sc-solar";
	const { default: Configurator } =
		await import("../src/components/configurator/ProjectWorkbench.tsx");
	const { createRoot } = await import("react-dom/client");
	const asset = geometryAsset,
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
					revision: command.expected_revision + 1,
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
			button("Place modules on the roof") &&
			!button("Place modules on the roof").closest("fieldset[disabled]"),
	);
	await click("Place modules on the roof");
	await click("Open roof layout");
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
	await until(() => saved?.revision === 2 && local?.baseline.revision === 2);
	assert.deepEqual(
		saved.inputs.geometry.roofs[0].holes_uv,
		asset.metadata.geometry_import.geometry.roofs[0].holes_uv,
	);
	await until(() => !document.querySelector(".sc-geometry-intake details"));
	assert.deepEqual(
		await geometryImportStore.list([session.query_scope], project.id),
		[],
	);
	await click("Undo");
	await until(() => local?.baseline.revision === 3);
	assert.equal(saved.inputs.geometry, undefined);
	await click("Redo");
	await until(() => local?.baseline.revision === 4);
	assert.deepEqual(
		saved.inputs.geometry.roofs[0].holes_uv,
		asset.metadata.geometry_import.geometry.roofs[0].holes_uv,
	);
	await click("Use module details");
	await until(
		() => local?.history.current.pvgis_reference_setup?.arrays?.length,
	);
	assert.deepEqual(
		local.history.current.pvgis_reference_setup.arrays,
		knownPv.project.inputs.pvgis_reference.arrays,
	);
	await click("Place modules on the roof");
	await click("Open roof layout");
	assert.equal(local.history.current.pvgis_reference_setup.arrays, undefined);
});
