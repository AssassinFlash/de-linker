import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import {
	QueryClient,
	QueryClientProvider,
	useQueryClient,
} from "@tanstack/react-query";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
// The renderer port is a fixture; this test proves route/consumer selection.
register("./map-library-loader.mjs", import.meta.url);

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

const siteInput = () => document.querySelector('input[name="location_label"]');
const editor = () =>
	document.querySelector(".sc-project-heading")?.parentElement;
const button = (label, area = document) =>
	[...area.querySelectorAll("button")].find(
		(node) =>
			node.getAttribute("aria-label") === label ||
			node.textContent.trim() === label,
	);
const nav = (label) =>
	[
		...document.querySelectorAll(".sc-nav button, .sc-refinement-tabs button"),
	].find((node) => node.textContent.trim().replace(/^\d+/, "") === label);
async function visit(label) {
	if (
		!nav(label) &&
		["Roof & PV", "Energy profile & CSV", "Matched equipment"].includes(label)
	)
		await act(async () => nav("Fine-tune (optional)").click());
	await act(async () => nav(label).click());
}
const choose = (select, value) =>
	act(async () => {
		select.value = value;
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});

async function startProjectCreation(title) {
	await until(
		() =>
			button("Enter project details") ||
			document.querySelector('input[name="project_title"]'),
	);
	if (button("Enter project details"))
		await act(async () => button("Enter project details").click());
	const name = 'input[name="project_title"]';
	await until(() => document.querySelector(name));
	await enter(document.querySelector(name), title);
	const form = document.querySelector(name).form;
	await choose(
		form.querySelector('select[name="system_scope"]'),
		"new_pv_storage",
	);
	await until(
		() => button("Compare systems") && !button("Compare systems").disabled,
	);
	await act(async () => button("Compare systems").click());
}

async function workspaceFixture(t, mode, configureDom = () => {}) {
	const fixture = setupDom();
	const browserGlobals = new Map();
	const browserValues = {
		indexedDB: new IDBFactory(),
		MutationObserver: window.MutationObserver,
		getComputedStyle: window.getComputedStyle.bind(window),
		requestAnimationFrame: (callback) =>
			setTimeout(() => callback(Date.now()), 0),
		cancelAnimationFrame: clearTimeout,
	};
	for (const [name, value] of Object.entries(browserValues)) {
		browserGlobals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value,
			configurable: true,
			writable: true,
		});
	}
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
		probes = 0,
		reads = 0,
		admittedScope = session.query_scope;
	const store = {
		async read() {
			reads++;
			return stored;
		},
		async readProfileImports() {
			return [];
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
		invalidate() {
			admittedScope = null;
		},
		async bootstrap() {
			bootstraps++;
			if (gate) await gate.promise;
			const value = nextSession;
			admittedScope = value.query_scope;
			return value;
		},
		async probeScope() {
			probes++;
			if (gate) await gate.promise;
			return nextSession.query_scope;
		},
		isCurrentScope(scope) {
			return scope === admittedScope;
		},
		async query(path) {
			if (path === "projects/runs" || path === "projects/list")
				return { items: [], next: null };
			if (path === "equipment/module-templates")
				return { items: [], next: null };
			if (path === "recovery/scopes")
				return { schema_version: 1, scopes: [], next: null };
			assert.equal(path, "projects/read");
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
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of browserGlobals) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
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
	await until(editor);
	const annual = () =>
		[...document.querySelectorAll("input")].find((input) =>
			document
				.getElementById(input.getAttribute("aria-labelledby"))
				?.textContent.includes("Annual electricity use"),
		);
	return {
		annual,
		commits,
		reads: () => reads,
		boots: () => bootstraps,
		probes: () => probes,
		store,
		root,
		fixture,
		async recheck(event = "focus") {
			const before = probes;
			await act(async () => window.dispatchEvent(new window.Event(event)));
			await until(() => probes > before && !editor().parentElement.hidden);
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
	await visit("Energy profile & CSV");
	await enter(app.annual(), "19");
	await until(() => app.commits.length === 1);
	const reads = app.reads();
	await app.recheck();
	assert.equal(app.annual().value, "19");
	assert.equal(app.reads(), reads);
	assert.equal(app.commits.length, 1);
	await act(async () => {
		for (const commit of app.commits.splice(0)) commit();
	});
	assert.equal(app.annual().value, "19");
	await enter(app.annual(), "1,");
	await app.recheck("online");
	assert.equal(app.annual().value, "1,");
	assert.equal(app.annual().getAttribute("aria-invalid"), "true");
	assert.equal(button("Save snapshot").disabled, true);
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

for (const hash of [
	"#sc-map-roof-properties",
	"#sc-map-ring-properties",
	"#sc-map-feature-properties",
])
	test(`reopening the ${hash} property link preserves the roof workspace and map recovery entry`, async (t) => {
		await workspaceFixture(t, "available", () => {
			window.history.replaceState(
				null,
				"",
				location.pathname + location.search + hash,
			);
		});
		assert.equal(nav("Roof & PV").getAttribute("aria-current"), "page");
		assert.equal(button("Aerial map").getAttribute("aria-pressed"), "true");
		await until(() => button("Coordinate references"));
		assert.match(
			document.querySelector(".sc-solar").textContent,
			/The map needs a geographic origin/,
		);
	});

test("a storage-only project reaches Energy use, System and Review without a roof step", async (t) => {
	await workspaceFixture(t, "available");
	await choose(
		document.querySelector("select[name=system_scope]"),
		"storage_only",
	);
	assert.equal(nav("Roof & PV"), undefined);
	await act(async () => button("Continue with storage").click());
	assert.equal(location.hash, "#sc-energy");
	await visit("Matched equipment");
	assert.equal(location.hash, "#sc-system");
	await visit("Review & send");
	assert.equal(location.hash, "#sc-review");
	assert.ok(document.querySelector(".sc-review"));
});

test("step changes retain the energy input and undo history and protect unfinished edits", async (t) => {
	const app = await workspaceFixture(t, "available");
	await visit("Energy profile & CSV");
	const annual = app.annual();
	await enter(annual, "25");
	await visit("Roof & PV");
	assert.ok(annual.closest("[hidden]"));
	await visit("Energy profile & CSV");
	assert.equal(app.annual(), annual);
	assert.equal(annual.value, "25");
	await act(async () =>
		button("Undo", document.querySelector(".sc-project-heading")).click(),
	);
	assert.equal(annual.value, "10");
	await enter(annual, "1,");
	await visit("Project & direction");
	assert.equal(location.hash, "#sc-energy");
	assert.equal(annual.value, "1,");
	assert.ok(
		document.body.textContent.includes("Correct the highlighted input"),
	);
	await act(async () =>
		annual.dispatchEvent(
			new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
		),
	);
	await visit("Roof & PV");
	await act(async () => button("Place modules on the roof").click());
	await act(async () => button("Open roof layout").click());
	await act(async () => button("Draw polygon").click());
	await visit("Project & direction");
	assert.equal(location.hash, "#sc-solar");
	assert.ok(
		document.body.textContent.includes("Finish or cancel roof editing"),
	);
	await act(async () => button("Select plane").click());
	await visit("Project & direction");
	assert.equal(location.hash, "#sc-project");
});

test("failed storage and a failed revalidation keep the open workspace editable behind a retryable notice", async (t) => {
	const app = await workspaceFixture(t, "unavailable");
	await enter(siteInput(), "UNSAVED SYNTHETIC NOTE");
	await until(() =>
		document.body.textContent.includes(
			"The project could not be saved or recovered",
		),
	);
	const gate = app.startCheck();
	const seen = app.probes();
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await until(() => app.probes() > seen);
	const wrapper = editor().parentElement;
	// Stale-while-revalidate: the confirmed workspace stays visible and
	// interactive while the probe is in flight.
	assert.equal(wrapper.hidden, false);
	assert.equal(wrapper.hasAttribute("inert"), false);
	assert.equal(siteInput().value, "UNSAVED SYNTHETIC NOTE");
	await act(async () => gate.reject(new Error("synthetic_offline")));
	await until(() =>
		document.body.textContent.includes(
			"Your session could not be rechecked. Your edits are preserved.",
		),
	);
	assert.equal(wrapper.hidden, false);
	assert.equal(wrapper.hasAttribute("inert"), false);
	assert.ok(
		!document.body.textContent.includes("Your workspace could not be opened"),
	);
	assert.equal(siteInput().value, "UNSAVED SYNTHETIC NOTE");
	assert.ok(
		document.body.textContent.includes(
			"The project could not be saved or recovered",
		),
	);
	const retry = app.startCheck();
	await act(async () =>
		[...document.querySelectorAll("button")]
			.findLast((button) => button.textContent === "Try again")
			.click(),
	);
	await act(async () => retry.resolve());
	await until(
		() =>
			!document.body.textContent.includes(
				"Your session could not be rechecked",
			),
	);
	assert.equal(wrapper.hidden, false);
	assert.equal(siteInput().value, "UNSAVED SYNTHETIC NOTE");
});

test("a confirmed different identity removes the former editor and does not grant its project", async (t) => {
	const app = await workspaceFixture(t, "available");
	await enter(siteInput(), "PRIVATE SYNTHETIC DRAFT");
	const gate = app.startCheck();
	const seen = app.probes();
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await until(() => app.probes() > seen);
	const wrapper = editor().parentElement;
	// The gate appears only after the probe confirms the change, never while
	// the same-identity workspace is merely being rechecked.
	assert.equal(wrapper.hidden, false);
	app.changeIdentity();
	await act(async () => gate.resolve());
	await until(() =>
		document.body.textContent.includes(
			"This project could not be opened in the current session",
		),
	);
	assert.equal(siteInput(), null);
	assert.ok(!document.body.textContent.includes("PRIVATE SYNTHETIC DRAFT"));
	assert.equal(wrapper.hidden, false);
});

test("same-scope revalidation causes zero disruption", async (t) => {
	const app = await workspaceFixture(t, "available");
	await enter(siteInput(), "WORK IN PROGRESS");
	const wrapper = editor().parentElement;
	const scroller = editor();
	scroller.scrollTop = 240;
	const textarea = siteInput();
	const gate = app.startCheck();
	const seen = app.probes();
	Object.defineProperty(document, "visibilityState", {
		value: "visible",
		configurable: true,
	});
	try {
		// focus and visibilitychange both arrive on one tab switch; they must
		// coalesce into a single probe.
		await act(async () => {
			window.dispatchEvent(new window.Event("focus"));
			document.dispatchEvent(new window.Event("visibilitychange"));
		});
		await until(() => app.probes() > seen);
		assert.equal(wrapper.hidden, false);
		assert.equal(wrapper.hasAttribute("inert"), false);
		// The workspace stays interactive while the revalidation is in flight.
		await enter(textarea, "STILL EDITABLE");
		assert.equal(textarea.value, "STILL EDITABLE");
		await act(async () => gate.resolve());
		await act(async () => {
			await new Promise((resolve) => setTimeout(resolve, 5));
		});
		assert.equal(app.probes() - seen, 1);
		// No remount, no flicker, no scroll reset, no status chrome.
		assert.ok(siteInput() === textarea);
		assert.equal(scroller.scrollTop, 240);
		assert.equal(wrapper.hidden, false);
		assert.ok(!document.body.textContent.includes("Opening your workspace"));
		assert.ok(
			!document.body.textContent.includes(
				"Your session could not be rechecked",
			),
		);
		assert.ok(
			!document.body.textContent.includes("Your workspace could not be opened"),
		);
	} finally {
		delete document.visibilityState;
	}
});

test("a confirmed scope change removes content with zero residue", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { useQueryClient } = await import("@tanstack/react-query");
	const oldSession = { ...session, kind: "user" };
	const newSession = { ...oldSession, query_scope: "7".repeat(64) };
	let nextSession = oldSession,
		cache = null,
		renderedScope = null;
	const client = {
		invalidate() {},
		async bootstrap() {
			return nextSession;
		},
		async probeScope() {
			return nextSession.query_scope;
		},
	};
	function Track(props) {
		cache = useQueryClient();
		renderedScope = props.session.query_scope;
		return React.createElement(
			"output",
			null,
			"OWNER " + props.session.query_scope.slice(0, 4),
		);
	}
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(SessionBoundary, { client }, (value) =>
				React.createElement(Track, {
					key: value.query_scope,
					session: value,
				}),
			),
		),
	);
	await until(() => renderedScope === oldSession.query_scope);
	cache.setQueryData([oldSession.query_scope, "secret"], "PRIVATE DATA");
	nextSession = newSession;
	await act(async () => window.dispatchEvent(new window.Event("focus")));
	await until(() => renderedScope === newSession.query_scope);
	const wrapper = fixture.element.querySelector("output").parentElement;
	assert.equal(wrapper.hidden, false);
	assert.equal(wrapper.hasAttribute("inert"), false);
	assert.equal(
		cache.getQueryData([oldSession.query_scope, "secret"]),
		undefined,
	);
	assert.ok(!document.body.textContent.includes("PRIVATE DATA"));
	assert.ok(
		document.body.textContent.includes(
			"OWNER " + newSession.query_scope.slice(0, 4),
		),
	);
});

test("the native site header is measured on resize and before revealing a result", async (t) => {
	let height = 72;
	const observers = new Set();
	const app = await workspaceFixture(t, "available", (fixture) => {
		Object.defineProperty(
			fixture.dom.window.HTMLElement.prototype,
			"offsetHeight",
			{
				configurable: true,
				get() {
					return this.id === "lc-header" ? height : 0;
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
	assert.equal(root.style.getPropertyValue("--sc-header-height"), "72px");
	height = 108;
	for (const observer of observers)
		if ([...observer.targets].some((target) => target.id === "lc-header"))
			observer.callback();
	assert.equal(root.style.getPropertyValue("--sc-header-height"), "108px");
	// An explicit reveal can run before ResizeObserver/effect delivery, as it
	// does while a saved calculation opens after a route reload.
	height = 144;
	root.style.removeProperty("--sc-header-height");
	const target = button("Projects", root);
	let measuredAtScroll;
	target.scrollIntoView = () => {
		measuredAtScroll = [
			root.style.getPropertyValue("--sc-header-height"),
			root.style.getPropertyValue("--sc-navigation-height"),
		];
	};
	const { revealActionResult } =
		await import("../src/components/revealActionResult.ts");
	assert.equal(revealActionResult(target), true);
	assert.deepEqual(measuredAtScroll, ["144px", "0px"]);
	assert.ok(document.activeElement === target);
	assert.equal(target.hasAttribute("tabindex"), false);
	const heading = document.createElement("h3");
	heading.textContent = "Restored planning report";
	root.append(heading);
	heading.scrollIntoView = target.scrollIntoView;
	assert.equal(revealActionResult(heading), true);
	assert.equal(document.activeElement, heading);
	assert.equal(heading.tabIndex, -1);
	assert.equal(heading.classList.contains("sc-focus-target"), true);
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
		async readCreations() {
			return [];
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
							return true;
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
				admittedScope = oldSession.query_scope,
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
				async readCreations() {
					return [];
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
				invalidate() {
					admittedScope = null;
				},
				async bootstrap() {
					admittedScope = nextSession.query_scope;
					return nextSession;
				},
				async probeScope() {
					return nextSession.query_scope;
				},
				isCurrentScope(scope) {
					return scope === admittedScope;
				},
				async query(path) {
					if (path === "recovery/scopes")
						return { schema_version: 1, scopes: [], next: null };
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
				googleMapsApiKey: "fixture-google-maps-key",
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
			await startProjectCreation(oldAck.title);
			await until(() => reached);
			nextSession = newSession;
			await act(async () => window.dispatchEvent(new window.Event("focus")));
			await until(
				() =>
					currentScope === newSession.query_scope &&
					!document.querySelector(".sc-configurator").parentElement.hidden,
			);
			assert.equal(location.search, "?compare=preliminary");
			await act(async () => gate.resolve());
			assert.equal(currentScope, newSession.query_scope);
			assert.equal(location.search, "?compare=preliminary");
			assert.equal(
				cache.getQueryData([oldSession.query_scope, "project", oldAck.id]),
				undefined,
			);
			assert.ok(!document.body.textContent.includes(oldAck.title));
			assert.equal(calls, stage === "write" ? 0 : 1);
		});
});

test("native confirmation fences pending creation, revision and navigation before React commits", async (t) => {
	for (const stage of ["write", "clear", "revise", "close"])
		await t.test(stage, async (t) => {
			const fixture = setupDom();
			history.replaceState(null, "", "/workspace/");
			const { createRoot } = await import("react-dom/client");
			const { SessionBoundary } =
				await import("../src/components/SessionBoundary.tsx");
			const { Workspace } = await import("../src/components/Workspace.tsx");
			const { PlannerClient } = await import("../src/data/PlannerClient.ts");
			const { emptyBrief } = await import("../src/domain/brief.ts");
			const oldSession = { ...session, kind: "user" };
			const newSession = { ...oldSession, query_scope: "9".repeat(64) };
			const gate = deferred();
			const events = [];
			let nextSession = oldSession,
				currentScope,
				cache,
				reached = false,
				calls = 0,
				closing = false,
				editStored = false;
			const oldAck = {
				id: "1".repeat(32),
				title: "OLD OWNER SYNTHETIC PROJECT",
				revision: 1,
				input_sha256: "2".repeat(64),
				inputs: { brief: emptyBrief() },
			};
			const opening = stage === "revise" || stage === "close";
			if (opening)
				history.replaceState(null, "", "/workspace/?project=" + oldAck.id);
			const expectedSearch = location.search;
			const response = (value, status = 200) =>
				new Response(JSON.stringify(value), {
					status,
					headers: { "Content-Type": "application/json" },
				});
			const client = new PlannerClient({
				origin: location.origin,
				baseUrl: location.origin + "/rpc/",
				nonceUrl: location.origin + "/nonce",
				fetch: async (url) => {
					if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
					if (String(url).endsWith("/scope"))
						return response({
							schema_version: 1,
							query_scope: nextSession.query_scope,
						});
					if (String(url).endsWith("/bootstrap")) return response(nextSession);
					if (String(url).endsWith("/recovery/scopes"))
						return response({ schema_version: 1, scopes: [], next: null });
					if (String(url).endsWith("/projects/list"))
						return response({ items: [], next: null });
					if (String(url).endsWith("/projects/read"))
						return nextSession === oldSession
							? response(oldAck)
							: response({ code: "not_found" }, 404);
					assert.ok(/\/projects\/(create|revise)$/.test(String(url)));
					calls++;
					return response(oldAck);
				},
			});
			const store = {
				async read() {
					return null;
				},
				async readProfileImports() {
					return [];
				},
				async candidates() {
					return [];
				},
				async write(_scope, draft) {
					if (
						(stage === "revise" && draft.pending) ||
						(stage === "close" && closing)
					) {
						reached = true;
						await gate.promise;
					} else editStored = true;
				},
				async readCreations() {
					return [];
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
			const config = {
				locale: "en-GB",
				countries: { NO: "Norway" },
				baseUrl: location.origin + "/rpc/",
				nonceUrl: location.origin + "/nonce",
				googleMapsApiKey: "fixture-google-maps-key",
			};
			function Track(props) {
				cache = useQueryClient();
				currentScope = props.session.query_scope;
				if (currentScope === newSession.query_scope)
					events.push("new_scope_render");
				return React.createElement(Workspace, props);
			}
			const root = createRoot(fixture.element);
			t.after(() => {
				globalThis.IS_REACT_ACT_ENVIRONMENT = true;
				return fixture.dispose(root);
			});
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
			if (opening) {
				await until(() => siteInput());
				await enter(siteInput(), "Synthetic local edit");
				await until(() => editStored);
				closing = stage === "close";
				await act(async () =>
					[...document.querySelectorAll("button")]
						.find(
							(button) =>
								button.textContent === (closing ? "Projects" : "Save snapshot"),
						)
						.click(),
				);
			} else {
				await startProjectCreation(oldAck.title);
			}
			await until(() => reached);
			const clear = cache.clear.bind(cache);
			cache.clear = (...args) => {
				assert.equal(client.isCurrentScope(newSession.query_scope), true);
				events.push("new_scope_confirmed");
				const result = clear(...args);
				queueMicrotask(() => {
					events.push("release_old_completion");
					gate.resolve();
				});
				return result;
			};
			const set = cache.setQueryData.bind(cache);
			cache.setQueryData = (key, ...args) => {
				if (key[0] === oldSession.query_scope)
					events.push("old_scope_cache_write");
				return set(key, ...args);
			};
			nextSession = newSession;
			// act would flush React's commit/cleanup before releasing the local
			// promise and hide the real browser-event pre-commit window.
			globalThis.IS_REACT_ACT_ENVIRONMENT = false;
			window.dispatchEvent(new window.Event("focus"));
			for (
				let attempt = 0;
				attempt < 100 && currentScope !== newSession.query_scope;
				attempt++
			)
				await new Promise((resolve) => setTimeout(resolve, 1));
			globalThis.IS_REACT_ACT_ENVIRONMENT = true;
			assert.equal(currentScope, newSession.query_scope);
			assert.ok(
				events.indexOf("new_scope_confirmed") <
					events.indexOf("release_old_completion"),
			);
			assert.ok(
				events.indexOf("release_old_completion") <
					events.indexOf("new_scope_render"),
				JSON.stringify(events),
			);
			assert.ok(!events.includes("old_scope_cache_write"));
			assert.equal(location.search, expectedSearch || "?compare=preliminary");
			assert.equal(
				cache.getQueryData([oldSession.query_scope, "project", oldAck.id]),
				undefined,
			);
			assert.ok(!document.body.textContent.includes(oldAck.title));
			assert.equal(calls, stage === "clear" ? 1 : 0);
			cache.clear = clear;
			cache.setQueryData = set;
			// The race assertions above run before any act flush. Drain the
			// native-event render's remaining effects before disposing its DOM.
			await act(async () => {
				await new Promise((resolve) => setImmediate(resolve));
			});
		});
});

test("a selected project waits for a pending guest claim before reading and opens after settlement", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const project = {
		id: "1".repeat(32),
		title: "Claimed guest project",
		revision: 1,
		input_sha256: "2".repeat(64),
		inputs: { brief: emptyBrief() },
	};
	history.replaceState(null, "", "/workspace/?project=" + project.id);
	let currentSession = { ...session, kind: "user", claim_pending: true },
		readCalls = 0;
	const response = (value, status = 200) =>
		new Response(JSON.stringify(value), {
			status,
			headers: { "Content-Type": "application/json" },
		});
	const client = new PlannerClient({
		origin: location.origin,
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
		fetch: async (url) => {
			if (String(url).endsWith("/nonce")) return new Response("abcdefghij");
			if (String(url).endsWith("/bootstrap")) return response(currentSession);
			if (String(url).endsWith("/recovery/scopes"))
				return response({ schema_version: 1, scopes: [], next: null });
			if (String(url).endsWith("/projects/read")) {
				readCalls++;
				return currentSession.claim_pending
					? response({ code: "not_found" }, 404)
					: response(project);
			}
			return response({ items: [], next: null });
		},
	});
	const store = {
		async read() {
			return null;
		},
		async readProfileImports() {
			return [];
		},
		async candidates() {
			return [];
		},
		async readCreations() {
			return [];
		},
		async write() {},
	};
	const config = {
		locale: "en-GB",
		countries: { NO: "Norway" },
		baseUrl: location.origin + "/rpc/",
		nonceUrl: location.origin + "/nonce",
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
	await until(() =>
		document.body.textContent.includes(
			"Projects from the guest session are still being linked to your account.",
		),
	);
	assert.equal(readCalls, 0);
	currentSession = { ...currentSession, claim_pending: false };
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((button) => button.textContent === "Check session")
			.click(),
	);
	await until(() => siteInput());
	assert.equal(readCalls, 1);
});

test("a creation receipt whose project was deleted is rekeyed and the draft is created", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	// The deleted project's own creation command is the one stored intent.
	const dead = JSON.stringify({
		schema_version: 1,
		title: "Deleted project",
		inputs: { brief: emptyBrief() },
		key: "11111111-1111-4111-8111-111111111111",
	});
	let bodies = [];
	let cleared = [];
	let replacements = [];
	let created = null;
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
			if (String(url).endsWith("/bootstrap"))
				return response({ ...session, kind: "user" });
			if (String(url).endsWith("/operations/replay/projects/create"))
				return response({ error: { code: "not_found" } }, 404);
			bodies.push(JSON.parse(init.body));
			if (bodies.length === 1)
				return response({ error: { code: "not_found" } }, 404);
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
	const records = [
		{
			key: "11111111-1111-4111-8111-111111111111",
			title: "Deleted project",
			body: dead,
			destination: null,
			createdAt: 1,
		},
	];
	const store = {
		async readCreations() {
			return records;
		},
		async writeCreation() {},
		async replaceCreation(scope, oldBody, body, destination) {
			const index = records.findIndex((record) => record.body === oldBody);
			if (index < 0) throw new Error("creation_intent_not_found");
			records[index] = {
				key: JSON.parse(body).key,
				title: JSON.parse(body).title,
				body,
				destination,
				createdAt: records[index].createdAt,
			};
			replacements.push([scope, oldBody, body, destination]);
		},
		async clearCreation(scope, body) {
			cleared.push(body);
		},
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
							return true;
						},
					}),
				),
			),
		),
	);
	await until(() => document.querySelector("form"));
	const submit = () =>
		act(async () =>
			document
				.querySelector("form")
				.dispatchEvent(
					new window.Event("submit", { bubbles: true, cancelable: true }),
				),
		);
	await submit();
	await until(() =>
		document.body.textContent.includes(
			"The project this request belonged to was deleted.",
		),
	);
	// The dead receipt is replaced in browser storage; the draft survives a reload.
	assert.deepEqual(cleared, []);
	assert.equal(records.length, 1);
	assert.notEqual(records[0].body, dead);
	assert.equal(records[0].title, "Deleted project");
	assert.equal(records[0].createdAt, 1);
	assert.equal(document.querySelector("input").value, "Deleted project");
	await submit();
	await until(() => created !== null);
	assert.equal(bodies.length, 2);
	assert.equal(bodies[1].title, "Deleted project");
	assert.deepEqual(bodies[1].inputs, { brief: emptyBrief() });
	assert.notEqual(bodies[1].key, "11111111-1111-4111-8111-111111111111");
	assert.deepEqual(replacements, [
		[session.query_scope, dead, records[0].body, null],
	]);
	assert.deepEqual(cleared, [records[0].body]);
});

test("an unknown creation 404 stays a retry failure instead of rekeying a live receipt", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { PlannerClient } = await import("../src/data/PlannerClient.ts");
	const dead = JSON.stringify({
		schema_version: 1,
		title: "Live project",
		inputs: { brief: emptyBrief() },
		key: "44444444-4444-4444-8444-444444444444",
	});
	const records = [
		{
			key: "44444444-4444-4444-8444-444444444444",
			title: "Live project",
			body: dead,
			destination: null,
			createdAt: 1,
		},
	];
	const sent = [];
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
			if (String(url).endsWith("/bootstrap"))
				return response({ ...session, kind: "user" });
			if (String(url).endsWith("/operations/replay/projects/create"))
				return response({ error: { code: "not_found" } }, 404);
			sent.push(JSON.parse(String(init.body)));
			return response({ error: { code: "route_missing" } }, 404);
		},
	});
	const store = {
		async readCreations() {
			return records;
		},
		async writeCreation() {},
		async replaceCreation() {
			throw new Error("creation_intent_must_not_be_replaced");
		},
		async clearCreation() {
			throw new Error("creation_intent_must_not_be_cleared");
		},
	};
	await client.bootstrap();
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(
					React.StrictMode,
					null,
					React.createElement(SessionBoundary, { client }, (value) =>
						React.createElement(NewProject, {
							session: value,
							client,
							store,
							recheck: () => assert.fail("unexpected identity failure"),
							created: () => assert.fail("creation must not succeed"),
						}),
					),
				),
			),
		),
	);
	await until(() => document.querySelector("form"));
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	await until(() =>
		document.body.textContent.includes(
			"Project creation was not confirmed. Retrying uses the same request.",
		),
	);
	assert.equal(records[0].body, dead);
	assert.equal(sent.length, 1);
	assert.equal(
		document.body.textContent.includes(
			"The project this request belonged to was deleted.",
		),
		false,
	);
});
