import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { beginDraft } from "../src/domain/draft.ts";
import { emptyBrief } from "../src/domain/brief.ts";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { readCommercialDesign } from "../src/data/readCommercialDesign.ts";
import { CommercialSizing } from "../src/components/commercial/CommercialSizing.tsx";
import { setupDom, until, enter } from "./dom-fixture.mjs";

/**
 * The commercial chain's break was that the workspace never sent the two
 * inputs the engine requires for a sized answer. This holds the interface to
 * that contract: both fields reach `design/commercial`, the engine's own
 * refusal is explained in the customer's words, and a sized answer is shown.
 */

const projectId = "1".repeat(32),
	scope = "2".repeat(64);

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
		runtime_sha256: "3".repeat(64),
		models: {},
		limits: {
			max_body_bytes: 16777216,
			max_csv_bytes: 8388608,
			max_page_size: 100,
			max_json_depth: 32,
		},
	},
};

function draft(projectUse) {
	return beginDraft({
		id: projectId,
		title: "Commercial sizing",
		revision: 1,
		updated_at: "2026-11-11T00:00:00Z",
		inputs: {
			brief: {
				...emptyBrief(),
				project_use: projectUse,
				site: {
					...emptyBrief().site,
					location_label: "80331 München",
				},
				annual_load: {
					kwh: 380000,
					basis: "user_estimate",
					source_note: "",
				},
			},
		},
	});
}

const sized = {
	status: "sized",
	load: {
		intervals: 2880,
		days: 30,
		annual_kwh: 380000,
		peak_kw: 119.4,
		base_kw: 18,
		full_load_hours: 3200,
		duration_curve_kw: [],
	},
	options: [{ cap_kw: 95.5, power_kw: 23.9, energy_kwh: 210.5, events: 12 }],
	power_kw_range: { low: 49.4, high: 49.4 },
	energy_kwh_range: { low: 443.2, high: 443.2 },
	basis: ["Peak of 119.4 kW capped at 70 kW: 49.4 kW of battery power"],
	systems: [
		{
			inverter: {
				id: 1,
				sku: "GW125",
				model: "GW125/261-ESA-LCN-G10",
				device_class: "all-in-one-systems",
			},
			inverter_units: 2,
			battery: null,
			usable_kwh: 261,
			power_kw: 62.5,
			lines: [],
		},
	],
	warnings: [],
	inquiry: "Talk to us",
};

/** A 30-day profile the engine accepts: one value per line, no timestamps. */
function profile(days = 30) {
	const lines = [];
	for (let day = 0; day < days; day += 1)
		for (let quarter = 0; quarter < 96; quarter += 1) {
			const hour = (quarter * 15) / 60;
			lines.push(hour >= 7 && hour < 18 ? "95.5" : "18.25");
		}
	return lines.join("\n");
}

const file = (text) => new File([text], "load.csv", { type: "text/csv" });

/** Mount into the fixture's own element, the way every planner test does. */
async function mount(element, node) {
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(element);
	await act(async () => root.render(node));
	return root;
}

test("the panel sends the profile and the target peak, then shows a sized system", async () => {
	const body = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const calls = [];
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/wp-json/linker/v1/planner",
		nonceUrl:
			"https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce",
		origin: "https://fixture.invalid",
		fetch: async (input, init) => {
			const url = String(input instanceof URL ? input.href : input);
			if (url.includes("action=rest-nonce"))
				return new Response("abcdefghij", { status: 200 });
			if (url.endsWith("/bootstrap"))
				return new Response(JSON.stringify(session), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				});
			calls.push({
				path: url.slice(url.indexOf("/rpc/") + 5),
				command: JSON.parse(String(init?.body ?? "{}")),
			});
			return new Response(JSON.stringify(sized), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		},
	});
	await client.bootstrap();
	const root = await mount(
		body.element,
		<CommercialSizing
			draft={draft("commercial")}
			client={client}
			session={session}
			locale="en-US"
			active
			disabled={false}
			onError={() => {}}
		/>,
	);
	try {
		// The postcode and the annual consumption come from the project brief;
		// the grid capacity and the target peak are this panel's own inputs.
		assert.equal(
			body.element.querySelector('input[inputmode="numeric"]')?.value,
			"80331",
		);
		const numbers = Array.from(
			body.element.querySelectorAll('input[inputmode="decimal"]'),
		);
		const annual = numbers.find((input) => input.value === "380000");
		assert.ok(annual, "the brief's annual consumption is offered");
		await enter(numbers[numbers.indexOf(annual!) - 1], "150");
		await enter(numbers[numbers.indexOf(annual!) + 1], "119");
		await enter(numbers[numbers.indexOf(annual!) + 2], "70");

		const picker = body.element.querySelector('input[type="file"]');
		assert.ok(picker);
		Object.defineProperty(picker!, "files", {
			value: [file(profile())],
			configurable: true,
		});
		await act(async () => {
			picker!.dispatchEvent(new Event("change", { bubbles: true }));
		});
		await until(() => document.body.textContent?.includes("intervals read"));

		await act(async () => {
			body.element
				.querySelector<HTMLButtonElement>('button[type="submit"]')!
				.click();
		});
		await until(() => body.element.textContent?.includes("Sized storage"));

		const call = calls.find((entry) => entry.path === "design/commercial");
		assert.ok(call, "the commercial design route is called");
		assert.equal(call!.command.target_peak_kw, 70);
		assert.equal(call!.command.grid_connection_kva, 150);
		assert.equal(call!.command.plz, "80331");
		assert.equal(call!.command.locale, "en");
		assert.deepEqual(call!.command.goals, ["peak_shaving"]);
		assert.equal(
			String(call!.command.load_profile_csv).split("\n").length,
			2880,
			"every interval reaches the engine",
		);
		assert.ok(
			String(call!.command.load_profile_csv)
				.split("\n")
				.every((line) => /^\d+(?:\.\d+)?$/.test(line)),
			"the values arrive as the engine reads them",
		);
		const text = body.element.textContent ?? "";
		assert.ok(
			text.includes("GW125/261-ESA-LCN-G10"),
			"the sized system is shown",
		);
		assert.ok(text.includes("443.2"), "the sized usable energy is shown");
	} finally {
		await act(async () => root.unmount());
		await body.dispose({ unmount: async () => {} });
	}
});

test("a residential project never sees the commercial panel", async () => {
	const body = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/wp-json/linker/v1/planner",
		nonceUrl:
			"https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce",
		origin: "https://fixture.invalid",
		fetch: async () => new Response("abcdefghij", { status: 200 }),
	});
	const root = await mount(
		body.element,
		<CommercialSizing
			draft={draft("residential")}
			client={client}
			session={session}
			locale="en-US"
			active={false}
			disabled={false}
			onError={() => {}}
		/>,
	);
	try {
		assert.equal(
			body.element.textContent,
			"",
			"an inactive commercial panel renders nothing",
		);
	} finally {
		await act(async () => root.unmount());
		await body.dispose({ unmount: async () => {} });
	}
});

test("the engine's refusal of a short profile reaches the customer as a sentence", async () => {
	const body = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/wp-json/linker/v1/planner",
		nonceUrl:
			"https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce",
		origin: "https://fixture.invalid",
		fetch: async (input) => {
			const url = String(input instanceof URL ? input.href : input);
			if (url.includes("action=rest-nonce"))
				return new Response("abcdefghij", { status: 200 });
			if (url.endsWith("/bootstrap"))
				return new Response(JSON.stringify(session), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				});
			return new Response(
				JSON.stringify({ error: { code: "profile_too_short" } }),
				{ status: 422, headers: { "Content-Type": "application/json" } },
			);
		},
	});
	await client.bootstrap();
	const root = await mount(
		body.element,
		<CommercialSizing
			draft={draft("commercial")}
			client={client}
			session={session}
			locale="en-US"
			active
			disabled={false}
			onError={() => {}}
		/>,
	);
	try {
		const element = body.element;
		const numbers = Array.from(
			element.querySelectorAll('input[inputmode="decimal"]'),
		);
		// Field order: grid capacity, annual consumption, peak, target peak.
		await enter(numbers[0], "150");
		await enter(numbers[2], "119");
		await enter(numbers[3], "70");
		const picker = element.querySelector('input[type="file"]');
		Object.defineProperty(picker!, "files", {
			value: [file(profile())],
			configurable: true,
		});
		await act(async () => {
			picker!.dispatchEvent(new Event("change", { bubbles: true }));
		});
		await until(() => element.textContent?.includes("intervals read"));
		await act(async () => {
			element.querySelector('button[type="submit"]')!.click();
		});
		await until(() => element.textContent?.includes("shorter than one week"));
		assert.ok(
			!element.textContent?.includes("load_profile"),
			"no server diagnostic leaks into the interface",
		);
	} finally {
		await act(async () => root.unmount());
		await body.dispose({ unmount: async () => {} });
	}
});

test("a sized answer without the engine's systems fields is not presented as a design", () => {
	assert.throws(
		() =>
			readCommercialDesign({ status: "sized", systems: [{ inverter: {} }] }),
		/invalid_commercial_result/,
	);
	assert.equal(
		readCommercialDesign({
			status: "indicative",
			systems: [],
			options: [],
			basis: [],
			warnings: [],
		}).systems.length,
		0,
	);
});

test("the panel sends nothing until the inputs the engine requires are there", async () => {
	const body = setupDom();
	globalThis.indexedDB = new IDBFactory();
	let requests = 0;
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/wp-json/linker/v1/planner",
		nonceUrl:
			"https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce",
		origin: "https://fixture.invalid",
		fetch: async (input) => {
			const url = String(input instanceof URL ? input.href : input);
			if (url.includes("action=rest-nonce"))
				return new Response("abcdefghij", { status: 200 });
			if (url.endsWith("/bootstrap"))
				return new Response(JSON.stringify(session), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				});
			requests += 1;
			return new Response(JSON.stringify(sized), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		},
	});
	await client.bootstrap();
	// A brief with no postcode and no annual figure: the engine cannot size
	// anything from it, so the panel must say what is missing instead of
	// sending a request that a client-side check would turn into a generic
	// failure (measured on the review stack before this guard existed).
	const bare = beginDraft({
		id: projectId,
		title: "Commercial sizing",
		revision: 1,
		updated_at: "2026-11-11T00:00:00Z",
		inputs: { brief: { ...emptyBrief(), project_use: "commercial" } },
	});
	const root = await mount(
		body.element,
		<CommercialSizing
			draft={bare}
			client={client}
			session={session}
			locale="en-US"
			active
			disabled={false}
			onError={() => {}}
		/>,
	);
	try {
		const element = body.element;
		const submit = element.querySelector('button[type="submit"]');
		assert.ok(submit, "the panel offers its calculate action");
		assert.equal(submit!.disabled, true, "an incomplete request is not sent");
		const status = Array.from(element.querySelectorAll('[role="status"]'))
			.map((node) => node.textContent ?? "")
			.join(" ");
		assert.match(status, /Still needed/);
		assert.match(status, /postcode/);
		assert.match(status, /annual consumption/);

		// A profile alone is not enough either: the target peak is what turns
		// an indicative cap list into a sized system.
		const numbers = Array.from(
			element.querySelectorAll('input[inputmode="decimal"]'),
		);
		await enter(numbers[0], "150"); // grid capacity
		await enter(numbers[1], "380000"); // annual consumption
		await enter(element.querySelector('input[inputmode="numeric"]'), "80331");
		const picker = element.querySelector('input[type="file"]');
		Object.defineProperty(picker!, "files", {
			value: [file(profile())],
			configurable: true,
		});
		await act(async () => {
			picker!.dispatchEvent(new Event("change", { bubbles: true }));
		});
		await until(() => element.textContent?.includes("intervals read"));
		const statuses = Array.from(
			element.querySelectorAll('[role="status"]'),
		).map((node) => node.textContent ?? "");
		assert.ok(
			statuses.some((text) => /target peak/.test(text)),
			"the missing target peak is named: " + JSON.stringify(statuses),
		);
		assert.equal(
			element.querySelector('button[type="submit"]')!.disabled,
			true,
			"a profile without the target peak is not a sizing request",
		);
		assert.equal(
			requests,
			0,
			"nothing was sent before the inputs were complete",
		);
	} finally {
		await act(async () => root.unmount());
		await body.dispose({ unmount: async () => {} });
	}
});
