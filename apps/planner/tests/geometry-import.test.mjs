import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred, enter } from "./dom-fixture.mjs";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { GeometryImportStore } from "../src/data/GeometryImportStore.ts";
import { useGeometryImport } from "../src/data/useGeometryImport.ts";

const asset = JSON.parse(
		readFileSync(
			new URL(
				"../../../fixtures/planning/geometry-import-asset.json",
				import.meta.url,
			),
			"utf8",
		),
	),
	source = readFileSync(
		new URL(
			"../../../fixtures/planning/source-roof-wgs84.geojson",
			import.meta.url,
		),
	),
	scope = "a".repeat(64),
	projectId = asset.project_id;
const command = () => ({
	schema_version: 1,
	project_id: projectId,
	content_base64: source.toString("base64"),
	options: asset.metadata.geometry_import_options,
	key: crypto.randomUUID(),
});
const session = {
	schema_version: 1,
	kind: "guest",
	cookie_confirmed: true,
	expires_at: 2000000000,
	query_scope: scope,
	nonce: "abcdefghij",
	claim_pending: false,
	runtime: {
		schema_version: 1,
		runtime_sha256: "4".repeat(64),
		models: {},
		limits: {
			max_body_bytes: 16777216,
			max_csv_bytes: 4194304,
			max_page_size: 20,
			max_json_depth: 32,
		},
	},
};
const json = (value, status = 200) =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "Content-Type": "application/json" },
	});

async function rig(
	t,
	{
		writeGate = null,
		replyGate = null,
		lost = false,
		refusal = null,
		previousScope = null,
		intake = false,
		locale = "en-GB",
	} = {},
) {
	const dom = setupDom(),
		prior = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const { createRoot } = await import("react-dom/client");
	const journal = new GeometryImportStore(),
		uploads = [];
	let owner = session,
		rechecks = 0,
		flow,
		writeStarted = false;
	const client = new PlannerClient({
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		origin: location.origin,
		fetch: async (url, init) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return json(owner);
			if (path.endsWith("/geometry/import")) {
				uploads.push(init.body);
				assert.equal(
					(await journal.list([previousScope ?? scope], projectId))[0].body,
					init.body,
					"dispatch requires a committed exact intent",
				);
				if (replyGate) await replyGate.promise;
				if (refusal) return json({ error: { code: refusal } }, 422);
				if (lost) {
					lost = false;
					throw new TypeError("lost acknowledgement");
				}
				return json(asset);
			}
			throw new Error("Unexpected fixture RPC " + path);
		},
	});
	await client.bootstrap();
	const store = {
		list: journal.list.bind(journal),
		clear: journal.clear.bind(journal),
		acknowledge: journal.acknowledge.bind(journal),
		async write(origin, body) {
			writeStarted = true;
			if (writeGate) await writeGate.promise;
			await journal.write(origin, body);
		},
	};
	const root = createRoot(dom.element);
	const { GeometryIntake } =
		await import("../src/components/design/GeometryIntake.tsx");
	const { emptyGeometry } = await import("../src/domain/geometryCommands.ts");
	let activity = false;
	const attachments = [];
	let props = {
		projectId,
		session,
		client,
		recheck: () => {
			rechecks++;
		},
		confirmedAssetIds: [],
		store,
		recoveryScopes: previousScope ? [scope, previousScope] : [scope],
	};
	function Probe() {
		if (intake)
			return React.createElement(GeometryIntake, {
				...props,
				locale,
				geometry: emptyGeometry(),
				disabled: false,
				onActivity: (open) => {
					activity = open;
				},
				currentAssetIds: [],
				attach: (before, prepared) => {
					attachments.push({ before, prepared });
					return true;
				},
			});
		flow = useGeometryImport(props);
		return null;
	}
	async function render(changes = {}) {
		props = { ...props, ...changes };
		await act(async () => root.render(React.createElement(Probe)));
	}
	t.after(async () => {
		await dom.dispose(root);
		if (prior) Object.defineProperty(globalThis, "indexedDB", prior);
		else delete globalThis.indexedDB;
	});
	await render();
	await until(() =>
		intake
			? document.querySelector("button")?.disabled === false
			: !flow.checking,
	);
	return {
		client,
		journal,
		uploads,
		render,
		get flow() {
			return flow;
		},
		get writeStarted() {
			return writeStarted;
		},
		get rechecks() {
			return rechecks;
		},
		get activity() {
			return activity;
		},
		attachments,
		setRefusal(code) {
			refusal = code;
		},
		setOwner(value) {
			owner = value;
		},
	};
}

test("a lost acknowledgement retains original bytes/key across review and an explicit retry", async (t) => {
	const fixture = await rig(t, { lost: true }),
		request = command();
	await act(async () => fixture.flow.prepare(request));
	assert.equal(fixture.flow.asset, null);
	const record = (await fixture.journal.list([scope], projectId))[0];
	assert.equal(record.key, request.key);
	assert.equal(JSON.parse(record.body).content_base64, request.content_base64);
	await act(async () => fixture.flow.dismiss());
	await until(() => fixture.flow.records.length === 1);
	await act(async () => fixture.flow.retry(record));
	await until(
		() =>
			!fixture.flow.checking && fixture.flow.records[0]?.assetId === asset.id,
	);
	assert.equal(fixture.flow.asset.id, asset.id);
	assert.deepEqual(fixture.uploads, [record.body, record.body]);
	assert.equal(
		(await fixture.journal.list([scope], projectId))[0].assetId,
		asset.id,
	);
	await fixture.render({ confirmedAssetIds: [asset.id] });
	await until(
		() => !fixture.flow.checking && fixture.flow.records.length === 0,
	);
	assert.deepEqual(await fixture.journal.list([scope], projectId), []);
});

test("unknown 422 keeps the frozen intent while a typed input refusal releases it", async (t) => {
	const fixture = await rig(t, { refusal: "request_failed" });
	await act(async () => fixture.flow.prepare(command()));
	assert.ok(fixture.flow.intent);
	assert.equal((await fixture.journal.list([scope], projectId)).length, 1);
	const pending = fixture.flow.intent;
	fixture.setRefusal("invalid_input");
	await act(async () => fixture.flow.retry(pending));
	assert.equal(fixture.flow.intent, null);
	assert.deepEqual(await fixture.journal.list([scope], projectId), []);
	assert.deepEqual(fixture.uploads, [pending.body, pending.body]);
});

test("withdrawn native admission during the recovery write prevents dispatch", async (t) => {
	const gate = deferred(),
		fixture = await rig(t, { writeGate: gate });
	let run;
	await act(async () => {
		run = fixture.flow.prepare(command());
	});
	await until(() => fixture.writeStarted);
	fixture.setOwner({ ...session, query_scope: "b".repeat(64) });
	await act(async () => fixture.client.bootstrap());
	await act(async () => {
		gate.resolve();
		await run;
	});
	assert.deepEqual(fixture.uploads, []);
	assert.equal((await fixture.journal.list([scope], projectId)).length, 1);
});

test("a failed journal write prevents upload and keeps an explicit retry in memory", async (t) => {
	const gate = deferred(),
		fixture = await rig(t, { writeGate: gate });
	let run;
	await act(async () => {
		run = fixture.flow.prepare(command());
	});
	await until(() => fixture.writeStarted);
	await act(async () => {
		gate.reject(new Error("Storage unavailable"));
		await run;
	});
	assert.deepEqual(fixture.uploads, []);
	assert.equal(fixture.flow.storageFailed, true);
	assert.equal(fixture.flow.durable, false);
	assert.ok(fixture.flow.intent);
	assert.deepEqual(await fixture.journal.list([scope], projectId), []);
});

test("dismissal and a different native scope cannot accept a delayed server result", async (t) => {
	const gate = deferred(),
		fixture = await rig(t, { replyGate: gate });
	let run;
	await act(async () => {
		run = fixture.flow.prepare(command());
	});
	await until(() => fixture.uploads.length === 1);
	await act(async () => fixture.flow.dismiss());
	fixture.setOwner({ ...session, query_scope: "b".repeat(64) });
	await act(async () => fixture.client.bootstrap());
	await act(async () => {
		gate.resolve();
		await run;
	});
	assert.equal(fixture.flow.asset, null);
	assert.equal((await fixture.journal.list([scope], projectId)).length, 1);
});

test("a native-granted previous namespace replays and cleans up that exact original", async (t) => {
	const oldScope = "c".repeat(64),
		fixture = await rig(t, { previousScope: oldScope }),
		body = JSON.stringify(command());
	await fixture.journal.write(oldScope, body);
	await act(async () => fixture.flow.refresh());
	await until(() => fixture.flow.records.length === 1);
	await act(async () => fixture.flow.retry(fixture.flow.records[0]));
	await until(
		() =>
			!fixture.flow.checking && fixture.flow.records[0]?.assetId === asset.id,
	);
	assert.deepEqual(fixture.uploads, [body]);
	await fixture.render({ confirmedAssetIds: [asset.id] });
	await until(
		() => !fixture.flow.checking && fixture.flow.records.length === 0,
	);
	assert.deepEqual(await fixture.journal.list([oldScope], projectId), []);
});

const button = (label) =>
	[...document.querySelectorAll("button")].find(
		(element) => element.textContent.trim() === label,
	);
const field = (name) => document.querySelector(`[name="${name}"]`);
async function click(label) {
	assert.ok(button(label), label);
	await act(async () => button(label).click());
}

test("guided import retains raw locale input and source holes across Back and a typed refusal", async (t) => {
	const fixture = await rig(t, {
		intake: true,
		locale: "de-DE",
		refusal: "invalid_input",
	});
	await click("Import roof geometry");
	assert.equal(fixture.activity, true);
	await act(async () => {
		const input = document.querySelector('input[type="file"]');
		Object.defineProperty(input, "files", {
			value: [
				{
					name: "survey.geojson",
					size: source.length,
					arrayBuffer: async () => Uint8Array.from(source).buffer,
				},
			],
		});
		input.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await until(() => !button("Continue").disabled);
	assert.equal(field("selection").value, "0:0");
	assert.ok(document.body.textContent.includes("Openings in source: 1"));
	await click("Continue");
	await enter(field("pitch"), "1.");
	await enter(field("bearing"), "180");
	await enter(field("height"), "5");
	await enter(field("basis"), "Synthetic measured plane");
	await click("Continue");
	assert.equal(document.querySelector('[data-import-step="1"]').hidden, false);
	assert.equal(field("pitch").value, "1.");
	assert.deepEqual(fixture.uploads, []);
	await enter(field("pitch"), "30,5");
	await click("Back");
	await click("Continue");
	assert.equal(field("pitch").value, "30,5");
	await click("Continue");
	await enter(field("source"), "Synthetic survey");
	await enter(
		field("rights"),
		"Test original; permission to derive and retain",
	);
	await act(async () => field("retention").click());
	await click("Prepare roof preview");
	await until(
		() =>
			fixture.uploads.length === 1 && !button("Prepare roof preview").disabled,
	);
	const uploaded = JSON.parse(fixture.uploads[0]);
	assert.equal(uploaded.content_base64, source.toString("base64"));
	assert.equal(uploaded.options.source.spatial_precision_m, null);
	assert.equal(uploaded.options.plane.origin_enu[2], 5);
	assert.equal(uploaded.options.reference.longitude_deg, 6.96);
	assert.equal(uploaded.options.reference.latitude_deg, 50.94);
	assert.equal(field("pitch").value, "30,5");
	assert.equal(
		field("rights").value,
		"Test original; permission to derive and retain",
	);
	assert.equal(fixture.attachments.length, 0);
	await click("Close import");
	assert.equal(fixture.activity, false);
	await until(() => document.activeElement === button("Import roof geometry"));
});

test("an earlier upload is explicitly reviewed before its actual fixture roof can join history", async (t) => {
	const fixture = await rig(t, { intake: true }),
		body = JSON.stringify(command());
	await fixture.journal.write(scope, body);
	await fixture.render({ confirmedAssetIds: ["f".repeat(32)] });
	await until(() =>
		button(asset.metadata.geometry_import_options.source.label),
	);
	await click(asset.metadata.geometry_import_options.source.label);
	assert.equal(fixture.uploads.length, 0);
	await click("Check or retry this upload");
	await until(
		() =>
			button("Add roof to current design") &&
			!button("Add roof to current design").disabled,
	);
	assert.equal(fixture.attachments.length, 0);
	assert.equal(
		document
			.querySelector(".lp-import-review svg")
			.getAttribute("aria-label")
			.includes(asset.metadata.geometry_import_options.roof_name),
		true,
	);
	await click("Add roof to current design");
	assert.equal(fixture.attachments.length, 1);
	assert.equal(
		fixture.attachments[0].prepared.geometry.roofs[0].holes_uv.length,
		1,
	);
	assert.equal(fixture.activity, false);
	assert.deepEqual(fixture.uploads, [body]);
});
