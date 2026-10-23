import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until } from "./dom-fixture.mjs";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { geometryImportStore } from "../src/data/GeometryImportStore.ts";
import { emptyBrief } from "../src/domain/brief.ts";
import { ProjectEditor } from "../src/components/ProjectEditor.tsx";

test("import joins one project history step, guards navigation, and a confirmed save clears its exact original", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	location.hash = "#lp-design";
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
		inputs: { brief: emptyBrief() },
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
				React.createElement(ProjectEditor, {
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
	await until(() =>
		button(asset.metadata.geometry_import_options.source.label),
	);
	await click(asset.metadata.geometry_import_options.source.label);
	assert.equal(button("Save project").disabled, true);
	await act(async () =>
		document.querySelector('nav a[href="#lp-overview"]').click(),
	);
	assert.equal(
		document.querySelector(".lp-project").dataset.workspace,
		"design",
	);
	assert.ok(document.querySelector(".lp-navigation-refusal"));
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
		local.history.current.geometry_imports.selected[
			asset.metadata.geometry_import.geometry.sources[0].id
		],
		asset.id,
	);
	await click("Undo");
	await until(() => local?.history.current.geometry === undefined);
	await click("Redo");
	await until(() => local?.history.current.geometry?.roofs.length === 1);
	await click("Save project");
	await until(
		() =>
			saved &&
			document.body.textContent.includes(
				"The roof import is included in the saved project.",
			),
	);
	await until(() => local?.baseline.revision === 2);
	await until(() => document.body.textContent.includes("Saved · revision 2"));
	assert.deepEqual(saved.inputs, local.history.current);
	await until(() => !document.querySelector(".lp-geometry-intake details"));
	assert.deepEqual(
		await geometryImportStore.list([session.query_scope], project.id),
		[],
	);
});
