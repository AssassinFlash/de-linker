import test from "node:test";
import assert from "node:assert/strict";
import { IDBFactory } from "fake-indexeddb";
import { PlanningIntentStore } from "./PlanningIntentStore.ts";
import scenario from "../../tests/fixtures/energy-scenario.json" with { type: "json" };

const scope = "a".repeat(64),
	project = "b".repeat(32),
	asset = "c".repeat(32);
const command = (key = crypto.randomUUID(), projectId = project) =>
	JSON.stringify({
		schema_version: 1,
		project_id: projectId,
		expected_revision: 7,
		key,
	});
function fresh(t: { after: (fn: () => void) => void }) {
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	t.after(() => {
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else Reflect.deleteProperty(globalThis, "indexedDB");
	});
	return new PlanningIntentStore();
}

test("exact request survives a new store instance; duplicate writers and acknowledgement keep one immutable receipt", async (t) => {
	const store = fresh(t),
		body = command();
	await Promise.all([
		store.write(scope, "runs/energy", body),
		store.write(scope, "runs/energy", body),
	]);
	assert.equal(
		(await new PlanningIntentStore().list([scope, scope], project)).length,
		1,
	);
	await store.acknowledge(scope, "runs/energy", body, asset);
	await store.acknowledge(scope, "runs/energy", body, asset);
	await store.write(scope, "runs/energy", body);
	assert.equal((await store.list([scope], project))[0]!.resultId, asset);
	await assert.rejects(
		store.acknowledge(scope, "runs/energy", body, "d".repeat(32)),
	);
	assert.equal((await store.list([scope], project))[0]!.resultId, asset);
	await store.clear(scope, "runs/energy", body);
	await store.clear(scope, "runs/energy", body);
	assert.deepEqual(await store.list([scope], project), []);
});

test("changed bytes cannot replace, acknowledge or delete an original intent; owners/projects remain scoped", async (t) => {
	const store = fresh(t),
		body = command(),
		changed = body.replace('"expected_revision":7', '"expected_revision":8');
	const outcomes = await Promise.allSettled([
		store.write(scope, "runs/energy", body),
		store.write(scope, "runs/energy", changed),
	]);
	assert.equal(outcomes[0]!.status, "fulfilled");
	assert.equal(outcomes[1]!.status, "rejected");
	await store.clear(scope, "runs/energy", changed);
	await store.acknowledge(scope, "runs/energy", changed, asset);
	const rows = await store.list([scope], project);
	assert.equal(rows[0]!.body, body);
	assert.equal(rows[0]!.resultId, null);
	assert.deepEqual(await store.list(["f".repeat(64)], project), []);
	assert.deepEqual(await store.list([scope], "e".repeat(32)), []);
});

test("live admission is atomic across connections and operation kinds while exact recovery stays available", async (t) => {
	const first = fresh(t),
		second = new PlanningIntentStore(),
		weather = command(),
		pv = command();
	const outcomes = await Promise.allSettled([
		first.write(scope, "runs/weather", weather, [scope]),
		second.write(scope, "runs/pv", pv, [scope]),
	]);
	assert.equal(
		outcomes.filter((value) => value.status === "fulfilled").length,
		1,
	);
	const rows = await first.list([scope], project);
	assert.equal(rows.length, 1);
	const original = rows[0]!;
	await second.write(scope, original.path, original.body, [scope]);
	await first.acknowledge(scope, original.path, original.body, asset);
	const next = original.path === "runs/weather" ? "runs/pv" : "runs/weather";
	await second.write(scope, next, command(), [scope]);
	assert.equal(
		(await first.list([scope], project)).length,
		2,
		"an acknowledged record does not block a new task",
	);
});

test("live admission includes native-granted prior namespaces without reading unrelated scopes", async (t) => {
	const store = fresh(t),
		former = "f".repeat(64),
		original = command();
	await store.write(former, "runs/weather", original);
	await assert.rejects(
		store.write(scope, "runs/pv", command(), [scope, former]),
		/planning_operation_pending/,
	);
	await store.write(former, "runs/weather", original, [scope, former]);
	await store.write(scope, "runs/pv", command(), [scope]);
	assert.equal((await store.list([scope], project)).length, 1);
	assert.equal((await store.list([former], project))[0]!.body, original);
});

test("one UUID in different operation namespaces retains independent exact bodies", async (t) => {
	const store = fresh(t),
		key = crypto.randomUUID(),
		run = command(key);
	const battery = JSON.stringify({
		schema_version: 1,
		project_id: project,
		key,
		source_note: scenario.source_note,
		parameters: scenario.battery_binding.parameters,
	});
	await store.write(scope, "runs/energy", run);
	await store.write(scope, "battery/scenario", battery);
	assert.equal((await store.list([scope], project)).length, 2);
	await store.clear(scope, "battery/scenario", battery);
	assert.equal((await store.list([scope], project))[0]!.body, run);
});

test("retention limit refuses new intents without evicting originals or losing known acknowledgements", async (t) => {
	const store = fresh(t),
		bodies = Array.from({ length: 128 }, () => command());
	for (const body of bodies) await store.write(scope, "runs/energy", body);
	await assert.rejects(store.write(scope, "runs/energy", command()), /limit/);
	await store.write(scope, "runs/energy", bodies[0]!);
	await store.acknowledge(scope, "runs/energy", bodies[0]!, asset);
	assert.equal((await store.list([scope], project)).length, 128);
	await store.clear(scope, "runs/energy", bodies[0]!);
	await store.write(scope, "runs/energy", command());
	assert.equal((await store.list([scope], project)).length, 128);
});

test("corrupt stored recovery is surfaced before project filtering, rather than silently discarded", async (t) => {
	const store = fresh(t);
	await store.write(scope, "runs/energy", command());
	await new Promise<void>((resolve, reject) => {
		const opened = indexedDB.open("linker-planner-energy-intents-v1", 1);
		opened.onerror = () => reject(opened.error);
		opened.onsuccess = () => {
			const db = opened.result,
				tx = db.transaction("intents", "readwrite");
			tx.objectStore("intents").put({
				id: scope + ":broken",
				scope,
				schema_version: 1,
				path: "runs/energy",
				body: "{}",
				created_at: 1,
				result_id: null,
			});
			tx.oncomplete = () => {
				db.close();
				resolve();
			};
			tx.onabort = () => reject(tx.error);
		};
	});
	await assert.rejects(store.list([scope], "e".repeat(32)), /invalid/);
});
