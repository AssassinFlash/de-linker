import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, deferred } from "./dom-fixture.mjs";
import { usePlanningRuns } from "../src/data/usePlanningRuns.ts";
import actualRun from "./fixtures/energy-run.json" with { type: "json" };

test("opening history after its first page loads pins the verified visible run in native links, only with current admission", async (t) => {
	const dom = setupDom(),
		gate = deferred(),
		scope = "a".repeat(64),
		calls = [];
	window.history.replaceState(
		null,
		"",
		`?project=${actualRun.project_id}#lp-calculations`,
	);
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	let admitted = true,
		update,
		current;
	const client = {
		isCurrentScope: (value) => admitted && value === scope,
		async query(path) {
			calls.push(path);
			// Read-only transport fixture over the recorded real managed result.
			if (path === "projects/runs")
				return {
					items: [
						{
							...Object.fromEntries(
								[
									"id",
									"project_id",
									"revision",
									"manifest_sha256",
									"result_sha256",
									"state",
									"is_current",
								].map((key) => [key, actualRun[key]]),
							),
							// Read from this exact immutable run in the owned p548 database.
							created_at: 1792798248.004341,
						},
					],
					next: null,
				};
			if (path === "runs/read") {
				await gate.promise;
				return actualRun;
			}
			throw new Error("Unexpected request " + path);
		},
	};
	function Harness() {
		const [active, setActive] = useState(false),
			[version, setVersion] = useState(0);
		update = (next) => {
			setActive(next);
			setVersion((value) => value + 1);
		};
		current = usePlanningRuns({
			projectId: actualRun.project_id,
			session: {
				query_scope: scope,
				runtime: { limits: { max_page_size: 100 } },
			},
			client,
			recheck: () => {},
			active,
		});
		return React.createElement(
			"p",
			null,
			current.run.data?.id ?? "No calculation read",
			version,
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Harness),
			),
		),
	);
	assert.deepEqual(calls, []);
	await act(async () => update(true));
	await until(() => calls.includes("runs/read"));
	assert.equal(
		new URL(location.href).searchParams.get("run"),
		null,
		"a list row alone does not stand in for the checked run",
	);
	admitted = false;
	await act(async () => {
		update(true);
		gate.resolve();
	});
	await until(() => current.run.data?.id === actualRun.id);
	assert.equal(
		new URL(location.href).searchParams.get("run"),
		null,
		"late reads cannot change native navigation after admission is withdrawn",
	);
	admitted = true;
	await act(async () => update(true));
	await until(
		() => new URL(location.href).searchParams.get("run") === actualRun.id,
	);
	assert.equal(location.hash, "#lp-calculations");
	assert.equal(current.runId, actualRun.id);
	assert.deepEqual(calls.slice(0, 2), ["projects/runs", "runs/read"]);
});
