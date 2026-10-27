import assert from "node:assert/strict";
import { test } from "node:test";
import { releaseUnownedRenderer } from "./renderLifetime.ts";

test("unowned failed renderer releases both partial backends and preserves cleanup isolation", async () => {
	const calls: string[] = [];
	const initial = {
			async dispose() {
				calls.push("initial");
				throw new Error("cleanup failure");
			},
		},
		backend = {
			async dispose() {
				calls.push("fallback");
			},
		};
	await releaseUnownedRenderer(
		{
			initialized: false,
			backend,
			async dispose() {
				calls.push("renderer");
			},
		},
		initial,
	);
	assert.deepEqual(calls.sort(), ["fallback", "initial", "renderer"]);
});
test("initialised renderer owns current backend disposal and previous fallback remains separate", async () => {
	const calls: string[] = [];
	const backend = {
		async dispose() {
			calls.push("current");
		},
	};
	await releaseUnownedRenderer(
		{
			initialized: true,
			backend,
			async dispose() {
				calls.push("renderer");
				await backend.dispose();
			},
		},
		{
			async dispose() {
				calls.push("initial");
			},
		},
	);
	assert.deepEqual(calls, ["initial", "renderer", "current"]);
});
