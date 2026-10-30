import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

async function exercise(t, historical) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const session = {
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
	};
	const originScope = historical ? "a".repeat(64) : session.query_scope;
	const pending = ["Synthetic tab A", "Synthetic tab B"].map((title, index) => {
		const key = crypto.randomUUID();
		return {
			key,
			title,
			body: JSON.stringify({
				schema_version: 1,
				title,
				inputs: { brief: emptyBrief() },
				key,
			}),
			destination: index === 1 ? "equipment" : null,
			createdAt: index,
		};
	});
	const sent = [],
		cleared = [];
	let created = null,
		createdDestination = null,
		writtenDestination = null;
	const response = (value) =>
		new Response(JSON.stringify(value), {
			headers: { "Content-Type": "application/json" },
		});
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url, init) => {
			if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
			if (String(url).endsWith("/bootstrap")) return response(session);
			assert.ok(String(url).endsWith("/projects/create"));
			sent.push(init.body);
			const command = JSON.parse(init.body);
			return response({
				id: "1".repeat(32),
				title: command.title,
				revision: 1,
				input_sha256: "2".repeat(64),
				inputs: command.inputs,
			});
		},
	});
	await client.bootstrap();
	const store = {
		async readCreations(scope) {
			return scope === originScope ? pending : [];
		},
		async writeCreation(scope, body, destination) {
			assert.equal(scope, originScope);
			assert.equal(body, pending[1].body);
			writtenDestination = destination;
		},
		async clearCreation(scope, body) {
			cleared.push([scope, body]);
		},
	};
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(
					React.StrictMode,
					null,
					React.createElement(NewProject, {
						session,
						client,
						store,
						recoveryScopes: [session.query_scope, originScope],
						recheck: () => assert.fail("unexpected identity failure"),
						created: (project, destination) => {
							created = project;
							createdDestination = destination;
							return true;
						},
					}),
				),
			),
		),
	);
	await until(() => document.querySelector("select"));
	assert.equal(sent.length, 0);
	assert.equal(document.querySelector("input").value, pending[0].title);
	assert.equal(document.querySelector("input").readOnly, true);
	await act(async () => {
		const select = document.querySelector("select");
		select.value = originScope + ":" + pending[1].key;
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(document.querySelector("input").value, pending[1].title);
	assert.equal(sent.length, 0);
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	await until(() => created !== null);
	assert.deepEqual(sent, [pending[1].body]);
	assert.deepEqual(cleared, [[originScope, pending[1].body]]);
	assert.equal(created.title, pending[1].title);
	assert.equal(writtenDestination, "equipment");
	assert.equal(createdDestination, "equipment");
}

test("several pending creations require selection and an explicit retry of the exact bytes", (t) =>
	exercise(t, false));
test("a native-granted prior scope restores exact creations without automatically sending or clearing another scope", (t) =>
	exercise(t, true));
