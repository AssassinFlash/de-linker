import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";

for (const source of ["prior", "current", "clean-prior"])
	for (const uncertain of source === "clean-prior" ? [false] : [false, true])
		test(`${source} scope: ${uncertain ? "uncertain intent remains reviewable" : "now-saved edits do not reappear as unsaved"}`, async (t) => {
			const fixture = setupDom();
			const { createRoot } = await import("react-dom/client");
			const { QueryClient, QueryClientProvider } =
				await import("@tanstack/react-query");
			const { ProjectEditor } =
				await import("../src/components/ProjectEditor.tsx");
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
						project_note: "Saved after native account handover",
					},
				},
			};
			let previous =
				source === "clean-prior"
					? beginDraft(old)
					: editDraft(beginDraft(old), current.inputs);
			if (uncertain)
				previous = prepareSave(previous, crypto.randomUUID(), {
					maxBytes: 1000000,
					maxDepth: 32,
				});
			const savedLocal = beginDraft(current);
			const client = new PlannerClient({
				origin: location.origin,
				baseUrl: location.origin + "/rpc/",
				nonceUrl: location.origin + "/nonce",
				fetch: async (url) => {
					if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
					assert.ok(
						String(url).endsWith("/bootstrap"),
						"recovery must not resubmit a mutation",
					);
					return new Response(JSON.stringify(session), {
						headers: { "Content-Type": "application/json" },
					});
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
				async readProfileImports() {
					return [];
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
			});
			await act(async () =>
				root.render(
					React.createElement(
						QueryClientProvider,
						{ client: cache },
						React.createElement(ProjectEditor, {
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
			await until(() => document.querySelector("textarea"));
			assert.equal(
				document.querySelector("textarea").value,
				current.inputs.brief.project_note,
			);
			assert.equal(
				document.body.textContent.includes(
					"Open changes have been kept alongside the saved revision.",
				),
				uncertain && source === "prior",
			);
			if (uncertain && source === "current")
				assert.ok(document.body.textContent.includes("Retry save"));
			if (!uncertain) {
				assert.ok(document.body.textContent.includes("Saved · revision 2"));
				assert.equal(
					document.body.textContent.includes("Unsaved changes"),
					false,
				);
			}
		});
