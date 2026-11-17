import assert from "node:assert/strict";
import test from "node:test";
import { IDBFactory } from "fake-indexeddb";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";

for (const { name, source, uncertain, changed } of [
	{ name: "Prior scope: now-saved edits do not reappear", source: "prior" },
	{ name: "Current scope: now-saved edits do not reappear", source: "current" },
	{
		name: "Clean prior scope: the saved revision is shown",
		source: "clean-prior",
	},
	{
		name: "Current scope: an uncertain save retries its original request",
		source: "current",
		uncertain: true,
	},
	{
		name: "Prior scope: an uncertain save matching the saved revision remains reviewable",
		source: "prior",
		uncertain: true,
	},
	{
		name: "Prior scope: an uncertain save with local edits can be saved against the current revision",
		source: "prior",
		uncertain: true,
		changed: true,
	},
])
	test(name, async (t) => {
		const fixture = setupDom();
		globalThis.indexedDB = new IDBFactory();
		const { createRoot } = await import("react-dom/client");
		const { QueryClient, QueryClientProvider } =
			await import("@tanstack/react-query");
		const { default: Configurator } =
			await import("../src/components/configurator/Configurator.tsx");
		const { PlannerClient } = await import("../src/data/PlannerClient.ts");
		const { emptyBrief } = await import("../src/domain/brief.ts");
		const { beginDraft, editDraft, prepareSave } =
			await import("../src/domain/draft.ts");
		const session = {
			schema_version: 1,
			kind: "user",
			cookie_confirmed: true,
			expires_at: 2000000000,
			query_scope: "a".repeat(64),
			nonce: "abcdefghij",
			claim_pending: false,
			runtime: {
				schema_version: 1,
				runtime_sha256: "b".repeat(64),
				models: {},
				limits: {
					max_body_bytes: 1000000,
					max_csv_bytes: 100000,
					max_page_size: 30,
					max_json_depth: 32,
				},
			},
		};
		const old = {
			id: "1".repeat(32),
			title: "Synthetic recovery",
			revision: 1,
			input_sha256: "2".repeat(64),
			inputs: { brief: emptyBrief() },
		};
		const current = {
			...old,
			revision: 2,
			input_sha256: "3".repeat(64),
			inputs: {
				brief: {
					...emptyBrief(),
					site: { ...emptyBrief().site, location_label: "Saved workshop" },
				},
			},
		};
		const revised = {
			...current,
			revision: 3,
			input_sha256: "4".repeat(64),
			inputs: {
				brief: {
					...current.inputs.brief,
					site: {
						...current.inputs.brief.site,
						location_label: "Local workshop",
					},
				},
			},
		};
		let previous =
			source === "clean-prior"
				? beginDraft(old)
				: editDraft(beginDraft(old), changed ? revised.inputs : current.inputs);
		if (uncertain)
			previous = prepareSave(previous, crypto.randomUUID(), {
				maxBytes: 1000000,
				maxDepth: 32,
			});
		const savedLocal = beginDraft(current);
		const saves = [];
		const client = new PlannerClient({
			origin: location.origin,
			baseUrl: location.origin + "/rpc/",
			nonceUrl: location.origin + "/nonce",
			fetch: async (url, request) => {
				if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
				if (String(url).endsWith("/projects/runs"))
					return Response.json({ items: [], next: null });
				if (String(url).endsWith("/projects/revise")) {
					saves.push(request.body);
					return Response.json(source === "prior" ? revised : current);
				}
				assert.ok(String(url).endsWith("/bootstrap"), String(url));
				return Response.json(session);
			},
		});
		await client.bootstrap();
		const store = {
			async read() {
				return source === "current" ? previous : savedLocal;
			},
			async candidates(scope, authorized) {
				assert.equal(scope, session.query_scope);
				assert.equal(authorized, current);
				return [{ scope: "c".repeat(64), draft: previous, updatedAt: 0 }];
			},
			async write() {},
		};
		const cache = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
		const root = createRoot(fixture.element);
		t.after(async () => {
			await fixture.dispose(root);
			cache.clear();
			delete globalThis.indexedDB;
		});
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						project: current,
						session,
						client,
						store,
						config: { locale: "en-GB", countries: { NO: "Norway" } },
						recheck: () => assert.fail("unexpected identity failure"),
						close: () => true,
					}),
				),
			),
		);
		const field = () => document.querySelector('[name="location_label"]');
		const button = (text) =>
			[...document.querySelectorAll("button")].find(
				(node) => node.textContent === text,
			);
		const status = (text) =>
			[...document.querySelectorAll('[role="status"]')].some(
				(node) => node.textContent === text,
			);
		await until(field);
		assert.equal(field().value, changed ? "Local workshop" : "Saved workshop");
		assert.deepEqual(saves, [], "opening the project must not resubmit a save");
		if (!uncertain) {
			assert.ok(status("Saved · revision 2"));
			assert.equal(status("Unsaved changes"), false);
			assert.equal(button("Restore local changes"), undefined);
			assert.equal(button("Keep my changes"), undefined);
			assert.equal(button("Retry save"), undefined);
			await act(async () => button("Save snapshot").click());
			assert.deepEqual(saves, []);
		} else if (source === "current") {
			assert.ok(status("Save not confirmed"));
			assert.equal(button("Retry save")?.disabled, false);
			await act(async () => button("Retry save").click());
			await until(() => status("Saved · revision 2"));
			assert.deepEqual(
				saves,
				[previous.pending.body],
				"retry uses the original save request",
			);
		} else {
			assert.ok(button("Use saved project"));
			assert.equal(button("Save snapshot").disabled, true);
			if (!changed) {
				await act(async () => button("Use saved project").click());
				assert.ok(status("Saved · revision 2"));
				assert.equal(button("Keep my changes"), undefined);
				assert.deepEqual(saves, []);
				return;
			}
			await act(async () => button("Keep my changes").click());
			assert.equal(field().value, "Local workshop");
			assert.ok(status("Unsaved changes"));
			await act(async () => button("Save snapshot").click());
			await until(() => status("Saved · revision 3"));
			assert.equal(saves.length, 1);
			const command = JSON.parse(saves[0]);
			assert.equal(command.expected_revision, 2);
			assert.equal(command.inputs.brief.site.location_label, "Local workshop");
			assert.notEqual(
				command.key,
				previous.pending.key,
				"the confirmed identity starts a new save",
			);
		}
	});
