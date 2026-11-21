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

async function mount(handler, store, url = "/workspace/") {
	const fixture = setupDom();
	// The shared fixture URL preselects a project; deletion lives in the list.
	history.replaceState({}, "", url);
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
	await until(() => document.querySelector('[role="listitem"]'));
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
	document.querySelectorAll('button[aria-label^="Delete project "]')[0];

const confirmButton = () =>
	[
		...document.querySelectorAll(
			'[role="group"][aria-label="Delete this project"] button',
		),
	].find((button) => button.className.includes("sc-button-danger"));

test("the account search opens directly at the older project list", async (t) => {
	const listRequests = [];
	const historical = { ...projects()[1], title: "Alte Straße" };
	const mounted = await mount(
		async (url, init) => {
			const path = String(url);
			if (path.endsWith("/nonce")) return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return response(session());
			if (path.endsWith("/projects/list")) {
				const query = JSON.parse(init.body);
				listRequests.push(query);
				return response({
					items: query.title_query === "Straße" ? [historical] : projects(),
					next: null,
					ordering:
						"updated_at_desc_id_desc; live_navigation_not_a_frozen_search",
				});
			}
			if (path.endsWith("/recovery/scopes"))
				return response({ scopes: [session().query_scope] });
			throw new Error(path);
		},
		recordingStore(),
		"/workspace/?projects=1&project_search=Stra%C3%9Fe",
	);
	t.after(() => mounted.dispose());

	assert.equal(listRequests[0].title_query, "Straße");
	assert.equal(
		document.querySelector('[role="listitem"] h3').textContent,
		"Alte Straße",
	);
	assert.equal(document.querySelector('input[type="search"]').value, "Straße");
	assert.equal(document.querySelector('input[name="title"]'), null);
	const { projectLanguageUrl } =
		await import("../src/data/useSiteIntegration.ts");
	const translated = new URL(projectLanguageUrl("/de/", location.href, null));
	assert.equal(translated.searchParams.get("projects"), "1");
	assert.equal(translated.searchParams.get("project_search"), "Straße");
});

test("a refreshing list waits for the saved revision before offering deletion", async (t) => {
	const refresh = deferred();
	let refreshing = false;
	const mounted = await mount(async (url) => {
		const path = new URL(url).pathname;
		if (path.endsWith("/nonce")) return new Response("abcdefghij");
		if (path.endsWith("/bootstrap")) return response(session());
		if (path.endsWith("/recovery/scopes"))
			return response({ schema_version: 1, scopes: [], next: null });
		if (path.endsWith("/projects/list")) {
			const items = projects();
			if (refreshing) {
				await refresh.promise;
				items[0].revision = 3;
			}
			return response({ items, next: null });
		}
		throw new Error("unexpected fetch " + path);
	}, recordingStore());
	t.after(() => mounted.dispose());
	refreshing = true;
	await act(async () =>
		document.querySelector('button[aria-label="Refresh projects"]').click(),
	);
	await act(async () => deleteIcon().click());
	const showedStaleConfirmation = Boolean(confirmButton());
	await act(async () => refresh.resolve());
	assert.equal(showedStaleConfirmation, false);
	await until(() => !deleteIcon().disabled);
	await act(async () => deleteIcon().click());
	assert.match(
		document.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent,
		/at revision 3/,
	);
});

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
	assert.equal(document.querySelector('[role="listitem"] button button'), null);
	await act(async () => deleteIcon().click());
	await until(() =>
		document.querySelector('[role="group"][aria-label="Delete this project"]'),
	);
	assert.ok(
		document
			.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent.includes('Delete the project "Delete me" at revision 1?'),
	);
	assert.ok(
		document
			.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent.includes("revision 1"),
	);
	const before = lists;
	await act(async () => confirmButton().click());
	await until(() => lists > before && deletes.length === 1);
	assert.equal(deletes[0].schema_version, 1);
	assert.equal(deletes[0].project_id, "1".repeat(32));
	assert.equal(deletes[0].expected_revision, 1);
	assert.match(deletes[0].key, /^[a-f0-9-]{36}$/);
	await until(
		() =>
			!document.querySelector(
				'[role="group"][aria-label="Delete this project"]',
			),
	);
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
			.querySelector('[role="group"][aria-label="Delete this project"]')
			?.textContent.includes("The project could not be deleted."),
	);
	assert.ok(
		document.querySelector('[role="group"][aria-label="Delete this project"]'),
	);
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
	await until(() =>
		document.querySelector('[role="group"][aria-label="Delete this project"]'),
	);
	await act(async () => confirmButton().click());
	await until(() =>
		document
			.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent.includes("This project changed before it could be deleted."),
	);
	assert.equal(confirmations, 1);
	// A key is bound to one command, so the retry cannot repeat the refused one.
	await until(() =>
		document
			.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent.includes("at revision 2?"),
	);
	await act(async () => confirmButton().click());
	await until(
		() =>
			deletes.length === 2 &&
			!document.querySelector(
				'[role="group"][aria-label="Delete this project"]',
			),
	);
	assert.equal(deletes[0].expected_revision, 1);
	assert.equal(deletes[1].expected_revision, 2);
	assert.notEqual(deletes[1].key, deletes[0].key);
});

for (const [code, message] of [
	[
		"inquiry_linked",
		"This project was handed to the Linker team as an inquiry and cannot be deleted.",
	],
	["inquiry_changed", "The project could not be deleted."],
])
	test(`a ${code} refusal explains the result and keeps the project listed`, async (t) => {
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
				return response({ error: { code } }, 409);
			throw new Error("unexpected fetch " + String(url));
		}, store);
		t.after(() => mounted.dispose());
		await act(async () => deleteIcon().click());
		await act(async () => confirmButton().click());
		await until(() =>
			document
				.querySelector('[role="group"][aria-label="Delete this project"]')
				.textContent.includes(message),
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
			.querySelector('[role="group"][aria-label="Delete this project"]')
			.textContent.includes("The project could not be deleted."),
	);
	await act(async () => confirmButton().click());
	await until(
		() =>
			deletes.length === 2 &&
			!document.querySelector(
				'[role="group"][aria-label="Delete this project"]',
			),
	);
	assert.equal(deletes[1].key, deletes[0].key);
});
