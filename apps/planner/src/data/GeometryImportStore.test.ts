import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { IDBFactory } from "fake-indexeddb";
import { GeometryImportStore } from "./GeometryImportStore.ts";

const source = readFileSync(
	new URL(
		"../../../../fixtures/planning/source-roof-wgs84.geojson",
		import.meta.url,
	),
);
const options = JSON.parse(
	readFileSync(
		new URL(
			"../../../../fixtures/planning/geometry-import-options.json",
			import.meta.url,
		),
		"utf8",
	),
);
const scope = "a".repeat(64),
	projectId = "b".repeat(32);
const command = (key = crypto.randomUUID()) =>
	JSON.stringify({
		schema_version: 1,
		project_id: projectId,
		content_base64: source.toString("base64"),
		options,
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
	return new GeometryImportStore();
}

test("committed original survives a new store instance; writes and acknowledgement are idempotent", async (t) => {
	const store = fresh(t),
		body = command(),
		asset = "c".repeat(32);
	await Promise.all([store.write(scope, body), store.write(scope, body)]);
	let records = await new GeometryImportStore().list([scope, scope], projectId);
	assert.equal(records.length, 1);
	assert.equal(records[0]!.body, body);
	await store.acknowledge(scope, body, asset);
	await store.acknowledge(scope, body, asset);
	await store.write(scope, body);
	records = await store.list([scope], projectId);
	assert.equal(records[0]!.assetId, asset);
	await assert.rejects(
		store.acknowledge(scope, body, "d".repeat(32)),
		/conflict/,
	);
	await store.clear(scope, body);
	await store.clear(scope, body);
	assert.deepEqual(await store.list([scope], projectId), []);
});

test("concurrent changed bytes under one key cannot overwrite or clear the committed original", async (t) => {
	const store = fresh(t),
		body = command(),
		changed = body.replace(options.source.label, "Changed source");
	const results = await Promise.allSettled([
		store.write(scope, body),
		store.write(scope, changed),
	]);
	assert.equal(results[0]!.status, "fulfilled");
	assert.equal(results[1]!.status, "rejected");
	await assert.rejects(store.clear(scope, changed), /conflict/);
	assert.equal((await store.list([scope], projectId))[0]!.body, body);
	assert.deepEqual(await store.list(["e".repeat(64)], projectId), []);
	assert.deepEqual(await store.list([scope], "f".repeat(32)), []);
});

test("scope retention is bounded and a quota refusal does not erase an earlier upload", async (t) => {
	const store = fresh(t),
		bodies = Array.from({ length: 32 }, () => command());
	for (const body of bodies) await store.write(scope, body);
	await assert.rejects(store.write(scope, command()), /limit/);
	await store.write(scope, bodies[0]!);
	assert.equal((await store.list([scope], projectId)).length, 32);
	await store.clear(scope, bodies[0]!);
	await store.write(scope, command());
	assert.equal((await store.list([scope], projectId)).length, 32);
});
