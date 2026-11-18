import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until, enter } from "./dom-fixture.mjs";
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

test("project setup retains entered information when the saved-project index refreshes", async (t) => {
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
	const creates = [];
	let accepted;
	const client = {
		async send(path, body) {
			assert.equal(path, "projects/create");
			creates.push(body);
			const command = JSON.parse(body);
			accepted = {
				id: projectId,
				revision: 1,
				title: command.title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
			return accepted;
		},
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
		async writeCreation() {},
		async clearCreation() {},
		async readCreations() {
			return [];
		},
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
	const start = () => document.querySelector("form");
	await until(() => document.querySelector('select[name="system_scope"]'));
	await act(async () => {
		const scope = document.querySelector('select[name="system_scope"]');
		scope.value = "storage_only";
		scope.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await enter(
		document.querySelector('input[name="project_title"]'),
		"Oslo storage",
	);

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
		() => document.querySelectorAll('[role="listitem"]').length === 1,
	);
	assert.ok(start());
	assert.equal(
		document.querySelector('input[name="project_title"]').value,
		"Oslo storage",
	);
	assert.equal(
		document.querySelector('select[name="system_scope"]').value,
		"storage_only",
	);
	const purpose = document.querySelector('select[name="project_purpose"]');
	assert.ok(purpose, "purpose belongs to the initial Project page");
	await act(async () => {
		purpose.value = "backup";
		purpose.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	const next = [...document.querySelectorAll("button")].find(
		(item) => item.textContent === "Continue with storage",
	);
	await act(async () => {
		next.click();
		next.click();
	});
	await until(() => location.hash === "#sc-energy");
	assert.equal(creates.length, 1);
	assert.equal(accepted.inputs.backup_demand.load_kw, null);
	assert.equal(accepted.title, "Oslo storage");
	await until(() =>
		document.body.textContent.includes("What should the system do?"),
	);
});
