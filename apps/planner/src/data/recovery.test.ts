import assert from "node:assert/strict";
import test from "node:test";
import { decodeDraft, DraftStore } from "./DraftStore.ts";
import { beginDraft, editDraft, prepareSave } from "../domain/draft.ts";
import type { Project } from "./protocol.ts";
import { IDBFactory } from "fake-indexeddb";

const project: Project = {
	id: "1".repeat(32),
	title: "Synthetic recovery",
	revision: 3,
	input_sha256: "2".repeat(64),
	inputs: { value: 10 },
};
const scope = "3".repeat(64);
const draft = prepareSave(
	editDraft(beginDraft(project), { value: 20 }),
	"00168d99-5d17-426d-9c71-16ea80aa1b56",
	{ maxDepth: 32, maxBytes: 100000 },
);
const record = {
	schema_version: 1,
	key: scope + ":" + project.id,
	scope,
	project_id: project.id,
	draft,
	updated_at: 1,
};

test("recovery retains the baseline, local edits and exact uncertain intent", async () => {
	const restored = decodeDraft(structuredClone(record), scope, project.id);
	assert.deepEqual(restored, draft);
	assert.equal(restored.pending?.body, draft.pending?.body);
	assert.equal(restored.history.current.value, 20);
	assert.equal(restored.baseline.inputs.value, 10);
	assert.throws(() => decodeDraft(record, "4".repeat(64), project.id));
	assert.throws(() => decodeDraft(record, scope, "5".repeat(32)));
	const legacy = structuredClone(record);
	const oldCommand = JSON.parse(legacy.draft.pending!.body);
	delete oldCommand.input_contract;
	legacy.draft = {
		...legacy.draft,
		pending: { ...legacy.draft.pending!, body: JSON.stringify(oldCommand) },
	};
	assert.equal(
		decodeDraft(legacy, scope, project.id).pending?.body,
		legacy.draft.pending!.body,
	);
	const pvOnly = structuredClone(legacy);
	pvOnly.draft = {
		...pvOnly.draft,
		pending: {
			...pvOnly.draft.pending!,
			body: JSON.stringify({
				...oldCommand,
				input_contract: "installation_pv_string_links_v1",
			}),
		},
	};
	assert.equal(
		decodeDraft(pvOnly, scope, project.id).pending?.body,
		pvOnly.draft.pending!.body,
	);
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	try {
		const store = new DraftStore();
		await store.write(scope, draft);
		assert.equal(
			(await new DraftStore().read(scope, project.id))?.pending?.body,
			draft.pending!.body,
		);
		await store.write(scope, { ...draft, pending: null });
		const afterRefusal = await new DraftStore().read(scope, project.id);
		assert.equal(afterRefusal?.pending, null);
		assert.deepEqual(afterRefusal?.history.current, draft.history.current);
		assert.deepEqual(afterRefusal?.baseline, draft.baseline);
		const create = {
			schema_version: 1,
			title: "Recovered creation",
			inputs: {},
			key: crypto.randomUUID(),
		};
		const legacyBody = JSON.stringify(create);
		await store.writeCreation(scope, legacyBody);
		const awareBody = JSON.stringify({
			...create,
			key: crypto.randomUUID(),
			input_contract: "installation_pv_string_links_v1",
		});
		await store.writeCreation(scope, awareBody, "equipment");
		const cumulativeBody = JSON.stringify({
			...create,
			key: crypto.randomUUID(),
			input_contract: "pv_string_links_direct_beam_visibility_v1",
		});
		await store.writeCreation(scope, cumulativeBody);
		const geometricBody = JSON.stringify({
			...create,
			key: crypto.randomUUID(),
			input_contract: "pv_string_links_direct_beam_geometric_pv_v1",
		});
		await store.writeCreation(scope, geometricBody);
		const restoredCreations = await new DraftStore().readCreations(scope);
		assert.deepEqual(
			new Set(restoredCreations.map((value) => value.body)),
			new Set([legacyBody, awareBody, cumulativeBody, geometricBody]),
		);
		assert.equal(
			restoredCreations.find((value) => value.body === awareBody)?.destination,
			"equipment",
		);
		assert.equal(
			restoredCreations.find((value) => value.body === legacyBody)?.destination,
			null,
		);
		await assert.rejects(
			store.writeCreation(
				scope,
				JSON.stringify({ ...create, input_contract: null }),
			),
			/invalid_creation_recovery/,
		);
	} finally {
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else Reflect.deleteProperty(globalThis, "indexedDB");
	}
});

test("tampered recovery cannot substitute a pending snapshot, project or acknowledgement", () => {
	const snapshot = structuredClone(record);
	assert.ok(snapshot.draft.pending);
	const value = {
		...snapshot,
		draft: {
			...snapshot.draft,
			pending: { ...snapshot.draft.pending, inputs: { value: 999 } },
		},
	};
	assert.throws(
		() => decodeDraft(value, scope, project.id),
		/invalid_recovery_intent/,
	);
	assert.throws(
		() =>
			decodeDraft(
				{
					...record,
					draft: { ...draft, conflict: { ...project, id: "6".repeat(32) } },
				},
				scope,
				project.id,
			),
		/invalid_recovery_conflict/,
	);
});

test("invalid recovered creation is rejected before IndexedDB or a network call", async () => {
	const store = new DraftStore();
	for (const command of [
		{ schema_version: 1, title: "", inputs: {}, key: crypto.randomUUID() },
		{ schema_version: 1, title: "x", inputs: {}, key: "not-a-durable-key" },
		{
			schema_version: 1,
			title: "x",
			inputs: {},
			key: crypto.randomUUID(),
			actor: "invented",
		},
	])
		await assert.rejects(
			store.writeCreation(scope, JSON.stringify(command)),
			/invalid_creation_recovery/,
		);
});
