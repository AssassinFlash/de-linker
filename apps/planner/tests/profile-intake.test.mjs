import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { DraftStore } from "../src/data/DraftStore.ts";
import { setupDom, until, deferred, enter } from "./dom-fixture.mjs";

const projectId = "1".repeat(32),
	assetId = "2".repeat(32),
	scope = "3".repeat(64);
const source = "time;power\n2024-01-01T00:00Z;-4\n2024-01-01T00:30Z;8\n";
const mapping = {
	timestamp_column: "time",
	value_column: "power",
	measurement: "net_import",
	value_kind: "interval_average_kw",
	timestamp_role: "start",
	timezone: "Europe/Oslo",
	origin: "synthetic",
	interval_seconds: 900,
	delimiter: ";",
	decimal: ".",
	end_timestamp_column: null,
	fold_column: null,
	end_fold_column: null,
	offset_rule: "explicit_offset_precedes_naive_timezone",
	within_interval_assumption: "constant_mean_no_new_observations",
};
const command = (label = "Synthetic interval fixture") =>
	JSON.stringify({
		schema_version: 1,
		project_id: projectId,
		content_base64: btoa(source),
		mapping,
		source_label: label,
		rights_note: "Created by this test",
		key: crypto.randomUUID(),
	});
const session = {
	schema_version: 1,
	kind: "guest",
	cookie_confirmed: true,
	expires_at: 2000000000,
	query_scope: scope,
	nonce: "abcdefghij",
	claim_pending: false,
	runtime: {
		schema_version: 1,
		runtime_sha256: "4".repeat(64),
		models: {},
		limits: {
			max_body_bytes: 1000000,
			max_csv_bytes: 100000,
			max_page_size: 20,
			max_json_depth: 32,
		},
	},
};
const asset = {
	id: assetId,
	project_id: projectId,
	content_sha256: "5".repeat(64),
	metadata_sha256: "6".repeat(64),
	media_type: "text/csv; charset=utf-8",
	purpose: "csv_profile_v1",
	metadata: { csv_mapping: mapping },
};
const preview = {
	schema_version: 1,
	project_id: projectId,
	asset_id: assetId,
	content_sha256: asset.content_sha256,
	metadata_sha256: asset.metadata_sha256,
	evaluation_scope: "profile_interpretation",
	measurement: "net_import",
	source: { origin: "synthetic" },
	transformations: [],
	summary: {
		start_utc: "2024-01-01T00:00:00+00:00",
		end_utc: "2024-01-01T00:45:00+00:00",
		interval_count: 2,
		covered_seconds: 1800,
		span_seconds: 2700,
		gap_seconds: 900,
		gap_count: 1,
		energy_kwh: 1,
		min_interval_mean_kw: -4,
		max_interval_mean_kw: 8,
		native_max_interval_seconds: 900,
		effective_max_interval_seconds: 900,
		reconstructed_means: false,
	},
	rows: [
		{
			interval_index: 0,
			start_utc: "2024-01-01T00:00:00+00:00",
			end_utc: "2024-01-01T00:15:00+00:00",
			interval_mean_kw: -4,
		},
		{
			interval_index: 1,
			start_utc: "2024-01-01T00:30:00+00:00",
			end_utc: "2024-01-01T00:45:00+00:00",
			interval_mean_kw: 8,
		},
	],
	first_gaps: [
		{
			start_utc: "2024-01-01T00:15:00+00:00",
			end_utc: "2024-01-01T00:30:00+00:00",
		},
	],
	gaps_truncated: false,
	next_offset: null,
	offset: 0,
};
const json = (value, status = 200) =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "Content-Type": "application/json" },
	});
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => (node.getAttribute("aria-label") ?? node.textContent) === text,
	);
const field = (text) =>
	[...document.querySelectorAll("label")]
		.find(
			(node) =>
				node.querySelector("span")?.textContent.replace(/\s+/g, "") ===
				text.replace(/\s+/g, ""),
		)
		?.querySelector("select,input,textarea");
async function choose(text, value) {
	await act(async () => {
		const node = field(text);
		assert.ok(node, text);
		node.value = value;
		node.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}

async function rig(
	t,
	{
		bodies = [],
		lost = false,
		writeGate = null,
		hydrationGate = null,
		auth = false,
		refuse = false,
		refuseCode = "invalid_input",
		reply = undefined,
		replyStatus = 200,
		realRecovery = false,
		storageDown = false,
		cleanupGate = null,
		editor = false,
		focusGate = null,
		recoveryOrigin = scope,
	} = {},
) {
	const dom = setupDom();
	let durableStore;
	if (realRecovery) {
		const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
		Object.defineProperty(globalThis, "indexedDB", {
			value: new IDBFactory(),
			configurable: true,
		});
		t.after(() => {
			if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
			else delete globalThis.indexedDB;
		});
		durableStore = new DraftStore();
		for (const body of bodies)
			await durableStore.writeProfileImport(recoveryOrigin, body);
	}
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { ProfileIntake } = await import("../src/components/ProfileIntake.tsx");
	const { ProjectEditor } = await import("../src/components/ProjectEditor.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	let owner = session,
		writeStarted = false,
		attachConfirmed = false,
		cleanupStarted = false,
		delayedRevealScheduled = false,
		durableDraft = null,
		closes = 0,
		guard = () => true;
	let project = {
		id: projectId,
		title: "Synthetic project",
		revision: 1,
		input_sha256: "9".repeat(64),
		inputs: { brief: emptyBrief() },
	};
	const opening = project;
	const recoveryScopes = [...new Set([scope, recoveryOrigin])];
	const refusedBodies = new Set();
	const pending = new Map(bodies.map((body) => [JSON.parse(body).key, body])),
		uploads = [],
		calls = [],
		attachments = [];
	const store = {
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async write(verified, draft) {
			assert.equal(verified, scope);
			if (storageDown) throw new Error("synthetic storage outage");
			durableDraft = draft;
		},
		async readProfileImports(verified, id) {
			if (hydrationGate) await hydrationGate.promise;
			const records = [...pending.values()]
				.filter(
					(body) =>
						verified === recoveryOrigin && JSON.parse(body).project_id === id,
				)
				.map((body) => ({
					body,
					key: JSON.parse(body).key,
					projectId: id,
					label: JSON.parse(body).source_label,
					createdAt: 0,
				}));
			if (focusGate && cleanupStarted && !delayedRevealScheduled) {
				delayedRevealScheduled = true;
				// Native focus can invalidate admission after the awaited read's
				// continuation but before React commits its completion feedback.
				return {
					then(resolve) {
						resolve(records);
						queueMicrotask(() =>
							window.dispatchEvent(new window.Event("focus")),
						);
					},
				};
			}
			return records;
		},
		async writeProfileImport(verified, body) {
			assert.equal(verified, recoveryOrigin);
			writeStarted = true;
			if (writeGate) await writeGate.promise;
			if (storageDown) throw new Error("synthetic storage outage");
			pending.set(JSON.parse(body).key, body);
		},
		async clearProfileImport(verified, body) {
			cleanupStarted = true;
			if (cleanupGate) await cleanupGate.promise;
			if (storageDown) throw new Error("synthetic storage outage");
			assert.equal(verified, recoveryOrigin);
			assert.ok(
				attachConfirmed ||
					durableDraft?.history.current.profile_selections?.selected
						.net_import === assetId ||
					auth ||
					refusedBodies.has(body),
				"selection recovery must be durable before cleanup",
			);
			if (pending.get(JSON.parse(body).key) === body)
				pending.delete(JSON.parse(body).key);
		},
	};
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url, init) => {
			const path = new URL(url).pathname;
			calls.push(path);
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) {
				if (focusGate && cleanupStarted) await focusGate.promise;
				return json(owner);
			}
			if (path.endsWith("/profiles/inspect"))
				return json({
					schema_version: 1,
					evaluation_scope: "csv_structure_only",
					content_sha256: asset.content_sha256,
					delimiter: ";",
					columns: ["time", "power"],
					record_count: 2,
					rows: [{ line: 2, cells: ["2024-01-01T00:00Z", "-4"] }],
					rows_truncated: true,
				});
			if (path.endsWith("/profiles/csv")) {
				uploads.push(init.body);
				if (durableStore)
					assert.equal(
						(
							await durableStore.readProfileImports(recoveryOrigin, projectId)
						)[0].body,
						init.body,
					);
				if (reply !== undefined) return json(reply, replyStatus);
				if (refuse) {
					refusedBodies.add(init.body);
					return json(
						{
							error: {
								code: refuseCode,
								profile_issue: { issue: "value_sign", line: 2, field: "value" },
							},
						},
						422,
					);
				}
				if (auth) return json({ error: { code: "expired" } }, 401);
				if (lost) {
					lost = false;
					throw new TypeError("synthetic lost acknowledgement");
				}
				return json(asset);
			}
			if (path.endsWith("/assets/read")) return json(asset);
			if (path.endsWith("/profiles/preview")) return json(preview);
			if (path.endsWith("/projects/revise")) {
				const command = JSON.parse(init.body);
				project = {
					...project,
					revision: command.expected_revision + 1,
					inputs: command.inputs,
				};
				return json(project);
			}
			assert.fail("unexpected path " + path);
		},
	});
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(
					SessionBoundary,
					{ client },
					(confirmed, recheck) =>
						editor
							? React.createElement(ProjectEditor, {
									key: confirmed.query_scope,
									project: opening,
									session: confirmed,
									client,
									store: durableStore ?? store,
									config: { locale: "en-GB", countries: { NO: "Norway" } },
									recheck,
									close() {
										closes++;
										return true;
									},
								})
							: React.createElement(ProfileIntake, {
									key: confirmed.query_scope,
									projectId,
									recoveryScopes,
									session: confirmed,
									client,
									store: durableStore ?? store,
									locale: "en-GB",
									timezone: "Europe/Oslo",
									recheck,
									registerGuard(value) {
										guard = value;
									},
									async attach(id, role) {
										attachments.push([id, role]);
										attachConfirmed = true;
										return true;
									},
								}),
				),
			),
		),
	);
	return {
		client,
		uploads,
		pending,
		readImports: () =>
			durableStore?.readProfileImports(recoveryOrigin, projectId),
		calls,
		attachments,
		get writeStarted() {
			return writeStarted;
		},
		get cleanupStarted() {
			return cleanupStarted;
		},
		get closes() {
			return closes;
		},
		get project() {
			return project;
		},
		setRefuse(value) {
			refuse = value;
		},
		guard: () => guard(),
		changeOwner(value) {
			owner = value;
		},
		root,
		dom,
	};
}

for (const status of [200, 422, 500])
	for (const response of [[], null, {}])
		test(`HTTP ${status} ${JSON.stringify(response)} keeps CSV original and retry key`, async (t) => {
			const body = command(),
				fixture = await rig(t, {
					bodies: [body],
					reply: response,
					replyStatus: status,
					realRecovery: true,
				});
			await until(() => button("Check or retry this import"));
			await act(async () => button("Check or retry this import").click());
			await until(() =>
				document.body.textContent.includes("could not be confirmed"),
			);
			assert.deepEqual([...fixture.pending.values()], [body]);
			assert.deepEqual(
				(await fixture.readImports()).map((record) => record.body),
				[body],
			);
			await act(async () => button("Check or retry this import").click());
			await until(() => fixture.uploads.length === 2);
			await until(
				() =>
					!button("Check or retry this import").disabled &&
					document.body.textContent.includes("could not be confirmed"),
			);
			assert.deepEqual(fixture.uploads, [body, body]);
			assert.deepEqual(
				(await fixture.readImports()).map((record) => record.body),
				[body],
			);
			assert.deepEqual([...fixture.pending.values()], [body]);
			assert.equal(fixture.attachments.length, 0);
		});

test("unknown imports are explicitly selected and retried with frozen bytes before durable selection clears recovery", async (t) => {
	const a = command("Synthetic A"),
		b = command("Synthetic B");
	const fixture = await rig(t, { bodies: [a, b], lost: true });
	await until(() => button("Check or retry this import"));
	assert.deepEqual(fixture.uploads, []);
	await choose("Imports to review", scope + ":" + JSON.parse(b).key);
	await act(async () => button("Check or retry this import").click());
	await until(() =>
		document.body.textContent.includes("could not be confirmed"),
	);
	assert.deepEqual(fixture.uploads, [b]);
	assert.equal(fixture.pending.size, 2);
	await act(async () => button("Check or retry this import").click());
	await until(() => button("Use this profile in the open draft"));
	assert.deepEqual(fixture.uploads, [b, b]);
	assert.ok(
		document.body.textContent.includes(
			"Missing intervals have not been filled",
		),
	);
	assert.ok(
		document.body.textContent.includes(
			"Total site consumption cannot be derived",
		),
	);
	assert.equal(fixture.attachments.length, 0);
	await act(async () => button("Use this profile in the open draft").click());
	await until(() => fixture.pending.size === 1);
	assert.deepEqual(fixture.attachments, [[assetId, "net_import"]]);
	assert.deepEqual([...fixture.pending.values()], [a]);
	assert.equal(button("Check or retry this import"), undefined);
	await act(async () => button("Import interval data").click());
	await choose("Imports to review", scope + ":" + JSON.parse(a).key);
	assert.ok(button("Check or retry this import"));
	assert.deepEqual(
		fixture.uploads,
		[b, b],
		"the next pending import still requires explicit retry",
	);
});

async function prepareFile(t, options = {}) {
	const fixture = await rig(t, options);
	await until(
		() =>
			button("Import interval data") &&
			!button("Import interval data").disabled,
	);
	await act(async () => button("Import interval data").click());
	const bytes = new TextEncoder().encode(source);
	await act(async () => {
		const input = field("Source file");
		Object.defineProperty(input, "files", {
			configurable: true,
			value: [{ size: bytes.length, arrayBuffer: async () => bytes.buffer }],
		});
		input.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await until(() => !field("Column delimiter").disabled);
	if (!options.editor)
		await act(async () => assert.equal(fixture.guard(), false));
	await choose("Column delimiter", ";");
	await act(async () => button("Preview columns").click());
	await until(() => field("Timestamp column"));
	assert.equal(button("Import and review data").disabled, true);
	assert.deepEqual(fixture.uploads, []);
	for (const [label, value] of [
		["Timestamp column", "time"],
		["Value column", "power"],
		["Measurement point", "net_import"],
		["Value meaning and unit", "interval_average_kw"],
		["Decimal separator in the file", "."],
		["Source type", "synthetic"],
		["Source time zone", "Europe/Oslo"],
		["Interval boundaries", "fixed"],
		["The timestamp identifies…", "start"],
	])
		await choose(label, value);
	await enter(field("Interval durationmin"), "15");
	await enter(field("Source label"), "Synthetic new file");
	await enter(
		field("Source and permission for permanent private storage"),
		"Created by this test",
	);
	await until(() => !button("Import and review data").disabled);
	return fixture;
}

test("a new file needs explicit mapping and provenance, and closing is guarded until recovery is durable", async (t) => {
	const fixture = await prepareFile(t);
	await act(async () => button("Import and review data").click());
	await until(() => button("Use this profile in the open draft"));
	const uploaded = JSON.parse(fixture.uploads[0]);
	assert.equal(document.activeElement.tagName, "H3");
	assert.equal(document.activeElement.textContent, "Data interpretation");
	assert.equal(uploaded.content_base64, btoa(source));
	assert.deepEqual(uploaded.mapping, mapping);
	assert.equal(fixture.guard(), true);
	assert.equal(fixture.attachments.length, 0);
});

test("close and reload are guarded while selected file bytes are still being read", async (t) => {
	const fixture = await rig(t),
		gate = deferred();
	await until(
		() =>
			button("Import interval data") &&
			!button("Import interval data").disabled,
	);
	await act(async () => button("Import interval data").click());
	const bytes = new TextEncoder().encode(source);
	await act(async () => {
		const input = field("Source file");
		Object.defineProperty(input, "files", {
			configurable: true,
			value: [{ size: bytes.length, arrayBuffer: () => gate.promise }],
		});
		input.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(button("Preview columns").disabled, true);
	await act(async () => assert.equal(fixture.guard(), false));
	assert.equal(
		window.dispatchEvent(
			new window.Event("beforeunload", { cancelable: true }),
		),
		false,
	);
	assert.deepEqual(fixture.uploads, []);
	await act(async () => gate.resolve(bytes.buffer));
	await until(() => !field("Column delimiter").disabled);
	await act(async () => button("Cancel").click());
	assert.equal(fixture.guard(), true);
	assert.equal(document.activeElement, button("Import interval data"));
	assert.equal(
		window.dispatchEvent(
			new window.Event("beforeunload", { cancelable: true }),
		),
		true,
	);
});

test("an unidentified 422 preserves the exact import until its explicit retry is confirmed", async (t) => {
	const original = command();
	const fixture = await rig(t, {
		bodies: [original],
		refuse: true,
		refuseCode: "request_failed",
	});
	await until(() => button("Check or retry this import"));
	await act(async () => button("Check or retry this import").click());
	await until(
		() =>
			fixture.uploads.length === 1 &&
			!button("Check or retry this import").disabled,
	);
	assert.equal(fixture.uploads[0], original);
	assert.equal(field("Source file"), undefined);
	fixture.setRefuse(false);
	await act(async () => button("Check or retry this import").click());
	await until(() => button("Use this profile in the open draft"));
	assert.deepEqual(fixture.uploads, [original, original]);
});

test("typed input refusal permits correction despite failed local writes and cleanup", async (t) => {
	const fixture = await prepareFile(t, { storageDown: true, refuse: true });
	await act(async () => button("Import and review data").click());
	await until(
		() =>
			document.body.textContent.includes("Negative values are accepted only") &&
			field("Measurement point"),
	);
	assert.equal(button("Check or retry this import"), undefined);
	assert.ok(field("Measurement point"));
	assert.ok(
		document.activeElement.textContent.includes(
			"Negative values are accepted only",
		),
		"user-triggered import errors receive focus after the correction form returns",
	);
	await act(async () => assert.equal(fixture.guard(), false));
	fixture.setRefuse(false);
	await choose("Measurement point", "net_import");
	await act(async () => button("Import and review data").click());
	await until(() => button("Use this profile in the open draft"));
	const [refused, corrected] = fixture.uploads.map(JSON.parse);
	assert.notEqual(refused.key, corrected.key);
	assert.equal(refused.content_base64, corrected.content_base64);
	assert.equal(corrected.mapping.measurement, "net_import");
});

test("a refused recovery is removed before slow cleanup and cannot regain false durable admission", async (t) => {
	const a = command("Synthetic A"),
		b = command("Synthetic B"),
		gate = deferred();
	const fixture = await rig(t, {
		bodies: [a, b],
		refuse: true,
		cleanupGate: gate,
	});
	await until(() => button("Check or retry this import"));
	await choose("Imports to review", scope + ":" + JSON.parse(b).key);
	await act(async () => button("Check or retry this import").click());
	await until(() => fixture.cleanupStarted);
	await act(async () => assert.equal(fixture.guard(), false));
	assert.equal(field("Imports to review").disabled, true);
	assert.equal(
		[...field("Imports to review").options].some(
			(option) => option.value === scope + ":" + JSON.parse(b).key,
		),
		false,
	);
	await act(async () => gate.resolve());
	await until(() => !button("Cancel").disabled);
	await act(async () => button("Cancel").click());
	await act(async () => button("Import interval data").click());
	await choose("Imports to review", scope + ":" + JSON.parse(a).key);
	assert.equal(fixture.guard(), true);
	fixture.setRefuse(false);
	await act(async () => button("Check or retry this import").click());
	await until(() => button("Use this profile in the open draft"));
	assert.deepEqual(fixture.uploads, [b, a]);
});

test("confirmed server selection releases the source workflow despite unavailable browser recovery", async (t) => {
	const fixture = await prepareFile(t, { storageDown: true, editor: true });
	await act(async () => button("Import and review data").click());
	await until(() => button("Use this profile in the open draft"));
	await act(async () => button("Use this profile in the open draft").click());
	await until(() => button("Remove draft selection"));
	assert.equal(
		document.body.textContent.includes(
			"This profile selection is saved with the project.",
		),
		false,
	);
	await act(async () => button("Projects").click());
	assert.equal(fixture.closes, 0);
	await act(async () => button("Save project").click());
	await until(() =>
		document.body.textContent.includes(
			"This profile selection is saved with the project.",
		),
	);
	assert.equal(fixture.project.revision, 2);
	assert.equal(
		fixture.project.inputs.profile_selections.selected.net_import,
		assetId,
	);
	assert.equal(button("Check or retry this import"), undefined);
	await act(async () => button("Projects").click());
	assert.equal(fixture.closes, 1);
});

test("selection notices follow current draft undo and redo independently of the saved baseline", async (t) => {
	await prepareFile(t, { editor: true });
	await act(async () => button("Import and review data").click());
	await until(() => button("Use this profile in the open draft"));
	await act(async () => button("Use this profile in the open draft").click());
	const draftNotice = () =>
		document.body.textContent.includes(
			"The profile is selected in the open draft.",
		);
	const savedNotice = () =>
		document.body.textContent.includes(
			"This profile selection is saved with the project.",
		);
	await until(draftNotice);
	assert.ok(
		document.activeElement.textContent.startsWith(
			"The profile is selected in the open draft.",
		),
	);
	assert.ok(button("Remove draft selection"));
	button("Undo").focus();
	await act(async () => button("Undo").click());
	assert.equal(button("Remove draft selection"), undefined);
	assert.equal(draftNotice(), false);
	assert.equal(savedNotice(), false);
	button("Redo").focus();
	await act(async () => button("Redo").click());
	assert.ok(button("Remove draft selection"));
	assert.equal(draftNotice(), true);
	assert.equal(
		document.activeElement,
		button("Redo"),
		"history does not replay import-completion focus",
	);
	await act(async () => button("Save project").click());
	await until(savedNotice);
	await act(async () => button("Undo").click());
	assert.equal(button("Remove draft selection"), undefined);
	assert.equal(draftNotice(), false);
	assert.equal(savedNotice(), false);
	await act(async () => button("Redo").click());
	assert.ok(button("Remove draft selection"));
	assert.equal(savedNotice(), true);
});

test("a different native scope confirmed during the recovery write prevents an old upload dispatch", async (t) => {
	const gate = deferred(),
		body = command();
	const fixture = await rig(t, { bodies: [body], writeGate: gate });
	await until(() => button("Check or retry this import"));
	await act(async () => button("Check or retry this import").click());
	await until(() => fixture.writeStarted);
	fixture.changeOwner({ ...session, query_scope: "7".repeat(64) });
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await until(() => fixture.client.isCurrentScope("7".repeat(64)));
	await act(async () => gate.resolve());
	assert.deepEqual(fixture.uploads, []);
	assert.equal(fixture.pending.get(JSON.parse(body).key), body);
	assert.deepEqual(fixture.attachments, []);
});

test("authentication refusal rechecks native identity even after the client invalidates its scope", async (t) => {
	const body = command();
	const fixture = await rig(t, { bodies: [body], auth: true });
	await until(() => button("Check or retry this import"));
	const before = fixture.calls.filter((path) =>
		path.endsWith("/bootstrap"),
	).length;
	await act(async () => button("Check or retry this import").click());
	await until(
		() =>
			fixture.calls.filter((path) => path.endsWith("/bootstrap")).length >
				before && fixture.client.isCurrentScope(scope),
	);
	assert.deepEqual(fixture.uploads, [body]);
	assert.equal(fixture.pending.get(JSON.parse(body).key), body);
});

test("same-scope verification does not strand delayed recovery hydration", async (t) => {
	const gate = deferred();
	const fixture = await rig(t, { hydrationGate: gate });
	await until(() => fixture.client.isCurrentScope(scope));
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await act(async () => gate.resolve());
	await until(
		() =>
			fixture.client.isCurrentScope(scope) &&
			button("Import interval data") &&
			!button("Import interval data").disabled,
	);
	assert.deepEqual(fixture.uploads, []);
});

test("a rejected replacement file cannot leave an older file available for import", async (t) => {
	await rig(t);
	await until(
		() =>
			button("Import interval data") &&
			!button("Import interval data").disabled,
	);
	await act(async () => button("Import interval data").click());
	const bytes = new TextEncoder().encode(source);
	const selectFile = async (file) =>
		act(async () => {
			const input = field("Source file");
			Object.defineProperty(input, "files", {
				configurable: true,
				value: [file],
			});
			input.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	await selectFile({
		size: bytes.length,
		arrayBuffer: async () => bytes.buffer,
	});
	await choose("Column delimiter", ";");
	await until(() => !button("Preview columns").disabled);
	await act(async () => button("Preview columns").click());
	await until(() => field("Timestamp column"));
	await selectFile({
		size: 100001,
		arrayBuffer: async () => assert.fail("oversized bytes must not be read"),
	});
	await until(() =>
		document.body.textContent.includes("exceeds this service's size limit"),
	);
	assert.equal(button("Preview columns").disabled, true);
	assert.equal(field("Timestamp column"), undefined);
});

test("an interactive result is revealed once; background reads and interval paging keep user focus", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { OwnedProfile } = await import("../src/components/OwnedProfile.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const elsewhere = document.createElement("input");
	elsewhere.setAttribute("aria-label", "Work elsewhere");
	dom.element.before(elsewhere);
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url, init) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return json(session);
			if (path.endsWith("/assets/read")) return json(asset);
			assert.ok(path.endsWith("/profiles/preview"));
			const { offset } = JSON.parse(init.body);
			return json({
				...preview,
				offset,
				rows: [preview.rows[offset]],
				next_offset: offset === 0 ? 1 : null,
			});
		},
	});
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const render = async (interactive) =>
		act(async () =>
			root.render(
				React.createElement(
					React.StrictMode,
					null,
					React.createElement(
						SessionBoundary,
						{ client },
						(confirmed, recheck) =>
							React.createElement(OwnedProfile, {
								projectId,
								assetId,
								session: confirmed,
								client,
								locale: "en-GB",
								recheck,
								onSelect: interactive ? () => {} : undefined,
							}),
					),
				),
			),
		);
	elsewhere.focus();
	await render(false);
	await until(() => button("Next intervals"));
	assert.equal(document.activeElement, elsewhere);
	await render(true);
	await until(() => document.activeElement.tagName === "H3");
	assert.equal(document.activeElement.textContent, "Data interpretation");
	elsewhere.focus();
	await render(true);
	assert.equal(document.activeElement, elsewhere);
	await act(async () => button("Next intervals").click());
	await until(() => button("First intervals"));
	assert.equal(document.activeElement, elsewhere);
	await act(async () => button("First intervals").click());
	await until(() => button("Next intervals"));
	assert.equal(document.activeElement, elsewhere);
});

test("same-identity verification consumes deferred completion before history can replay it", async (t) => {
	const gate = deferred();
	const fixture = await rig(t, {
		bodies: [command()],
		editor: true,
		focusGate: gate,
	});
	await until(() => button("Check or retry this import"));
	await act(async () => button("Check or retry this import").click());
	await until(() => button("Use this profile in the open draft"));
	await act(async () => button("Use this profile in the open draft").click());
	await until(
		() =>
			button("Import interval data") && !fixture.client.isCurrentScope(scope),
	);
	await act(async () => gate.resolve());
	await until(() => fixture.client.isCurrentScope(scope));
	assert.ok(
		document.activeElement.textContent.startsWith(
			"The profile is selected in the open draft.",
		),
	);
	button("Undo").focus();
	await act(async () => button("Undo").click());
	assert.equal(document.activeElement, button("Undo"));
});

test("native withdrawal between render and effects prevents cached-result and error focus", async (t) => {
	for (const mode of ["preview", "error"])
		await t.test(mode, async (st) => {
			const dom = setupDom();
			const { createRoot } = await import("react-dom/client");
			const { QueryClient, QueryClientProvider } =
				await import("@tanstack/react-query");
			const { OwnedProfile } =
				await import("../src/components/OwnedProfile.tsx");
			const { ProfileError } =
				await import("../src/components/ProfileError.tsx");
			const { PlannerClient } = await import("../src/data/PlannerClient.ts");
			const client = new PlannerClient({
				origin: location.origin,
				baseUrl: location.origin + "/rpc/",
				nonceUrl: location.origin + "/nonce",
				fetch: async (url) =>
					String(url).endsWith("/nonce")
						? new Response("abcdefghij")
						: json(session),
			});
			await client.bootstrap();
			const cache = new QueryClient({
				defaultOptions: { queries: { staleTime: Infinity, retry: false } },
			});
			cache.setQueryData(
				[scope, "profile", projectId, assetId, "unassigned", 0],
				{ asset, preview },
			);
			const root = createRoot(dom.element);
			st.after(async () => {
				await dom.dispose(root);
				cache.clear();
			});
			const elsewhere = document.createElement("input");
			dom.element.before(elsewhere);
			elsewhere.focus();
			const focusDuringWithdrawal = [];
			document.addEventListener("focusin", (event) => {
				if (!client.isCurrentScope(scope))
					focusDuringWithdrawal.push(event.target.tagName);
			});
			function Parent() {
				React.useLayoutEffect(() => client.invalidate(), []);
				return mode === "preview"
					? React.createElement(OwnedProfile, {
							projectId,
							assetId,
							session,
							client,
							locale: "en-GB",
							recheck() {},
							onSelect() {},
						})
					: React.createElement(ProfileError, {
							error: new Error("private fixture exception"),
							focus: true,
							canReveal: () => client.isCurrentScope(scope),
						});
			}
			await act(async () =>
				root.render(
					React.createElement(
						QueryClientProvider,
						{ client: cache },
						React.createElement(Parent),
					),
				),
			);
			assert.equal(client.isCurrentScope(scope), false);
			assert.deepEqual(focusDuringWithdrawal, []);
			assert.equal(document.activeElement, elsewhere);
		});
});

test("persistent profile authentication failure rechecks once and waits for an explicit session retry", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { OwnedProfile } = await import("../src/components/OwnedProfile.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	let bootstraps = 0,
		reads = 0;
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url) => {
			if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
			if (String(url).endsWith("/bootstrap")) {
				bootstraps++;
				return json(session);
			}
			assert.ok(String(url).endsWith("/assets/read"));
			reads++;
			return json({ error: { code: "identity_refused" } }, 403);
		},
	});
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(SessionBoundary, { client }, (confirmed, recheck) =>
				React.createElement(OwnedProfile, {
					projectId,
					assetId,
					session: confirmed,
					client,
					locale: "en-GB",
					recheck,
				}),
			),
		),
	);
	await until(() => button("Check session") && reads === 2);
	await act(async () => {
		await Promise.resolve();
		await Promise.resolve();
	});
	assert.equal(bootstraps, 2);
	assert.equal(reads, 2);
	await act(async () => button("Check session").click());
	await until(() => reads === 4 && button("Check session"));
	assert.equal(bootstraps, 4);
});

test("a native-granted previous import namespace is retained through explicit retry and exact cleanup", async (t) => {
	const original = command("Prior guest synthetic source");
	const fixture = await rig(t, {
		bodies: [original],
		recoveryOrigin: "a".repeat(64),
	});
	await until(() => button("Check or retry this import"));
	assert.deepEqual(fixture.uploads, []);
	await act(async () => button("Check or retry this import").click());
	await until(() => button("Use this profile in the open draft"));
	assert.deepEqual(fixture.uploads, [original]);
	await act(async () => button("Use this profile in the open draft").click());
	await until(() => fixture.pending.size === 0);
	assert.deepEqual(fixture.attachments, [[assetId, "net_import"]]);
});
