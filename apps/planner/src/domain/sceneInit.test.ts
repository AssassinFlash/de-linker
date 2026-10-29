import assert from "node:assert/strict";
import { test } from "node:test";
import { SceneInitTimeout, withInitDeadline } from "./sceneInit.ts";

type Renderer = { id: string };

test("initialisation inside the deadline resolves with the renderer", async () => {
	const renderer: Renderer = { id: "renderer" };
	const late: Renderer[] = [];
	const value = await withInitDeadline(
		Promise.resolve(renderer),
		1_000,
		(result) => late.push(result),
	);
	assert.equal(value, renderer);
	assert.deepEqual(late, []);
});

test("a rejected initialisation keeps its own error and is not reported as a timeout", async () => {
	const failure = new TypeError("Cannot read properties of null");
	await assert.rejects(
		withInitDeadline(Promise.reject(failure), 1_000, () => {
			assert.fail("late cleanup");
		}),
		(error) => error === failure,
	);
});

test("a startup that never settles rejects as a timeout", async () => {
	await assert.rejects(
		withInitDeadline(new Promise<Renderer>(() => {}), 5, () => {
			assert.fail("no value");
		}),
		(error) =>
			error instanceof SceneInitTimeout &&
			error.message === "scene_init_timeout",
	);
});

test("a renderer that arrives after the deadline is handed to cleanup", async () => {
	let settle: (value: Renderer) => void = () => {};
	const pending = new Promise<Renderer>((resolve) => {
		settle = resolve;
	});
	const late: Renderer[] = [];
	await assert.rejects(
		withInitDeadline(pending, 5, (value) => late.push(value)),
		SceneInitTimeout,
	);
	const renderer: Renderer = { id: "late" };
	settle(renderer);
	await new Promise((resolve) => setTimeout(resolve, 0));
	assert.deepEqual(late, [renderer]);
});

test("late cleanup failures cannot replace the reported timeout", async () => {
	let settle: (value: Renderer | null) => void = () => {};
	const pending = new Promise<Renderer | null>((resolve) => {
		settle = resolve;
	});
	await assert.rejects(
		withInitDeadline(pending, 5, () => {
			throw new Error("cleanup_failed");
		}),
		SceneInitTimeout,
	);
	settle(null);
	await new Promise((resolve) => setTimeout(resolve, 0));
});
