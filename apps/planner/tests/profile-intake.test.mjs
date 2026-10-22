import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
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
		(node) => node.textContent === text,
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
	} = {},
) {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { ProfileIntake } = await import("../src/components/ProfileIntake.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	let owner = session,
		writeStarted = false,
		attachConfirmed = false,
		guard = () => true;
	const pending = new Map(bodies.map((body) => [JSON.parse(body).key, body])),
		uploads = [],
		calls = [],
		attachments = [];
	const store = {
		async readProfileImports(verified, id) {
			if (hydrationGate) await hydrationGate.promise;
			return [...pending.values()]
				.filter(
					(body) => verified === scope && JSON.parse(body).project_id === id,
				)
				.map((body) => ({
					body,
					key: JSON.parse(body).key,
					projectId: id,
					label: JSON.parse(body).source_label,
					createdAt: 0,
				}));
		},
		async writeProfileImport(verified, body) {
			assert.equal(verified, scope);
			writeStarted = true;
			if (writeGate) await writeGate.promise;
			pending.set(JSON.parse(body).key, body);
		},
		async clearProfileImport(verified, body) {
			assert.equal(verified, scope);
			assert.ok(
				attachConfirmed || auth,
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
			if (path.endsWith("/bootstrap")) return json(owner);
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
				if (auth) return json({ error: { code: "expired" } }, 401);
				if (lost) {
					lost = false;
					throw new TypeError("synthetic lost acknowledgement");
				}
				return json(asset);
			}
			if (path.endsWith("/assets/read")) return json(asset);
			if (path.endsWith("/profiles/preview")) return json(preview);
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
				React.createElement(SessionBoundary, { client }, (confirmed, recheck) =>
					React.createElement(ProfileIntake, {
						key: confirmed.query_scope,
						projectId,
						session: confirmed,
						client,
						store,
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
		calls,
		attachments,
		get writeStarted() {
			return writeStarted;
		},
		guard: () => guard(),
		changeOwner(value) {
			owner = value;
		},
		root,
		dom,
	};
}

test("unknown imports are explicitly selected and retried with frozen bytes before durable selection clears recovery", async (t) => {
	const a = command("Synthetic A"),
		b = command("Synthetic B");
	const fixture = await rig(t, { bodies: [a, b], lost: true });
	await until(() => button("Check or retry this import"));
	assert.deepEqual(fixture.uploads, []);
	await choose("Imports to review", JSON.parse(b).key);
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
});

test("a new file needs explicit mapping and provenance, and closing is guarded until recovery is durable", async (t) => {
	const fixture = await rig(t);
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
	await act(async () => button("Import and review data").click());
	await until(() => button("Use this profile in the open draft"));
	const uploaded = JSON.parse(fixture.uploads[0]);
	assert.equal(uploaded.content_base64, btoa(source));
	assert.deepEqual(uploaded.mapping, mapping);
	assert.equal(fixture.guard(), true);
	assert.equal(fixture.attachments.length, 0);
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
