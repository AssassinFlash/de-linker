import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred } from "./dom-fixture.mjs";
import { EnergyIntentStore } from "../src/data/EnergyIntentStore.ts";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { useEnergyOperations } from "../src/data/useEnergyOperations.ts";
import result from "./fixtures/energy-run.json" with { type: "json" };
import scenario from "./fixtures/energy-scenario.json" with { type: "json" };

const scope = "a".repeat(64),
	projectId = result.project_id;
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
		runtime_sha256: result.manifest.context.code_sha256,
		models: result.manifest.context.models,
		limits: {
			max_body_bytes: 16777216,
			max_csv_bytes: 8388608,
			max_page_size: 100,
			max_json_depth: 32,
		},
	},
};
const json = (value, status = 200) =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "Content-Type": "application/json" },
	});

async function rig(t, respond, options = {}) {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const durable = new EnergyIntentStore(),
		calls = [];
	let owner = session,
		api,
		props = {
			projectId,
			session,
			store: options.store ?? durable,
			recoveryScopes: [scope],
			...options,
		};
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/wp-json/planner/",
		nonceUrl: "https://fixture.invalid/nonce",
		origin: "https://fixture.invalid",
		fetch: async (url, request) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return json(owner);
			calls.push({
				path: path.split("/rpc/")[1],
				body: request.body,
				headers: request.headers,
			});
			return await respond(calls.at(-1), request);
		},
	});
	await client.bootstrap();
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	function Probe() {
		api = useEnergyOperations({ ...props, client, recheck: () => {} });
		return React.createElement("p", null, api.checking ? "Checking" : "Ready");
	}
	const render = async (next = {}) => {
		props = { ...props, ...next };
		await act(async () => root.render(React.createElement(Probe)));
	};
	let closed = false;
	t.after(async () => {
		if (!closed) {
			await dom.dispose(root);
			closed = true;
		}
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	await render();
	await until(() => !api.checking);
	return {
		client,
		durable,
		calls,
		get api() {
			return api;
		},
		render,
		async transition(next) {
			owner = next;
			client.invalidate();
			await client.bootstrap();
			await render({
				session: next,
				recoveryScopes: [scope, next.query_scope],
			});
			await until(() => !api.checking);
		},
		async unmount() {
			await act(async () => root.unmount());
		},
	};
}

test("double activation dispatches one durably saved request; a lost response retries the exact original revision/key", async (t) => {
	let first = true;
	const r = await rig(t, async (call) => {
		if (first) {
			first = false;
			throw new TypeError("synthetic lost acknowledgement");
		}
		return json(result);
	});
	await act(async () => {
		await Promise.all([
			r.api.start("runs/energy", { expected_revision: 2 }),
			r.api.start("runs/energy", { expected_revision: 2 }),
		]);
	});
	await until(() => r.api.records.length === 1);
	assert.equal(r.calls.length, 1);
	const stored = (await r.durable.list([scope], projectId))[0];
	assert.equal(stored.body, r.calls[0].body);
	await act(async () => r.api.start("runs/energy", { expected_revision: 9 }));
	assert.equal(
		r.calls.length,
		1,
		"unknown original prevents a replacement request",
	);
	let reply;
	await act(async () => {
		reply = await r.api.retry(stored);
	});
	assert.equal(reply.run.id, result.id);
	assert.equal(r.calls[1].body, r.calls[0].body);
	await until(() => r.api.records.length === 0);
	assert.deepEqual(await r.durable.list([scope], projectId), []);
});

test("storage failure prevents dispatch, remains visible and requires an explicit successful storage check", async (t) => {
	let down = true;
	const store = {
		list: async () => [],
		write: async () => {
			if (down) throw new Error("synthetic quota");
		},
		acknowledge: async () => {},
		clear: async () => {},
	};
	const r = await rig(t, async () => json(result), { store });
	await act(async () => r.api.start("runs/energy", { expected_revision: 2 }));
	assert.equal(r.calls.length, 0);
	assert.equal(r.api.storageFailed, true);
	down = false;
	await act(async () => r.api.start("runs/energy", { expected_revision: 2 }));
	assert.equal(r.calls.length, 0);
	await act(async () => r.api.refresh());
	await until(() => !r.api.checking && !r.api.storageFailed);
	assert.equal(r.calls.length, 0, "storage recovery never auto-submits a task");
	await act(async () => r.api.start("runs/energy", { expected_revision: 2 }));
	assert.equal(r.calls.length, 1);
});

test("unmount while persistence is pending never sends a mutation and retains the eventual durable intent", async (t) => {
	const gate = deferred(),
		saved = [];
	const store = {
		list: async () => saved,
		write: async (s, path, body) => {
			await gate.promise;
			saved.push({
				scope: s,
				path,
				body,
				projectId,
				key: JSON.parse(body).key,
				resultId: null,
				createdAt: 1,
			});
		},
		acknowledge: async () => {},
		clear: async () => {},
	};
	const r = await rig(t, async () => json(result), { store });
	let pending;
	await act(async () => {
		pending = r.api.start("runs/energy", { expected_revision: 2 });
	});
	await r.unmount();
	await act(async () => {
		gate.resolve();
		await pending;
	});
	assert.equal(r.calls.length, 0);
	assert.equal(saved.length, 1);
	assert.equal(JSON.parse(saved[0].body).expected_revision, 2);
});

test("a verified account transition discovers the guest intent but never submits it automatically", async (t) => {
	let lost = true;
	const r = await rig(t, async () => {
		if (lost) throw new TypeError("lost response");
		return json(result);
	});
	await act(async () => r.api.start("runs/energy", { expected_revision: 2 }));
	await until(() => r.api.records.length === 1);
	const original = r.api.records[0];
	await r.transition({ ...session, kind: "user", query_scope: "b".repeat(64) });
	assert.equal(r.calls.length, 1);
	assert.equal(r.api.records[0].body, original.body);
	lost = false;
	await act(async () => r.api.retry(r.api.records[0]));
	assert.equal(r.calls.length, 2);
	assert.equal(r.calls[1].body, original.body);
	assert.equal(
		r.calls[1].headers["X-Linker-Planner-Nonce"],
		undefined,
		"native authenticated session replaces guest nonce authority",
	);
});

test("only a specific proven pre-mutation stale-revision refusal releases a calculation intent", async (t) => {
	let code = "conflict";
	const r = await rig(t, async () => json({ error: { code } }, 409));
	await act(async () => r.api.start("runs/energy", { expected_revision: 2 }));
	await until(() => r.api.records.length === 1);
	const original = r.api.records[0];
	assert.equal((await r.durable.list([scope], projectId)).length, 1);
	code = "evaluation_revision_changed";
	await act(async () => r.api.retry(original));
	await until(() => r.api.records.length === 0);
	assert.deepEqual(await r.durable.list([scope], projectId), []);
});

test("acknowledged battery settings remain recoverable until that asset is saved, or explicitly dismissed", async (t) => {
	const asset = {
		id: "d".repeat(32),
		project_id: projectId,
		content_sha256: "e".repeat(64),
		metadata_sha256: "f".repeat(64),
		media_type: "application/json",
		purpose: "battery_parameters_v1",
		metadata: {
			retention: "permanent",
			provenance: {
				basis: "user_explicit_scenario_not_equipment_release",
				label: scenario.source_note,
			},
		},
	};
	const r = await rig(t, async () => json(asset));
	await act(async () =>
		r.api.start("battery/scenario", {
			parameters: scenario.battery_binding.parameters,
			source_note: scenario.source_note,
		}),
	);
	await until(
		() => r.api.records.length === 1 && r.api.records[0].resultId === asset.id,
	);
	await r.render({ confirmedBatteryId: "c".repeat(32) });
	await until(() => !r.api.checking);
	assert.equal(r.api.records.length, 1);
	await r.render({ confirmedBatteryId: asset.id });
	await until(() => !r.api.checking && r.api.records.length === 0);
	await r.render({ confirmedBatteryId: null });
	await until(() => !r.api.checking);
	await act(async () =>
		r.api.start("battery/scenario", {
			parameters: scenario.battery_binding.parameters,
			source_note: scenario.source_note,
		}),
	);
	await until(() => r.api.records.length === 1);
	await act(async () => r.api.dismissAcknowledged(r.api.records[0]));
	await until(() => r.api.records.length === 0);
});

test("native scope withdrawal before persistence finishes prevents dispatch and preserves the exact guest intent", async (t) => {
	const gate = deferred(),
		saved = [];
	const store = {
		list: async () => saved,
		write: async (s, path, body) => {
			await gate.promise;
			saved.push({
				scope: s,
				path,
				body,
				projectId,
				key: JSON.parse(body).key,
				resultId: null,
				createdAt: 1,
			});
		},
		acknowledge: async () => {},
		clear: async () => {},
	};
	const r = await rig(t, async () => json(result), { store });
	let pending;
	await act(async () => {
		pending = r.api.start("runs/energy", { expected_revision: 2 });
	});
	await r.transition({ ...session, kind: "user", query_scope: "b".repeat(64) });
	await act(async () => {
		gate.resolve();
		await pending;
	});
	assert.equal(r.calls.length, 0);
	assert.equal(saved.length, 1);
	assert.equal(saved[0].scope, scope);
	assert.equal(r.api.busy, false);
	await act(async () => r.api.refresh());
	await until(() => !r.api.checking && r.api.records.length === 1);
	assert.equal(r.calls.length, 0);
});
