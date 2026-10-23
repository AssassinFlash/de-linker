import assert from "node:assert/strict";
import test from "node:test";
import type { PlannerClient } from "./PlannerClient.ts";
import type { DraftStore } from "./DraftStore.ts";
import { recoveryScopes } from "./recoveryScopes.ts";
import {
	creationIntents,
	profileIntents,
	intentId,
} from "./recoveryIntents.ts";

const scope = "f".repeat(64);
const numberScope = (n: number) => n.toString(16).padStart(64, "0");

test("native recovery discovery consumes every ordered page without inventing a scope", async () => {
	const entries = Array.from({ length: 67 }, (_, n) => numberScope(n));
	const cursors: unknown[] = [];
	const client = {
		isCurrentScope: (current: string) => current === scope,
		async query(
			path: string,
			body: { after: string | null },
			expected: string,
		) {
			assert.equal(path, "recovery/scopes");
			assert.equal(expected, scope);
			cursors.push(body.after);
			const start = body.after === null ? 0 : entries.indexOf(body.after) + 1;
			const page = entries.slice(start, start + 32);
			return {
				schema_version: 1,
				scopes: page,
				next: start + 32 < entries.length ? page.at(-1) : null,
			};
		},
	} as unknown as PlannerClient;
	assert.deepEqual(await recoveryScopes(client, scope), [scope, ...entries]);
	assert.deepEqual(cursors, [null, entries[31], entries[63]]);
});

test("malformed, unordered and nonadvancing grant pages cannot release browser data", async () => {
	for (const page of [
		{ schema_version: true, scopes: [], next: null },
		{ schema_version: 1, scopes: [numberScope(2), numberScope(1)], next: null },
		{ schema_version: 1, scopes: [numberScope(1), numberScope(1)], next: null },
		{ schema_version: 1, scopes: ["arbitrary-owner"], next: null },
		{ schema_version: 1, scopes: [], next: numberScope(1) },
		{ schema_version: 1, scopes: [], next: null, owner: "from-browser" },
	]) {
		const client = {
			isCurrentScope: () => true,
			query: async () => page,
		} as unknown as PlannerClient;
		await assert.rejects(
			recoveryScopes(client, scope),
			/invalid_recovery_scopes/,
		);
	}
});

test("a delayed grant reply after native withdrawal cannot be used", async () => {
	let admitted = true;
	const client = {
		isCurrentScope: () => admitted,
		async query() {
			admitted = false;
			return { schema_version: 1, scopes: [numberScope(1)], next: null };
		},
	} as unknown as PlannerClient;
	await assert.rejects(
		recoveryScopes(client, scope),
		/invalid_recovery_scopes/,
	);
});

test("discovered immutable intents retain exact original namespaces and bodies", async () => {
	const previous = numberScope(1),
		reads: string[] = [];
	const body = '{"literal":"exact bytes\\n"}';
	const store = {
		async readCreations(source: string) {
			reads.push(source);
			return [{ body, key: "same-key", title: "Synthetic", createdAt: 1 }];
		},
	} as unknown as DraftStore;
	const records = await creationIntents(store, [scope, previous, previous]);
	assert.deepEqual(reads, [scope, previous]);
	assert.deepEqual(
		new Set(records.map((r) => r.scope)),
		new Set([scope, previous]),
	);
	assert.ok(records.every((r) => r.body === body));
	assert.equal(new Set(records.map(intentId)).size, 2);
});

test("import discovery stays on the currently authorised project in every approved namespace", async () => {
	const projectId = "1".repeat(32),
		calls: unknown[] = [];
	const store = {
		async readProfileImports(source: string, project: string) {
			calls.push([source, project]);
			return [
				{
					body: "exact synthetic source",
					key: "key",
					projectId: project,
					label: "Synthetic",
					createdAt: 0,
				},
			];
		},
	} as unknown as DraftStore;
	const records = await profileIntents(
		store,
		[scope, numberScope(1)],
		projectId,
	);
	assert.deepEqual(calls, [
		[scope, projectId],
		[numberScope(1), projectId],
	]);
	assert.ok(records.every((r) => r.projectId === projectId));
});

test("aggregate recovery ceilings report inability to read rather than truncate or evict", async () => {
	const store = {
		async readCreations() {
			return Array.from({ length: 129 }, (_, n) => ({
				body: "x",
				key: String(n),
				title: "Synthetic",
				createdAt: 0,
			}));
		},
		async readProfileImports() {
			return [
				{
					body: "x".repeat(32 * 1024 * 1024 + 1),
					key: "key",
					projectId: "1".repeat(32),
					label: "Synthetic",
					createdAt: 0,
				},
			];
		},
		clearCreation() {
			assert.fail("must preserve every original record");
		},
		clearProfileImport() {
			assert.fail("must preserve every original record");
		},
	} as unknown as DraftStore;
	await assert.rejects(
		creationIntents(store, [scope]),
		/recovery_storage_limit/,
	);
	await assert.rejects(
		profileIntents(store, [scope], "1".repeat(32)),
		/recovery_storage_limit/,
	);
});
