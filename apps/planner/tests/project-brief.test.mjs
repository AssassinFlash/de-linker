/** The customer's own note reaches the created project unchanged. */
import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, until } from "./dom-fixture.mjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const BRIEF_ID = "0123456789abcdef0123456789abcdef";
const REVISION = "a".repeat(64);
const NOTE = "SAJ H2-10K, 6000 W, west roof\nno backup";

function session() {
	return {
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
}

test("a staged note is shown verbatim, infers no sizing, and is created as brief.project_note", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ProjectBriefStart } =
		await import("../src/components/ProjectBriefStart.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const current = session();
	const requests = [];
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
			if (String(url).endsWith("/bootstrap")) return response(current);
			const path = String(url);
			requests.push([path, init?.body]);
			if (path.endsWith("/sources/project-brief"))
				return response({
					schema_version: 1,
					brief_id: BRIEF_ID,
					revision: REVISION,
					text: NOTE,
					source_path: "/for-installer/",
				});
			if (path.endsWith("/projects/create")) {
				const command = JSON.parse(init.body);
				return response({
					id: "1".repeat(32),
					title: command.title,
					revision: 1,
					input_sha256: "2".repeat(64),
					inputs: command.inputs,
				});
			}
			throw new Error("unexpected request " + path);
		},
	});
	await client.bootstrap();
	let created = null;
	const store = {
		async readCreations() {
			return [];
		},
		async writeCreation() {},
		async clearCreation() {},
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
				React.createElement(ProjectBriefStart, {
					briefId: BRIEF_ID,
					session: current,
					client,
					store,
					locale: "en",
					recheck: () => assert.fail("unexpected identity failure"),
					created: (project) => {
						created = project;
						return true;
					},
					recoveryScopes: [current.query_scope],
					dismiss: () => assert.fail("unexpected dismissal"),
				}),
			),
		),
	);
	await until(() => fixture.element.textContent.includes("Your project note"));
	// No structured link values: every row must say "Not entered", even though
	// the note itself mentions 6000 W and a model name.
	const text = fixture.element.textContent;
	assert.ok(text.includes(NOTE));
	assert.ok(text.includes("Not entered"));
	assert.ok(!text.includes("Carried over"));

	await act(async () => {
		fixture.element
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			);
	});
	await until(() => created !== null);
	const command = JSON.parse(
		requests.find(([path]) => path.endsWith("/projects/create"))[1],
	);
	assert.equal(command.inputs.brief.project_note, NOTE);
	// The note never becomes a sizing input.
	assert.equal(command.inputs.brief.annual_load.kwh, null);
	assert.equal(command.inputs.brief.site.location_label, "");
	assert.equal(command.inputs.equipment_setup, undefined);
});
