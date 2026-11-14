import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

const projectId = "7".repeat(32);
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

/**
 * The one-screen start owns a running chain of server commands. Creating the
 * project puts a row in the saved-project index, so a start rendered only in
 * the empty-index branch is unmounted by its own first success: the chain stops
 * polling and its queued server run is orphaned. Measured in production before
 * the fix: projects/create 200 at 12.4s, the start gone at 13.3s, no runs/read.
 */
test("the start survives its own project appearing in the saved-project index", async (t) => {
	const fixture = setupDom();
	// The shared fixture opens a project from its URL; this test starts at the
	// empty index, which is where the one-screen start lives.
	window.history.replaceState({}, "", "/workspace/");
	const globals = new Map();
	for (const [name, value] of Object.entries({
		MutationObserver: window.MutationObserver,
		getComputedStyle: window.getComputedStyle.bind(window),
		requestAnimationFrame: (callback) =>
			setTimeout(() => callback(Date.now()), 0),
		cancelAnimationFrame: clearTimeout,
	})) {
		globals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value,
			configurable: true,
			writable: true,
		});
	}
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");

	let listed = [];
	const client = {
		invalidate() {},
		async bootstrap() {
			return session;
		},
		async probeScope() {
			return session.query_scope;
		},
		isCurrentScope(scope) {
			return scope === session.query_scope;
		},
		async query(path) {
			if (path === "projects/list")
				return { schema_version: 1, items: listed, next: null };
			throw new Error("unexpected command " + path);
		},
	};
	const store = {
		async read() {
			return null;
		},
		async readProfileImports() {
			return [];
		},
		async candidates() {
			return [];
		},
		async write() {},
	};
	const config = {
		baseUrl: location.origin + "/api/",
		nonceUrl: location.origin + "/nonce",
		locale: "en-US",
		countries: { NO: "Norway" },
	};
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of globals) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(SessionBoundary, { client }, (value, recheck) =>
					React.createElement(Workspace, {
						key: value.query_scope,
						session: value,
						client,
						store,
						config,
						recheck,
					}),
				),
			),
		),
	);
	const start = () => document.querySelector(".lp-quickstart");
	await until(() => start());
	assert.ok(start(), "expected the start on an empty index");

	listed = [
		{
			id: projectId,
			title: "Residential · 10 kWp · 10115 Berlin",
			revision: 1,
			input_sha256: "8".repeat(64),
			updated_at: 1763200000,
		},
	];
	const refresh = () =>
		[...document.querySelectorAll("button")].find(
			(button) => button.getAttribute("aria-label") === "Refresh projects",
		);
	await act(async () => refresh().click());
	await until(
		() => document.querySelectorAll(".lp-project-entry").length === 1,
	);
	assert.ok(
		start(),
		"the start that is running the project must stay mounted when the index gains its row",
	);
});
