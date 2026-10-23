import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until } from "./dom-fixture.mjs";
import { useProjectDraft } from "../src/data/useProjectDraft.ts";
import { ApiError } from "../src/data/protocol.ts";
import { editDraft } from "../src/domain/draft.ts";

for (const code of ["request_failed", "invalid_json_object", "invalid_input"])
	test(`${code}: revision retry keeps or releases the original key according to the identified refusal`, async (t) => {
		const fixture = setupDom(),
			{ createRoot } = await import("react-dom/client");
		const project = {
			id: "1".repeat(32),
			title: "Synthetic revision",
			revision: 1,
			input_sha256: "2".repeat(64),
			inputs: {},
		};
		const session = {
			query_scope: "3".repeat(64),
			runtime: { limits: { max_json_depth: 32, max_body_bytes: 1000000 } },
		};
		const sent = [],
			cache = new QueryClient();
		let local = null,
			hook;
		const store = {
			async read() {
				return local;
			},
			async candidates() {
				return [];
			},
			async write(_scope, value) {
				local = structuredClone(value);
			},
		};
		const client = {
			isCurrentScope: () => true,
			async send(_path, body) {
				sent.push(body);
				throw new ApiError(422, code);
			},
		};
		function Probe() {
			hook = useProjectDraft(project, session, client, store, () =>
				assert.fail("Unexpected identity error"),
			);
			return null;
		}
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
					React.createElement(Probe),
				),
			),
		);
		await until(() => hook.draft !== null);
		await act(async () =>
			hook.update((previous) =>
				editDraft(previous, { note: "Uncertain original" }),
			),
		);
		await act(async () => hook.save());
		const first = JSON.parse(sent[0]);
		assert.equal(hook.draft.pending !== null, code !== "invalid_input");
		await act(async () => hook.save());
		const second = JSON.parse(sent[1]);
		assert.equal(first.key === second.key, code !== "invalid_input");
		if (code !== "invalid_input") assert.equal(sent[0], sent[1]);
		assert.equal(hook.draft.history.current.note, "Uncertain original");
	});
