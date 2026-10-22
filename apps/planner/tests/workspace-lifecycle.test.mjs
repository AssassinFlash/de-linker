import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";

const session = {
	schema_version: 1,
	kind: "guest",
	cookie_confirmed: true,
	expires_at: 2000000000,
	query_scope: "3".repeat(64),
	nonce: "abcdefghij",
	claim_pending: false,
	runtime: {
		schema_version: 1,
		runtime_sha256: "4".repeat(64),
		models: {},
		limits: {
			max_body_bytes: 1000000,
			max_csv_bytes: 100000,
			max_page_size: 30,
			max_json_depth: 32,
		},
	},
};

async function workspaceFixture(t, mode, configureDom = () => {}) {
	const fixture = setupDom();
	configureDom(fixture);
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { ApiError } = await import("../src/data/protocol.ts");
	const brief = emptyBrief();
	brief.annual_load.kwh = 10;
	const project = {
		id: "1".repeat(32),
		title: "Synthetic lifecycle fixture",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: { brief },
	};
	const commits = [];
	let stored = null,
		gate = null,
		nextSession = session,
		bootstraps = 0,
		reads = 0;
	const store = {
		async read() {
			reads++;
			return stored;
		},
		async candidates() {
			return [];
		},
		write(_scope, draft) {
			if (mode === "unavailable")
				return Promise.reject(new Error("quota_unavailable"));
			if (mode === "delayed")
				return new Promise((resolve) =>
					commits.push(() => {
						stored = structuredClone(draft);
						resolve();
					}),
				);
			stored = structuredClone(draft);
			return Promise.resolve();
		},
	};
	const client = {
		invalidate() {},
		async bootstrap() {
			bootstraps++;
			return gate ? gate.promise : nextSession;
		},
		async query() {
			if (nextSession.query_scope !== session.query_scope)
				throw new ApiError(404, "not_found");
			return structuredClone(project);
		},
	};
	const config = {
		baseUrl: location.origin + "/api/",
		nonceUrl: location.origin + "/nonce",
		locale: "en-US",
		countries: { NO: "Norway" },
	};
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(SessionBoundary, { client }, (value, recheck) =>
					React.createElement(Workspace, {
						key: value.query_scope,
						session: value,
						client,
						store,
						config,
						recheck,
					}),
				),
			),
		),
	);
	await until(() => document.querySelector("textarea"));
	const annual = () =>
		[...document.querySelectorAll("input")].find((input) =>
			document
				.getElementById(input.getAttribute("aria-labelledby"))
				?.textContent.includes("Annual consumption"),
		);
	return {
		annual,
		commits,
		reads: () => reads,
		boots: () => bootstraps,
		store,
		root,
		fixture,
		async recheck(event = "focus") {
			const before = bootstraps;
			await act(async () => window.dispatchEvent(new window.Event(event)));
			await until(
				() =>
					bootstraps > before &&
					!document.querySelector(".lp-project").parentElement.hidden,
			);
		},
		startCheck() {
			gate = deferred();
			return gate;
		},
		changeIdentity() {
			nextSession = { ...session, kind: "user", query_scope: "5".repeat(64) };
		},
		nextSession: () => nextSession,
	};
}

test("same identity rechecks retain delayed edits and invalid raw numeric text", async (t) => {
	const app = await workspaceFixture(t, "delayed");
	await enter(app.annual(), "19");
	await until(() => app.commits.length === 1);
	const reads = app.reads();
	await app.recheck();
	assert.equal(app.annual().value, "19");
	assert.equal(app.reads(), reads);
	assert.equal(
		document.querySelector(".lp-save-state").textContent,
		"Unsaved changes",
	);
	await act(async () => {
		for (const commit of app.commits.splice(0)) commit();
	});
	assert.equal(app.annual().value, "19");
	await enter(app.annual(), "1,");
	await app.recheck("online");
	assert.equal(app.annual().value, "1,");
	assert.equal(app.annual().getAttribute("aria-invalid"), "true");
	assert.equal(
		document.querySelector(".lp-save-state").textContent,
		"Input needs attention",
	);
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((button) => button.textContent === "Projects")
			.click(),
	);
	assert.ok(
		document.body.textContent.includes("Correct the highlighted input"),
	);
	await act(async () =>
		app
			.annual()
			.dispatchEvent(
				new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
			),
	);
	assert.equal(app.annual().value, "19");
	assert.ok(
		!document.body.textContent.includes("Browser recovery could not be stored"),
	);
});

test("failed storage and failed identity refresh preserve hidden edits until same owner returns", async (t) => {
	const app = await workspaceFixture(t, "unavailable");
	await enter(document.querySelector("textarea"), "UNSAVED SYNTHETIC NOTE");
	await until(() =>
		document.body.textContent.includes("Browser recovery is unavailable"),
	);
	const gate = app.startCheck();
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	const wrapper = document.querySelector(".lp-project").parentElement;
	assert.equal(wrapper.hidden, true);
	assert.equal(wrapper.hasAttribute("inert"), true);
	assert.equal(
		document.querySelector("textarea").value,
		"UNSAVED SYNTHETIC NOTE",
	);
	await act(async () => gate.reject(new Error("synthetic_offline")));
	await until(() =>
		document.body.textContent.includes("Your workspace could not be opened"),
	);
	assert.equal(wrapper.hidden, true);
	const retry = app.startCheck();
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((button) => button.textContent === "Try again")
			.click(),
	);
	await act(async () => retry.resolve(session));
	await until(() => !wrapper.hidden);
	assert.equal(
		document.querySelector("textarea").value,
		"UNSAVED SYNTHETIC NOTE",
	);
	assert.ok(
		document.body.textContent.includes("Browser recovery is unavailable"),
	);
});

test("a confirmed different identity removes the former editor and does not grant its project", async (t) => {
	const app = await workspaceFixture(t, "available");
	await enter(document.querySelector("textarea"), "PRIVATE SYNTHETIC DRAFT");
	const gate = app.startCheck();
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	assert.equal(
		document.querySelector(".lp-project").parentElement.hidden,
		true,
	);
	app.changeIdentity();
	await act(async () => gate.resolve(app.nextSession()));
	await until(() =>
		document.body.textContent.includes(
			"This project could not be opened in the current session",
		),
	);
	assert.equal(document.querySelector("textarea"), null);
	assert.ok(!document.body.textContent.includes("PRIVATE SYNTHETIC DRAFT"));
});

test("the actual project bar is observed after asynchronous draft opening and on resize", async (t) => {
	let height = 72;
	const observers = new Set();
	const app = await workspaceFixture(t, "available", (fixture) => {
		Object.defineProperty(
			fixture.dom.window.HTMLElement.prototype,
			"offsetHeight",
			{
				configurable: true,
				get() {
					return this.id === "lc-header"
						? 88
						: this.classList.contains("lp-project-bar")
							? height
							: 0;
				},
			},
		);
		globalThis.ResizeObserver = class {
			constructor(callback) {
				this.callback = callback;
				this.targets = new Set();
				observers.add(this);
			}
			observe(target) {
				this.targets.add(target);
			}
			disconnect() {
				this.targets.clear();
				observers.delete(this);
			}
		};
	});
	const root = app.fixture.element;
	assert.equal(root.style.getPropertyValue("--lp-site-header-height"), "88px");
	assert.equal(root.style.getPropertyValue("--lp-project-bar-height"), "72px");
	height = 108;
	for (const observer of observers)
		if (
			[...observer.targets].some((target) =>
				target.classList.contains("lp-project-bar"),
			)
		)
			observer.callback();
	assert.equal(root.style.getPropertyValue("--lp-project-bar-height"), "108px");
});

test("creation authentication failure rechecks once and explicitly retries the exact intent", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	let bootstraps = 0,
		creates = 0,
		created = null;
	const bodies = [];
	const response = (value, status = 200) =>
		new Response(JSON.stringify(value), {
			status,
			headers: { "Content-Type": "application/json" },
		});
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url, init) => {
			if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
			if (String(url).endsWith("/bootstrap")) {
				bootstraps++;
				return response({ ...session, kind: "user" });
			}
			creates++;
			bodies.push(init.body);
			if (creates === 1)
				return response({ code: "rest_cookie_invalid_nonce" }, 403);
			const command = JSON.parse(init.body);
			return response({
				id: "1".repeat(32),
				title: command.title,
				revision: 1,
				input_sha256: "2".repeat(64),
				inputs: command.inputs,
			});
		},
	});
	const store = {
		async readCreation() {
			return null;
		},
		async writeCreation() {},
		async clearCreation() {},
	};
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(
				React.StrictMode,
				null,
				React.createElement(SessionBoundary, { client }, (value, recheck) =>
					React.createElement(NewProject, {
						session: value,
						client,
						store,
						recheck,
						created: (project) => {
							created = project;
						},
					}),
				),
			),
		),
	);
	await until(() =>
		[...document.querySelectorAll("button")].some(
			(button) =>
				button.textContent.includes("New project") && !button.disabled,
		),
	);
	await act(async () => document.querySelector("button").click());
	await enter(document.querySelector("input"), "Synthetic new project");
	const before = bootstraps;
	const submit = () =>
		act(async () =>
			document
				.querySelector("form")
				.dispatchEvent(
					new window.Event("submit", { bubbles: true, cancelable: true }),
				),
		);
	await submit();
	await until(
		() =>
			bootstraps > before &&
			document.body.textContent.includes("Retry project creation") &&
			!document.querySelector("form").parentElement.hidden,
	);
	assert.equal(creates, 1); // No automatic mutation replay after reauthentication.
	assert.equal(document.querySelector("input").value, "Synthetic new project");
	await submit();
	await until(() => created !== null);
	assert.equal(creates, 2);
	assert.equal(bodies[0], bodies[1]);
	assert.equal(created.title, "Synthetic new project");
});

test("a former identity's delayed creation cannot dispatch or restore cache and navigation", async (t) => {
	for (const stage of ["write", "clear"])
		await t.test(stage, async (t) => {
			const fixture = setupDom();
			history.replaceState(null, "", "/workspace/");
			const { createRoot } = await import("react-dom/client");
			const { SessionBoundary } =
				await import("../src/components/SessionBoundary.tsx");
			const { Workspace } = await import("../src/components/Workspace.tsx");
			const { emptyBrief } = await import("../src/domain/brief.ts");
			const gate = deferred();
			const oldSession = { ...session, kind: "user" };
			const newSession = { ...oldSession, query_scope: "9".repeat(64) };
			let nextSession = oldSession,
				reached = false,
				calls = 0,
				cache,
				currentScope;
			const oldAck = {
				id: "1".repeat(32),
				title: "OLD OWNER SYNTHETIC PROJECT",
				revision: 1,
				input_sha256: "2".repeat(64),
				inputs: { brief: emptyBrief() },
			};
			const store = {
				async readCreation() {
					return null;
				},
				async writeCreation() {
					if (stage === "write") {
						reached = true;
						await gate.promise;
					}
				},
				async clearCreation() {
					if (stage === "clear") {
						reached = true;
						await gate.promise;
					}
				},
			};
			const client = {
				invalidate() {},
				async bootstrap() {
					return nextSession;
				},
				async query() {
					return { items: [], next: null };
				},
				async send() {
					calls++;
					return oldAck;
				},
			};
			const config = {
				locale: "en-GB",
				countries: { NO: "Norway" },
				baseUrl: location.origin + "/api/",
				nonceUrl: location.origin + "/nonce",
			};
			function Track(props) {
				cache = useQueryClient();
				currentScope = props.session.query_scope;
				return React.createElement(Workspace, props);
			}
			const root = createRoot(fixture.element);
			t.after(() => fixture.dispose(root));
			await act(async () =>
				root.render(
					React.createElement(
						React.StrictMode,
						null,
						React.createElement(SessionBoundary, { client }, (value, recheck) =>
							React.createElement(Track, {
								key: value.query_scope,
								session: value,
								client,
								store,
								config,
								recheck,
							}),
						),
					),
				),
			);
			await until(() =>
				[...document.querySelectorAll("button")].some(
					(button) =>
						button.textContent.includes("New project") && !button.disabled,
				),
			);
			await act(async () =>
				[...document.querySelectorAll("button")]
					.find((button) => button.textContent.includes("New project"))
					.click(),
			);
			await enter(document.querySelector("input"), oldAck.title);
			await act(async () =>
				document
					.querySelector("form")
					.dispatchEvent(
						new window.Event("submit", { bubbles: true, cancelable: true }),
					),
			);
			await until(() => reached);
			nextSession = newSession;
			await act(async () => window.dispatchEvent(new window.Event("focus")));
			await until(
				() =>
					currentScope === newSession.query_scope &&
					!document.querySelector(".lp-workspace").parentElement.hidden,
			);
			assert.equal(location.search, "");
			await act(async () => gate.resolve());
			assert.equal(currentScope, newSession.query_scope);
			assert.equal(location.search, "");
			assert.equal(
				cache.getQueryData([oldSession.query_scope, "project", oldAck.id]),
				undefined,
			);
			assert.ok(!document.body.textContent.includes(oldAck.title));
			assert.equal(calls, stage === "write" ? 0 : 1);
		});
});
