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

test("native bootstrap confirms the presented cookie before any private RPC", async () => {
	const { client, calls } = fixture([
		guest(),
		json({ ...context, cookie_confirmed: false }),
		json(context),
		json({ items: [] }),
	]);
	await assert.rejects(client.query("projects/list", {}), {
		code: "session_confirmation_required",
	});
	assert.deepEqual(await client.bootstrap(), context);
	await client.query("projects/list", {
		schema_version: 1,
		page_size: 10,
		after: null,
	});
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
	await account.client.query("projects/list", {});
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
	await assert.rejects(client.send("projects/create", body), {
		code: "upstream",
	});
	assert.equal(calls.length, 3);
	assert.deepEqual(await client.send("projects/create", body), { saved: true });
	assert.equal(calls[2]?.init.body, body);
	assert.equal(calls[3]?.init.body, body);
	await assert.rejects(
		client.send("../identity/claim-session" as JsonRpcPath, "{}"),
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
	await assert.rejects(client.query("projects/list", {}));
	await assert.rejects(client.query("projects/list", {}), {
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
