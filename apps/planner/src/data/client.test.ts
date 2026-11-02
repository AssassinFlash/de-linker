import assert from "node:assert/strict";
import { test } from "node:test";
import { boundedBody } from "./boundedBody.ts";
import { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import type { JsonRpcPath, Session } from "./protocol.ts";
import { readProject, readSession, wire } from "./readProtocol.ts";

const ORIGIN = "https://planner.example";
const context: Session = {
	schema_version: 1,
	kind: "guest",
	cookie_confirmed: true,
	expires_at: 1800000000,
	query_scope: "a".repeat(64),
	nonce: "a123456789",
	claim_pending: false,
	runtime: {
		schema_version: 1,
		runtime_sha256: "b".repeat(64),
		models: { energy: "fixture" },
		limits: {
			max_body_bytes: 16777216,
			max_csv_bytes: 8388608,
			max_page_size: 100,
			max_json_depth: 32,
		},
	},
};
const json = (value: unknown, status = 200): Response =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "content-type": "application/json; charset=UTF-8" },
	});
function fixture(replies: Response[]) {
	const calls: { url: string; init: RequestInit }[] = [];
	const fetcher: typeof fetch = async (url, init) => {
		calls.push({ url: String(url), init: init ?? {} });
		const next = replies.shift();
		if (!next) throw new Error("unexpected_request");
		return next;
	};
	const client = new PlannerClient({
		baseUrl: ORIGIN + "/wp-json/linker/v1/planner",
		nonceUrl: ORIGIN + "/wp-admin/admin-ajax.php?action=rest-nonce",
		origin: ORIGIN,
		fetch: fetcher,
	});
	return { client, calls };
}
const guest = () => new Response("0", { status: 400 });

test("owned report downloads verify both frozen PDF and CSV bytes", async () => {
	for (const format of ["pdf", "csv"] as const) {
		const content = new TextEncoder().encode(
				format === "pdf"
					? "%PDF-owned fixture"
					: "\uFEFFProdukt,Menge\r\nModul,24\r\n",
			),
			digest = new Uint8Array(await crypto.subtle.digest("SHA-256", content)),
			sha = Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join(""),
			{ client, calls } = fixture([
				guest(),
				json(context),
				new Response(content),
				new Response(content),
			]);
		await client.bootstrap();
		const file =
			format === "pdf"
				? await client.reportPdf(
						"project",
						"asset",
						context.query_scope,
						undefined,
						sha,
					)
				: await client.reportCsv("project", "asset", context.query_scope, sha);
		assert.deepEqual(new Uint8Array(await file.arrayBuffer()), content);
		assert.equal(calls[2]!.init.credentials, "same-origin");
		assert.equal(calls[2]!.init.cache, "no-store");
		await assert.rejects(
			client.reportCsv("project", "asset", context.query_scope, "0".repeat(64)),
			(error: unknown) =>
				error instanceof ApiError && error.code === "report_download_failed",
		);
	}
});

test("large PV series is the only larger verified report download", async () => {
	const content = new Uint8Array(36_635_293);
	content.fill(65);
	const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", content));
	const sha = Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join(
		"",
	);
	const { client, calls } = fixture([
		guest(),
		json(context),
		new Response(content),
		new Response(content),
	]);
	await client.bootstrap();
	const blob = await client.reportCsv(
		"project",
		"asset",
		context.query_scope,
		sha,
		undefined,
		true,
	);
	assert.equal(blob.size, content.length);
	assert.equal(JSON.parse(String(calls[2]!.init.body)).series_csv, true);
	await assert.rejects(
		client.reportCsv("project", "asset", context.query_scope, sha),
		{ code: "reply_too_large" },
	);
});

test("scope admission follows native confirmation immediately, independently of React cleanup", async () => {
	const other = { ...context, query_scope: "c".repeat(64) };
	const { client } = fixture([guest(), json(context), guest(), json(other)]);
	assert.equal(client.isCurrentScope(context.query_scope), false);
	await client.bootstrap();
	assert.equal(client.isCurrentScope(context.query_scope), true);
	client.invalidate();
	assert.equal(client.isCurrentScope(context.query_scope), false);
	const confirming = client.bootstrap();
	assert.equal(client.isCurrentScope(other.query_scope), false);
	await confirming;
	assert.equal(client.isCurrentScope(context.query_scope), false);
	assert.equal(client.isCurrentScope(other.query_scope), true);
	await assert.rejects(
		client.send("projects/create", "{}", context.query_scope),
		{ code: "session_changed" },
	);
	await assert.rejects(
		client.send("projects/revise", "{}", context.query_scope),
		{ code: "session_changed" },
	);
	await assert.rejects(client.query("projects/read", {}, context.query_scope), {
		code: "session_changed",
	});
});

test("native bootstrap confirms the presented cookie before any private RPC", async () => {
	const { client, calls } = fixture([
		guest(),
		json({ ...context, cookie_confirmed: false }),
		json(context),
		json({ items: [] }),
	]);
	await assert.rejects(client.query("projects/list", {}, context.query_scope), {
		code: "session_confirmation_required",
	});
	assert.deepEqual(await client.bootstrap(), context);
	await client.query(
		"projects/list",
		{
			schema_version: 1,
			page_size: 10,
			after: null,
		},
		context.query_scope,
	);
	assert.equal(calls.length, 4);
	assert.ok(calls[0]?.url.includes("action=rest-nonce"));
	for (const call of calls) {
		assert.equal(call.init.credentials, "same-origin");
		assert.equal(call.init.cache, "no-store");
		assert.equal(call.init.redirect, "error");
		assert.ok(
			!Object.keys(call.init.headers ?? {}).some((key) =>
				/principal|actor|service|subject/i.test(key),
			),
		);
	}
	assert.equal(
		new Headers(calls[1]?.init.headers).get("X-Linker-Planner-Nonce"),
		null,
	);
	assert.equal(
		new Headers(calls[3]?.init.headers).get("X-Linker-Planner-Nonce"),
		context.nonce,
	);
});

test("account nonce failure blocks bootstrap and cannot silently downgrade to guest", async () => {
	const failed = fixture([new Response("maintenance", { status: 503 })]);
	await assert.rejects(failed.client.bootstrap(), {
		code: "session_unavailable",
	});
	assert.equal(failed.calls.length, 1);
	const account = fixture([
		new Response("1234567890"),
		json({ ...context, kind: "user" }),
		json({ items: [] }),
	]);
	await account.client.bootstrap();
	await account.client.query("projects/list", {}, context.query_scope);
	assert.equal(
		new Headers(account.calls[2]?.init.headers).get("X-WP-Nonce"),
		"1234567890",
	);
	assert.equal(
		new Headers(account.calls[2]?.init.headers).get("X-Linker-Planner-Nonce"),
		null,
	);
});

test("a failed save has no automatic retry; an explicit retry sends the frozen bytes", async () => {
	const { client, calls } = fixture([
		guest(),
		json(context),
		json({ code: "upstream" }, 503),
		json({ saved: true }),
	]);
	await client.bootstrap();
	const body = '{ "schema_version":1, "key":"same-key", "inputs":{"one":1.0} }';
	await assert.rejects(
		client.send("projects/create", body, context.query_scope),
		{
			code: "upstream",
		},
	);
	assert.equal(calls.length, 3);
	assert.deepEqual(
		await client.send("projects/create", body, context.query_scope),
		{ saved: true },
	);
	assert.equal(calls[2]?.init.body, body);
	assert.equal(calls[3]?.init.body, body);
	await assert.rejects(
		client.send(
			"../identity/claim-session" as JsonRpcPath,
			"{}",
			context.query_scope,
		),
		{ code: "invalid_rpc_path" },
	);
	assert.equal(calls.length, 4);
});

test("authentication refusal clears private admission even when its reply is malformed", async () => {
	const { client, calls } = fixture([
		guest(),
		json(context),
		new Response("<html>expired</html>", { status: 401 }),
	]);
	await client.bootstrap();
	await assert.rejects(client.query("projects/list", {}, context.query_scope));
	await assert.rejects(client.query("projects/list", {}, context.query_scope), {
		code: "session_confirmation_required",
	});
	assert.equal(calls.length, 3);
});

test("bounded replies preserve split UTF-8 and cancel an oversized chunked stream", async () => {
	const bytes = new TextEncoder().encode("欧洲😀");
	const stream = new ReadableStream<Uint8Array>({
		start(controller) {
			for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
			controller.close();
		},
	});
	assert.equal(await boundedBody(new Response(stream), bytes.length), "欧洲😀");
	let cancelled = false;
	const over = new ReadableStream<Uint8Array>({
		start(controller) {
			controller.enqueue(new Uint8Array(6));
		},
		cancel() {
			cancelled = true;
		},
	});
	await assert.rejects(boundedBody(new Response(over), 5), {
		code: "reply_too_large",
	});
	assert.equal(cancelled, true);
	await assert.rejects(boundedBody(new Response(Uint8Array.of(255)), 5), {
		code: "invalid_reply_encoding",
	});
});

test("protocol validation rejects unsafe local values before recursive parsing or encoding", () => {
	let called = false;
	const accessor = Object.defineProperty({}, "value", {
		enumerable: true,
		get() {
			called = true;
			return 1;
		},
	});
	assert.throws(() => wire(accessor, 32, 1000), ApiError);
	assert.equal(called, false);
	const cycle: Record<string, unknown> = {};
	cycle.self = cycle;
	assert.throws(() => wire(cycle as never, 32, 1000), { code: "cyclic_json" });
	assert.throws(() => wire({ number: Infinity }, 32, 1000), {
		code: "invalid_json_number",
	});
	assert.throws(() => wire({ one: [undefined] } as never, 32, 1000), ApiError);
	const encoder = Object.defineProperty({}, "toJSON", {
		value() {
			called = true;
			return {};
		},
	});
	assert.throws(() => wire(encoder, 32, 1000), {
		code: "invalid_json_encoder",
	});
	assert.equal(called, false);
	assert.equal(
		wire({ zero: 0, empty: {}, array: [] }, 32, 1000),
		'{"zero":0,"empty":{},"array":[]}',
	);
});

test("wire schemas reject coercion and extra response fields without changing the input", () => {
	assert.throws(() => readSession({ ...context, expires_at: "1800000000" }), {
		code: "invalid_session_reply",
	});
	assert.throws(() => readSession({ ...context, principal: "forged" }), {
		code: "invalid_session_reply",
	});
	assert.equal(typeof context.expires_at, "number");
	assert.throws(
		() =>
			readProject({
				id: "a".repeat(32),
				title: "Project",
				revision: 1,
				input_sha256: "b".repeat(64),
				inputs: [],
			}),
		{ code: "invalid_project_reply" },
	);
});

test("the optional larger-roof budget is strictly read alongside the ordinary budget", () => {
	const ordinary = {
		max_module_steps: 220000,
		max_samples: 2000000,
		max_ray_face_checks: 20000000,
		max_bounds_checks: 50000000,
		index_leaf_size: 8,
	};
	const expanded = {
		max_module_steps: 841000,
		max_samples: 4300000,
		max_modules: 96,
		max_strings: 6,
		max_weather_rows: 8760,
	};
	const session = {
		...context,
		runtime: {
			...context.runtime,
			models: { geometric_pv_generation: "prepare_geometric_pv_reference_v1" },
			limits: {
				...context.runtime.limits,
				geometric_pv_generation: ordinary,
				geometric_pv_clear_flat_roof: expanded,
			},
		},
	};
	assert.equal(readSession(session), session);
	const pitchedSession = {
		...session,
		runtime: {
			...session.runtime,
			limits: {
				...session.runtime.limits,
				geometric_pv_clear_pitched_roof: expanded,
			},
		},
	};
	assert.equal(readSession(pitchedSession), pitchedSession);
	assert.throws(
		() =>
			readSession({
				...pitchedSession,
				runtime: {
					...pitchedSession.runtime,
					limits: {
						...pitchedSession.runtime.limits,
						geometric_pv_clear_pitched_roof: { ...expanded, max_modules: 0 },
					},
				},
			}),
		{ code: "invalid_session_reply" },
	);
	for (const value of [
		null,
		{ ...expanded, max_modules: "96" },
		{ ...expanded, max_strings: 0 },
		{ ...expanded, qualified: true },
	])
		assert.throws(
			() =>
				readSession({
					...session,
					runtime: {
						...session.runtime,
						limits: {
							...session.runtime.limits,
							geometric_pv_clear_flat_roof: value,
						},
					},
				}),
			{ code: "invalid_session_reply" },
		);
	assert.throws(
		() =>
			readSession({
				...context,
				runtime: {
					...context.runtime,
					limits: {
						...context.runtime.limits,
						geometric_pv_clear_flat_roof: expanded,
					},
				},
			}),
		{ code: "invalid_session_reply" },
	);
	assert.equal(
		readSession(context),
		context,
		"older sessions keep the ordinary contract",
	);
});
