import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred, enter } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

test("a first-time guest can edit while native confirmation is pending and sees no unsolicited project list", async (t) => {
	const fixture = setupDom();
	window.history.replaceState(null, "", "/solution-configurator/");
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { DraftStore } = await import("../src/data/DraftStore.ts");
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		configurable: true,
		value: new IDBFactory(),
	});
	const admission = deferred(),
		queries = [];
	let starts = 0,
		admitted = false;
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
				max_body_bytes: 1000000,
				max_csv_bytes: 100000,
				max_page_size: 30,
				max_json_depth: 32,
			},
		},
	};
	const client = {
		bootstrap: async () => {
			starts++;
			await admission.promise;
			admitted = true;
			return session;
		},
		invalidate() {},
		isCurrentScope: (scope) => admitted && scope === session.query_scope,
		query: async (path) => {
			queries.push(path);
			return { items: [], next: null };
		},
		probeScope: async () => session.query_scope,
	};
	const root = createRoot(fixture.element),
		store = new DraftStore();
	t.after(async () => {
		await fixture.dispose(root);
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else Reflect.deleteProperty(globalThis, "indexedDB");
	});
	await act(async () =>
		root.render(
			React.createElement(
				SessionBoundary,
				{ client, publicIntake: true },
				(value, recheck, ensureSession) =>
					React.createElement(Workspace, {
						client,
						store,
						session: value,
						recheck,
						ensureSession,
						config: { locale: "en", countries: { DE: "Germany" } },
					}),
			),
		),
	);
	const start = document.querySelector('select[name="project_start"]');
	assert.ok(start);
	assert.equal(start.disabled, false);
	assert.equal(starts, 0);
	const name = document.querySelector('input[name="project_name"]');
	assert.ok(name);
	await act(async () => name.focus());
	await enter(name, "Rooftop");
	assert.equal(starts, 1);
	assert.deepEqual(queries, []);
	const language = document.createElement("a");
	language.lang = "de";
	language.hreflang = "de";
	language.href = location.pathname + "#sc-preliminary-options";
	document.querySelector("header").append(language);
	const click = new window.MouseEvent("click", {
		bubbles: true,
		cancelable: true,
	});
	await act(async () => language.dispatchEvent(click));
	assert.ok(click.defaultPrevented);
	assert.equal(window.sessionStorage.getItem("linker-comparison-draft"), null);
	await act(async () => admission.resolve());
	await until(() => location.hash === "#sc-preliminary-options");
	const handoff = JSON.parse(
		window.sessionStorage.getItem("linker-comparison-draft"),
	);
	assert.equal(handoff.scope, session.query_scope);
	assert.equal(handoff.title, "Rooftop");
	assert.equal(handoff.languageUrl, language.href);
	await until(() => admitted);
	assert.equal(name, document.querySelector('input[name="project_name"]'));
	assert.equal(name.value, "Rooftop");
	assert.deepEqual(queries, []);
	const projects = Array.from(document.querySelectorAll("button")).find(
		(x) => x.textContent === "Projects",
	);
	await act(async () => projects.click());
	await until(() => queries.includes("projects/list"));
	assert.equal(starts, 1);
});

test("signed-in, recovery and private links use the existing admission gate; public marketing hints show intake", async (t) => {
	const fixture = setupDom();
	t.after(() => fixture.dom.window.close());
	const { canStartPublicIntake } = await import("../src/data/publicIntake.ts");
	const url = (query = "") =>
		new URL("/solution-configurator/" + query, location.origin);
	const anon = { nonceUrl: "", hasWorkspaceSession: false };
	for (const query of [
		"",
		"?application=commercial&goal=peak_shaving",
		"?scope=storage_addition",
		"?utm_source=example",
	])
		assert.equal(canStartPublicIntake(anon, url(query)), true, query);
	for (const query of [
		"?projects=1",
		"?project=123",
		"?saved_solution=1",
		"?brief=1",
		"?retry_revision=1",
		"?linker_inquiry_retry=1",
		"?run=1",
		"?view=equipment",
		"?energy_view=1",
		"?step=roof",
		"#sc-review",
	])
		assert.equal(canStartPublicIntake(anon, url(query)), false, query);
	assert.equal(
		canStartPublicIntake({ ...anon, nonceUrl: "/nonce" }, url()),
		false,
	);
	assert.equal(
		canStartPublicIntake({ ...anon, hasWorkspaceSession: true }, url()),
		false,
	);
	window.history.replaceState({ "linker-comparison-draft": "draft123" }, "");
	window.sessionStorage.setItem(
		"linker-comparison-draft",
		JSON.stringify({ id: "draft123" }),
	);
	assert.equal(canStartPublicIntake(anon, url()), false);
});
