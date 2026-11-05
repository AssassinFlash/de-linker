import assert from "node:assert/strict";
import { test } from "node:test";
import { clearCreationsForTitle } from "./recoveryIntents.ts";
import type { CreationIntent, DraftStore } from "./DraftStore.ts";

function storeWith(records: readonly (CreationIntent & { scope: string })[]) {
	const cleared: { scope: string; body: string }[] = [];
	const store: Pick<DraftStore, "readCreations" | "clearCreation"> = {
		async readCreations(scope: string) {
			return records
				.filter((record) => record.scope === scope)
				.map(({ scope: _scope, ...intent }) => intent);
		},
		async clearCreation(scope: string, body: string) {
			cleared.push({ scope, body });
		},
	};
	return { store, cleared };
}

test("clearing a deleted project's creation hints skips a title another project still uses", async () => {
	const first = {
		scope: "a".repeat(64),
		key: "11111111-1111-4111-8111-111111111111",
		title: "Deleted project",
		body: '{"schema_version":1,"title":"Deleted project","inputs":{},"key":"11111111-1111-4111-8111-111111111111"}',
		destination: null,
		createdAt: 1,
	};
	const kept = {
		scope: "a".repeat(64),
		key: "22222222-2222-4222-8222-222222222222",
		title: "Another project",
		body: '{"schema_version":1,"title":"Another project","inputs":{},"key":"22222222-2222-4222-8222-222222222222"}',
		destination: null,
		createdAt: 2,
	};
	const claimed = {
		scope: "b".repeat(64),
		key: "33333333-3333-4333-8333-333333333333",
		title: "Deleted project",
		body: '{"schema_version":1,"title":"Deleted project","inputs":{},"key":"33333333-3333-4333-8333-333333333333"}',
		destination: null,
		createdAt: 3,
	};
	const scopes = ["a".repeat(64), "b".repeat(64)];
	const { store, cleared } = storeWith([first, kept, claimed]);
	await clearCreationsForTitle(
		store as unknown as DraftStore,
		scopes,
		"Deleted project",
		["Another project"],
	);
	assert.deepEqual(cleared, [
		{ scope: "a".repeat(64), body: first.body },
		{ scope: "b".repeat(64), body: claimed.body },
	]);
	// A remaining project with that title owns an indistinguishable intent, so
	// the whole title is left alone rather than discarding a live unsent draft.
	await clearCreationsForTitle(
		store as unknown as DraftStore,
		scopes,
		"Deleted project",
		["Deleted project"],
	);
	assert.equal(cleared.length, 2);
});
