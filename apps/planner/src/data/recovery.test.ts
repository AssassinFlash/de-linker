import assert from "node:assert/strict";
import test from "node:test";
import { decodeDraft, DraftStore } from "./DraftStore.ts";
import { beginDraft, editDraft, prepareSave } from "../domain/draft.ts";
import type { Project } from "./protocol.ts";

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

test("recovery retains the baseline, local edits and exact uncertain intent", () => {
	const restored = decodeDraft(structuredClone(record), scope, project.id);
	assert.deepEqual(restored, draft);
	assert.equal(restored.pending?.body, draft.pending?.body);
	assert.equal(restored.history.current.value, 20);
	assert.equal(restored.baseline.inputs.value, 10);
	assert.throws(() => decodeDraft(record, "4".repeat(64), project.id));
	assert.throws(() => decodeDraft(record, scope, "5".repeat(32)));
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
