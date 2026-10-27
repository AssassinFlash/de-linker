import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";

test("a deferred close refused during same-scope verification remains retryable", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
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
	const project = {
		id: "1".repeat(32),
		title: "Synthetic close fixture",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: { brief: emptyBrief() },
	};
	const flushGate = deferred(),
		bootstrapGate = deferred();
	let closing = false,
		writing = false,
		verifying = false,
		bootstraps = 0;
	const response = (value) =>
		new Response(JSON.stringify(value), {
			headers: { "Content-Type": "application/json" },
		});
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url) => {
			if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
			if (String(url).endsWith("/bootstrap")) {
				bootstraps++;
				if (verifying) await bootstrapGate.promise;
				return response(session);
			}
			if (String(url).endsWith("/recovery/scopes"))
				return response({ schema_version: 1, scopes: [], next: null });
			if (String(url).endsWith("/projects/read")) return response(project);
			assert.ok(String(url).endsWith("/projects/list"));
			return response({ items: [], next: null });
		},
	});
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
		async readCreations() {
			return [];
		},
		async write() {
			if (closing) {
				writing = true;
				await flushGate.promise;
			}
		},
	};
	const config = {
		locale: "en-GB",
		countries: { NO: "Norway" },
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
	};
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
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
	await until(() => document.querySelector("textarea"));
	await enter(document.querySelector("textarea"), "SYNTHETIC UNSAVED NOTE");
	const projects = () =>
		[...document.querySelectorAll("button")].find(
			(button) => button.textContent === "Projects",
		);
	closing = true;
	await act(async () => projects().click());
	await until(() => writing);
	verifying = true;
	const before = bootstraps;
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await until(() => bootstraps > before);
	assert.equal(client.isCurrentScope(session.query_scope), false);
	await act(async () => flushGate.resolve());
	await act(async () => bootstrapGate.resolve());
	await until(
		() =>
			client.isCurrentScope(session.query_scope) &&
			!document.querySelector(".lp-project").parentElement.hidden,
	);
	assert.equal(projects().disabled, false);
	assert.equal(
		document.querySelector("textarea").value,
		"SYNTHETIC UNSAVED NOTE",
	);
	assert.equal(location.search, "?project=" + project.id);
	closing = false;
	await act(async () => projects().click());
	await until(() => document.querySelector(".lp-workspace"));
	assert.equal(location.search, "");
	assert.ok(document.body.textContent.includes("Your projects"));
});
