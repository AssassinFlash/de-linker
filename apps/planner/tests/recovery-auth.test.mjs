import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until, deferred } from "./dom-fixture.mjs";

test("a transient authentication refusal recovers native reads without replaying a mutation", async (t) => {
	const dom = setupDom();
	history.replaceState(null, "", "/workspace/");
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
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
	const json = (body, status = 200) =>
		new Response(JSON.stringify(body), {
			status,
			headers: { "Content-Type": "application/json" },
		});
	const gate = deferred();
	let bootstraps = 0,
		discoveryCalls = 0;
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/api/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) {
				bootstraps++;
				return json(session);
			}
			if (path.endsWith("/projects/list"))
				return json({ items: [], next: null });
			if (path.endsWith("/recovery/scopes")) {
				discoveryCalls++;
				if (discoveryCalls === 1) {
					await gate.promise;
					return json({ error: { code: "identity_refused" } }, 401);
				}
				return json({
					schema_version: 1,
					scopes: [session.query_scope],
					next: null,
				});
			}
			assert.fail(path);
		},
	});
	const store = {
		async readCreations() {
			return [];
		},
	};
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(SessionBoundary, { client }, (confirmed, recheck) =>
				React.createElement(Workspace, {
					key: confirmed.query_scope,
					session: confirmed,
					client,
					store,
					config: { locale: "en-GB", countries: { NO: "Norway" } },
					recheck,
				}),
			),
		),
	);
	await until(() => document.body.textContent.includes("Project workspace"));
	await act(async () => gate.resolve());
	await until(
		() =>
			bootstraps >= 2 &&
			discoveryCalls >= 2 &&
			client.isCurrentScope(session.query_scope) &&
			[...document.querySelectorAll("button")].some(
				(x) => x.textContent === "New project" && !x.disabled,
			),
	);
	assert.equal(
		document.body.textContent.includes("earlier sessions could not be checked"),
		false,
	);
	assert.equal(
		document.body.textContent.includes("Saved projects could not be loaded"),
		false,
	);
	assert.equal(bootstraps, 2);
	assert.equal(discoveryCalls, 2);
});

for (const status of [401, 503])
	test(`recovery ${status} has bounded verification and a working explicit retry`, async (t) => {
		const dom = setupDom();
		history.replaceState(null, "", "/workspace/");
		const { createRoot } = await import("react-dom/client");
		const { SessionBoundary } =
			await import("../src/components/SessionBoundary.tsx");
		const { Workspace } = await import("../src/components/Workspace.tsx");
		const { PlannerClient } = await import("../src/data/PlannerClient.ts");
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
		const json = (body, status = 200) =>
			new Response(JSON.stringify(body), {
				status,
				headers: { "Content-Type": "application/json" },
			});
		let bootstraps = 0,
			discoveryCalls = 0,
			failing = true;
		const client = new PlannerClient({
			origin: location.origin,
			baseUrl: location.origin + "/api/",
			nonceUrl: location.origin + "/nonce",
			fetch: async (url) => {
				const path = new URL(url).pathname;
				if (path === "/nonce") return new Response("abcdefghij");
				if (path.endsWith("/bootstrap")) {
					bootstraps++;
					return json(session);
				}
				if (path.endsWith("/projects/list"))
					return json({ items: [], next: null });
				if (path.endsWith("/recovery/scopes")) {
					discoveryCalls++;
					return failing
						? json({ error: { code: "synthetic_refusal" } }, status)
						: json({
								schema_version: 1,
								scopes: [session.query_scope],
								next: null,
							});
				}
				assert.fail(
					"Discovery must not automatically send any mutation: " + path,
				);
			},
		});
		const root = createRoot(dom.element);
		t.after(() => dom.dispose(root));
		await act(async () =>
			root.render(
				React.createElement(SessionBoundary, { client }, (confirmed, recheck) =>
					React.createElement(Workspace, {
						key: confirmed.query_scope,
						session: confirmed,
						client,
						store: {
							async readCreations() {
								return [];
							},
						},
						config: { locale: "en-GB", countries: { NO: "Norway" } },
						recheck,
					}),
				),
			),
		);
		const retry = () =>
			[...document.querySelectorAll("button")].find(
				(x) => x.textContent === "Try again",
			);
		await until(() => retry() && (status === 503 || discoveryCalls >= 2));
		for (let i = 0; i < 8; i++)
			await act(async () => {
				await new Promise((resolve) => setTimeout(resolve, 0));
			});
		assert.equal(
			bootstraps,
			status === 401 ? 2 : 1,
			"one automatic native verification for authentication failure, none for ordinary failure",
		);
		const priorBootstraps = bootstraps,
			priorCalls = discoveryCalls;
		if (status === 401) {
			await act(async () => retry().click());
			await until(() => discoveryCalls === priorCalls + 1);
			for (let i = 0; i < 8; i++)
				await act(async () => {
					await new Promise((resolve) => setTimeout(resolve, 0));
				});
			assert.equal(bootstraps, priorBootstraps + 1);
			assert.equal(
				discoveryCalls,
				priorCalls + 1,
				"persistent refusal must wait for another explicit action",
			);
		}
		failing = false;
		await act(async () => retry().click());
		await until(
			() =>
				client.isCurrentScope(session.query_scope) &&
				!retry() &&
				[...document.querySelectorAll("button")].some(
					(x) => x.textContent === "New project" && !x.disabled,
				),
		);
		assert.equal(bootstraps, status === 401 ? 4 : 1);
	});
