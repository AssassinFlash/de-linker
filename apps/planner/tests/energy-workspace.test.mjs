import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import {
	beginDraft,
	editDraft,
	undoDraft,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import { ApiError } from "../src/data/protocol.ts";
import scenario from "./fixtures/energy-scenario.json" with { type: "json" };
import selections from "./fixtures/energy-selections.json" with { type: "json" };
import actualRun from "./fixtures/energy-run.json" with { type: "json" };

const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) =>
			(node.getAttribute("aria-label") ?? node.textContent) === text &&
			!node.closest("[hidden]"),
	);
const control = (text) =>
	[...document.querySelectorAll("label")]
		.find((label) => label.querySelector("span")?.textContent.startsWith(text))
		?.querySelector("input,textarea,select");
const click = async (text) => {
	const node = button(text);
	assert.ok(node, "missing control " + text);
	assert.equal(node.disabled, false, "disabled " + text);
	await act(async () => node.click());
};

test("actual scenario controls retain raw input, require confirmed save, use one frozen revision, and preserve edits from a late preparation response", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	window.history.replaceState(
		null,
		"",
		`?project=${actualRun.project_id}#lp-calculations`,
	);
	const scope = "a".repeat(64),
		project = {
			id: actualRun.project_id,
			title: "Synthetic component workflow",
			revision: 1,
			input_sha256: "b".repeat(64),
			inputs: {
				profile_selections: selections,
				energy_scenario: { ...scenario, battery_binding: null },
			},
		};
	const session = {
		query_scope: scope,
		runtime: {
			limits: {
				max_json_depth: 32,
				max_body_bytes: 16777216,
				max_page_size: 100,
			},
		},
	};
	const requests = [],
		queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
	let setter,
		current = beginDraft(project),
		gate = null,
		serverRun = null;
	const assetFor = (body, index) => ({
		id: String(index).repeat(32),
		project_id: project.id,
		content_sha256: "c".repeat(64),
		metadata_sha256: "d".repeat(64),
		media_type: "application/json",
		purpose: "battery_parameters_v1",
		metadata: {
			retention: "permanent",
			provenance: {
				basis: "user_explicit_scenario_not_equipment_release",
				label: body.source_note,
			},
		},
	});
	const client = {
		isCurrentScope: (value) => value === scope,
		async send(path, serialized) {
			const body = JSON.parse(serialized);
			requests.push({ path, body, serialized });
			if (path === "battery/scenario") {
				if (gate) await gate.promise;
				return assetFor(body, requests.filter((x) => x.path === path).length);
			}
			if (path === "runs/energy") {
				// Component transport fixture, not a simulated numerical engine.
				serverRun = {
					...actualRun,
					state: "queued",
					result: null,
					result_sha256: null,
					error: null,
					revision: body.expected_revision,
					manifest: { ...actualRun.manifest, revision: body.expected_revision },
				};
				return serverRun;
			}
			throw new Error("Unexpected mutation " + path);
		},
		async query(path) {
			if (path === "projects/runs")
				return {
					items: serverRun
						? [
								{
									id: serverRun.id,
									project_id: project.id,
									revision: serverRun.revision,
									manifest_sha256: serverRun.manifest_sha256,
									result_sha256: serverRun.result_sha256,
									state: serverRun.state,
									is_current: true,
									created_at: 1700000000,
								},
							]
						: [],
					next: null,
				};
			if (path === "runs/read") return serverRun;
			if (path === "runs/cancel") {
				serverRun = { ...serverRun, state: "cancelled" };
				return serverRun;
			}
			throw new ApiError(404, "not_found");
		},
	};
	function edit(operation) {
		try {
			current = editDraft(current, operation(current.history.current));
			setter(current);
			return true;
		} catch {
			return false;
		}
	}
	function Harness() {
		const [draft, setDraft] = useState(current);
		setter = setDraft;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(
				"button",
				{
					onClick: () => {
						current = prepareSave(current, crypto.randomUUID(), {
							maxDepth: 32,
							maxBytes: 16777216,
						});
						const intent = current.pending;
						current = acknowledgeSave(current, intent, {
							...project,
							revision: intent.expectedRevision + 1,
							input_sha256: "e".repeat(64),
							inputs: intent.inputs,
						});
						setter(current);
					},
				},
				"Confirm project save fixture",
			),
			React.createElement(EnergyWorkspace, {
				draft,
				edit,
				flush: async () => true,
				session,
				client,
				recheck: () => {},
				locale: "en-US",
				blocked: false,
				active: true,
				onValidity: () => {},
				openProfiles: () => {},
			}),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(Harness),
			),
		),
	);
	await until(
		() =>
			button("Prepare scenario settings") &&
			!button("Prepare scenario settings").disabled,
	);
	const sourceNote = control("Source or assumption for storage parameters");
	await enter(sourceNote, "");
	await click("Prepare scenario settings");
	assert.match(
		document.activeElement.textContent,
		/storage parameters need a source/,
	);
	assert.equal(
		requests.length,
		0,
		"an incomplete scenario creates no parameter asset",
	);
	await enter(sourceNote, scenario.source_note);
	const charge = control("AC charging power");
	await enter(charge, "unfinished");
	assert.equal(charge.getAttribute("aria-invalid"), "true");
	assert.equal(button("03Operation").disabled, true);
	await act(async () =>
		charge.dispatchEvent(
			new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
		),
	);
	await enter(charge, "7");
	await click("02Starting state");
	await click("01Storage");
	assert.equal(
		control("AC charging power"),
		charge,
		"hidden sections retain the same real input node",
	);
	assert.equal(charge.value, "7");
	await click("Prepare scenario settings");
	await until(() => current.history.current.energy_replay !== undefined);
	assert.equal(requests.length, 1);
	assert.equal(requests[0].body.parameters.charge_ac_kw, 7);
	assert.equal(
		button("Calculate saved scenario").disabled,
		true,
		"prepared unsaved inputs cannot start a job",
	);
	await click("Confirm project save fixture");
	await until(() => !button("Calculate saved scenario").disabled);
	await act(async () => {
		button("Calculate saved scenario").click();
		button("Calculate saved scenario")?.click();
	});
	await until(
		() => document.querySelector(".lp-run-result h3")?.textContent === "Queued",
	);
	assert.equal(requests.filter((x) => x.path === "runs/energy").length, 1);
	assert.equal(requests.at(-1).body.expected_revision, 2);
	assert.equal(new URL(location.href).searchParams.get("run"), actualRun.id);
	await click("Cancel calculation");
	await until(
		() =>
			document.querySelector(".lp-run-result h3")?.textContent ===
			"Calculation cancelled",
	);
	await click("Scenario settings");
	assert.equal(new URL(location.href).searchParams.get("run"), null);
	await enter(control("AC charging power"), "8");
	gate = deferred();
	await click("Prepare scenario settings");
	await until(
		() => requests.filter((x) => x.path === "battery/scenario").length === 2,
	);
	await act(async () => {
		current = undoDraft(current);
		setter(current);
	});
	const restored = structuredClone(current.history.current);
	await act(async () => gate.resolve());
	await until(() =>
		document
			.querySelector(".lp-notice")
			?.textContent.includes("inputs changed before preparation finished"),
	);
	assert.deepEqual(
		current.history.current,
		restored,
		"late asset response cannot overwrite the restored scenario",
	);
	assert.equal(current.history.current.energy_scenario.battery.charge_ac_kw, 7);
});
