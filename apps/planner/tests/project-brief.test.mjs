/** The customer's own note reaches the created project unchanged. */
import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { enter, setupDom, until } from "./dom-fixture.mjs";
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

async function openBrief(t, hints = null) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ProjectBriefStart } =
		await import("../src/components/ProjectBriefStart.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const current = session();
	const requests = [];
	const record = {
		schema_version: 1,
		brief_id: BRIEF_ID,
		revision: REVISION,
		text: NOTE,
		source_path: "/for-installer/",
	};
	const state = {
		failStage: false,
		failCreate: false,
		holdStage: null,
		created: null,
		record,
	};
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
			if (path.endsWith("/sources/project-brief")) return response(record);
			if (path.endsWith("/sources/project-brief/stage")) {
				const command = JSON.parse(init.body);
				if (state.holdStage) await state.holdStage;
				if (command.expected_revision !== record.revision)
					return new Response(
						JSON.stringify({ code: "linker_planner_project_brief_conflict" }),
						{ status: 409 },
					);
				if (state.failStage) return new Response("", { status: 503 });
				Object.assign(record, {
					text: command.text,
					revision: (record.revision === REVISION ? "b" : "c").repeat(64),
				});
				return response(record);
			}
			if (path.endsWith("/projects/create")) {
				if (state.failCreate) return new Response("{}", { status: 503 });
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
					entryHints: hints,
					session: current,
					client,
					store,
					locale: "en",
					recheck: () => assert.fail("unexpected identity failure"),
					created: (project) => {
						state.created = project;
						return true;
					},
					recoveryScopes: [current.query_scope],
					dismiss: () => assert.fail("unexpected dismissal"),
				}),
			),
		),
	);
	await until(() => fixture.element.textContent.includes("Your project note"));
	const button = (label) =>
		[...fixture.element.querySelectorAll("button")].find(
			(b) => b.textContent === label,
		);
	const click = async (label) => {
		const b = button(label);
		assert.ok(b, label);
		await act(async () => b.click());
	};
	await until(
		() =>
			button("Continue with solar") && !button("Continue with solar").disabled,
	);
	return { fixture, state, requests, click, button };
}

test("Next carries the staged note without inferring sizing", async (t) => {
	const { fixture, state, click } = await openBrief(t);
	assert.equal(fixture.element.querySelector("textarea").value, NOTE);
	await click("Continue with solar");
	await until(() => state.created);
	const { inputs } = state.created;
	assert.equal(inputs.brief.project_note, NOTE);
	assert.equal(inputs.brief.annual_load.kwh, null);
	assert.equal(inputs.brief.site.location_label, "");
	assert.equal(inputs.equipment_setup, undefined);
});

test("after editing the site, consent and a note edit are carried on Next", async (t) => {
	const { readEntryHints } = await import("../src/domain/entryHints.ts");
	const { fixture, state, click, requests, button } = await openBrief(
		t,
		readEntryHints(
			new URLSearchParams("plz=81671&annual_kwh=8000&pv_kwp=10&phase=3"),
		),
	);
	await enter(
		fixture.element.querySelector('[name="location_label"]'),
		"Customer site",
	);
	await click("Use these values");
	await enter(fixture.element.querySelector("textarea"), "Revised requirement");
	await click("Continue with solar");
	await until(() => state.created);
	const { inputs } = state.created;
	assert.equal(inputs.brief.project_note, "Revised requirement");
	assert.equal(inputs.brief.site.location_label, "Customer site");
	assert.equal(inputs.brief.annual_load.kwh, 8000);
	assert.equal(inputs.equipment_setup.pv_dc_kw, 10);
	assert.equal(inputs.equipment_setup.grid_phase, 3);
	assert.equal(requests.filter(([p]) => p.endsWith("/stage")).length, 1);
	assert.equal(button("Save"), undefined);
});

test("a failed stage keeps the form open; retrying Next does not opt into sizing", async (t) => {
	const { readEntryHints } = await import("../src/domain/entryHints.ts");
	const { fixture, state, click, requests } = await openBrief(
		t,
		readEntryHints(new URLSearchParams("annual_kwh=8000")),
	);
	state.failStage = true;
	await enter(fixture.element.querySelector("textarea"), "Edited brief");
	await click("Continue with solar");
	await until(() =>
		fixture.element.textContent.includes(
			"The project note could not be carried over.",
		),
	);
	assert.equal(fixture.element.querySelector("textarea").value, "Edited brief");
	assert.ok(!requests.some(([p]) => p.endsWith("/create")));
	state.failStage = false;
	state.failCreate = true;
	await click("Continue with solar");
	await until(() =>
		fixture.element.textContent.includes("Retry project creation"),
	);
	state.failCreate = false;
	await click("Retry project creation");
	await until(() => state.created);
	const creates = requests.filter(([p]) => p.endsWith("/create"));
	assert.equal(creates.length, 2);
	assert.equal(creates[0][1], creates[1][1]);
	assert.equal(state.created.inputs.brief.annual_load.kwh, null);
	assert.equal(state.created.inputs.brief.project_note, "Edited brief");
});
test("a conflicting staged brief stays open until the customer chooses a revision", async (t) => {
	const { fixture, state, click, button } = await openBrief(t);
	Object.assign(state.record, {
		revision: "c".repeat(64),
		text: "Other tab's note",
	});
	await enter(fixture.element.querySelector("textarea"), "My open note");
	await click("Continue with solar");
	await until(() => button("Use saved revision"));
	assert.equal(fixture.element.querySelector("textarea").value, "My open note");
	assert.ok(fixture.element.textContent.includes("Other tab's note"));
	assert.equal(state.created, null);
	await click("Use saved revision");
	await click("Continue with solar");
	await until(() => state.created);
	assert.equal(state.created.inputs.brief.project_note, "Other tab's note");
});
test("autosave followed immediately by Next stages only the latest subsequent edit", async (t) => {
	const { fixture, state, click, requests } = await openBrief(t);
	let release;
	state.holdStage = new Promise((resolve) => {
		release = resolve;
	});
	await enter(fixture.element.querySelector("textarea"), "First edit");
	await until(() => requests.some(([p]) => p.endsWith("/stage")));
	await enter(fixture.element.querySelector("textarea"), "Second edit");
	await click("Continue with solar");
	await act(async () => {
		release();
	});
	await until(() => state.created);
	assert.deepEqual(
		requests
			.filter(([p]) => p.endsWith("/stage"))
			.map(([, body]) => JSON.parse(body).text),
		["First edit", "Second edit"],
	);
	assert.equal(state.created.inputs.brief.project_note, "Second edit");
});
