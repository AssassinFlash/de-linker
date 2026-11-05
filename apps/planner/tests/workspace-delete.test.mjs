import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until, deferred } from "./dom-fixture.mjs";

const session = () => ({
	schema_version: 1,
	kind: "user",
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
});

function projects() {
	return [
		{
			id: "1".repeat(32),
			title: "Delete me",
			revision: 1,
			input_sha256: "2".repeat(64),
			updated_at: 1700000000,
		},
		{
			id: "5".repeat(32),
			title: "Keep me",
			revision: 2,
			input_sha256: "6".repeat(64),
			updated_at: 1700000001,
		},
	];
}

async function mount(handler, store) {
	const fixture = setupDom();
	// The shared fixture URL preselects a project; deletion lives in the list.
	history.replaceState({}, "", "/workspace/");
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const value = session();
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: handler,
	});
	const config = {
		locale: "en-GB",
		countries: { NO: "Norway" },
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
	};
	const root = createRoot(fixture.element);
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(
					SessionBoundary,
					{ client },
					(sessionValue, recheck) =>
						React.createElement(Workspace, {
							key: sessionValue.query_scope,
							session: sessionValue,
							client,
							store,
							config,
							recheck,
						}),
				),
			),
		),
	);
	await until(() => document.querySelector(".lp-project-entry"));
	return {
		fixture,
		client,
		scope: value.query_scope,
		async dispose() {
			await fixture.dispose(root);
		},
	};
}

function recordingStore() {
	const cleared = [];
	const creations = [];
	return {
		cleared,
		creations,
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
		async readCreations() {
			return creations;
		},
		async clearCreation(scope, body) {
			cleared.push({ scope, body });
		},
	};
}

const response = (value, status = 200) =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "Content-Type": "application/json" },
	});

const deleteIcon = () =>
	document.querySelectorAll("button.lp-project-delete")[0];

const confirmButton = () =>
	[...document.querySelectorAll(".lp-delete-confirm button")].find((button) =>
		button.className.includes("lp-button-danger"),
	);

test("an owned project is deleted behind an explicit confirm, one request, and the list refreshes", async (t) => {
	const store = recordingStore();
	store.creations.push({
		key: "11111111-1111-4111-8111-111111111111",
		title: "Delete me",
		body: '{"schema_version":1,"title":"Delete me","inputs":{},"key":"11111111-1111-4111-8111-111111111111"}',
		destination: null,
		createdAt: 1,
	});
	const deletes = [];
	let lists = 0;
	const mounted = await mount(async (url, init) => {
		if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
		if (String(url).endsWith("/bootstrap")) return response(session());
		if (String(url).endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (String(url).endsWith("/projects/list")) {
			lists++;
			return response({ items: projects(), next: null });
		}
		if (String(url).endsWith("/projects/delete")) {
			deletes.push(JSON.parse(String(init.body)));
			return response({
				project_id: "1".repeat(32),
				revision: 1,
				deleted: true,
			});
		}
		throw new Error("unexpected fetch " + String(url));
	}, store);
	t.after(() => mounted.dispose());
	// The secondary entry is a sibling of the row button, never nested.
	assert.equal(
		document.querySelector(".lp-project-entry-row button button"),
		null,
	);
	await act(async () => deleteIcon().click());
	await until(() => document.querySelector(".lp-delete-confirm"));
	assert.ok(
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes('Delete the project "Delete me" at revision 1?'),
	);
	assert.ok(
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes("revision 1"),
	);
	const before = lists;
	await act(async () => confirmButton().click());
	await until(() => lists > before && deletes.length === 1);
	assert.equal(deletes[0].schema_version, 1);
	assert.equal(deletes[0].project_id, "1".repeat(32));
	assert.equal(deletes[0].expected_revision, 1);
	assert.match(deletes[0].key, /^[a-f0-9-]{36}$/);
	await until(() => !document.querySelector(".lp-delete-confirm"));
	assert.ok(document.body.textContent.includes("Keep me"));
	assert.deepEqual(store.cleared, [
		{
			scope: session().query_scope,
			body: store.creations[0].body,
		},
	]);
});

test("an unknown 404 is a delete failure, not proof that another session removed the project", async (t) => {
	const store = recordingStore();
	const deletes = [];
	const mounted = await mount(async (url, init) => {
		if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
		if (String(url).endsWith("/bootstrap")) return response(session());
		if (String(url).endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (String(url).endsWith("/projects/list"))
			return response({ items: projects(), next: null });
		if (String(url).endsWith("/projects/delete")) {
			deletes.push(JSON.parse(String(init.body)));
			return response({ error: { code: "route_missing" } }, 404);
		}
		throw new Error("unexpected fetch " + String(url));
	}, store);
	t.after(() => mounted.dispose());
	await act(async () => deleteIcon().click());
	await act(async () => confirmButton().click());
	await until(() =>
		document
			.querySelector(".lp-delete-confirm")
			?.textContent.includes("The project could not be deleted."),
	);
	assert.ok(document.querySelector(".lp-delete-confirm"));
	assert.ok(document.body.textContent.includes("Delete me"));
	assert.equal(deletes.length, 1);
});

test("a changed revision explains itself and the retry is a new command for the listed revision", async (t) => {
	const store = recordingStore();
	const deletes = [];
	let confirmations = 0;
	// The first command loses a race: the project moved to revision 2 before it
	// arrived, and the workspace now lists that revision.
	let current = 1;
	const mounted = await mount(async (url, init) => {
		if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
		if (String(url).endsWith("/bootstrap")) return response(session());
		if (String(url).endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (String(url).endsWith("/projects/list")) {
			const items = projects();
			items[0] = { ...items[0], revision: current };
			return response({ items, next: null });
		}
		if (String(url).endsWith("/projects/read")) {
			confirmations++;
			return response({
				id: "1".repeat(32),
				title: "Delete me",
				revision: current,
				input_sha256: "2".repeat(64),
				inputs: {},
			});
		}
		if (String(url).endsWith("/projects/delete")) {
			deletes.push(JSON.parse(String(init.body)));
			if (deletes.length === 1) {
				current = 2;
				return response({ error: { code: "conflict" } }, 409);
			}
			return response({
				project_id: "1".repeat(32),
				revision: current,
				deleted: true,
			});
		}
		throw new Error("unexpected fetch " + String(url));
	}, store);
	t.after(() => mounted.dispose());
	await act(async () => deleteIcon().click());
	await until(() => document.querySelector(".lp-delete-confirm"));
	await act(async () => confirmButton().click());
	await until(() =>
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes("This project changed before it could be deleted."),
	);
	assert.equal(confirmations, 1);
	// A key is bound to one command, so the retry cannot repeat the refused one.
	await until(() =>
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes("at revision 2?"),
	);
	await act(async () => confirmButton().click());
	await until(
		() => deletes.length === 2 && !document.querySelector(".lp-delete-confirm"),
	);
	assert.equal(deletes[0].expected_revision, 1);
	assert.equal(deletes[1].expected_revision, 2);
	assert.notEqual(deletes[1].key, deletes[0].key);
});

test("a handoff refusal names the inquiry and keeps the project listed", async (t) => {
	const store = recordingStore();
	const mounted = await mount(async (url) => {
		if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
		if (String(url).endsWith("/bootstrap")) return response(session());
		if (String(url).endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (String(url).endsWith("/projects/list"))
			return response({ items: projects(), next: null });
		if (String(url).endsWith("/projects/read"))
			return response({
				id: "1".repeat(32),
				title: "Delete me",
				revision: 1,
				input_sha256: "2".repeat(64),
				inputs: {},
			});
		if (String(url).endsWith("/projects/delete"))
			return response({ error: { code: "conflict" } }, 409);
		throw new Error("unexpected fetch " + String(url));
	}, store);
	t.after(() => mounted.dispose());
	await act(async () => deleteIcon().click());
	await act(async () => confirmButton().click());
	await until(() =>
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes(
				"This project was handed to the Linker team as an inquiry and cannot be deleted.",
			),
	);
	assert.ok(document.body.textContent.includes("Delete me"));
});

test("a failed delete recovers with the same request and repeated clicks send one command", async (t) => {
	const store = recordingStore();
	const deletes = [];
	const gate = deferred();
	let attempts = 0;
	const mounted = await mount(async (url, init) => {
		if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
		if (String(url).endsWith("/bootstrap")) return response(session());
		if (String(url).endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (String(url).endsWith("/projects/list"))
			return response({ items: projects(), next: null });
		if (String(url).endsWith("/projects/delete")) {
			attempts++;
			deletes.push(JSON.parse(String(init.body)));
			if (attempts === 1) {
				await gate.promise;
				return response({ error: { code: "request_failed" } }, 502);
			}
			return response({
				project_id: "1".repeat(32),
				revision: 1,
				deleted: true,
			});
		}
		throw new Error("unexpected fetch " + String(url));
	}, store);
	t.after(() => mounted.dispose());
	await act(async () => deleteIcon().click());
	await act(async () => confirmButton().click());
	await until(() => attempts === 1);
	// While the command is in flight the entry points are disabled and a
	// second click cannot start another delete.
	assert.ok(confirmButton().disabled);
	await act(async () => confirmButton().click());
	assert.equal(deletes.length, 1);
	await act(async () => gate.resolve());
	await until(() =>
		document
			.querySelector(".lp-delete-confirm")
			.textContent.includes("The project could not be deleted."),
	);
	await act(async () => confirmButton().click());
	await until(
		() => deletes.length === 2 && !document.querySelector(".lp-delete-confirm"),
	);
	assert.equal(deletes[1].key, deletes[0].key);
});
