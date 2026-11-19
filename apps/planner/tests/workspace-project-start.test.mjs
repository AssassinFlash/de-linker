import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { setupDom, until, enter } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

const projectId = "7".repeat(32);
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

test("project setup retains entered information when the saved-project index refreshes", async (t) => {
	const fixture = setupDom();
	// The shared fixture opens a project from its URL; this test starts at the
	// empty index, which is where the one-screen start lives.
	window.history.replaceState({}, "", "/workspace/");
	const globals = new Map();
	for (const [name, value] of Object.entries({
		MutationObserver: window.MutationObserver,
		getComputedStyle: window.getComputedStyle.bind(window),
		requestAnimationFrame: (callback) =>
			setTimeout(() => callback(Date.now()), 0),
		cancelAnimationFrame: clearTimeout,
	})) {
		globals.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value,
			configurable: true,
			writable: true,
		});
	}
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { Workspace } = await import("../src/components/Workspace.tsx");

	let listed = [];
	const creates = [];
	let accepted;
	const client = {
		async send(path, body) {
			assert.equal(path, "projects/create");
			creates.push(body);
			const command = JSON.parse(body);
			accepted = {
				id: projectId,
				revision: 1,
				title: command.title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
			return accepted;
		},
		invalidate() {},
		async bootstrap() {
			return session;
		},
		async probeScope() {
			return session.query_scope;
		},
		isCurrentScope(scope) {
			return scope === session.query_scope;
		},
		async query(path) {
			if (path === "projects/list")
				return { schema_version: 1, items: listed, next: null };
			throw new Error("unexpected command " + path);
		},
	};
	const store = {
		async writeCreation() {},
		async clearCreation() {},
		async readCreations() {
			return [];
		},
		async read() {
			return null;
		},
		async readProfileImports() {
			return [];
		},
		async candidates() {
			return [];
		},
		async write() {},
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
		for (const [name, descriptor] of globals) {
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
	const start = () => document.querySelector("form");
	await until(() => document.querySelector('select[name="system_scope"]'));
	await act(async () => {
		const scope = document.querySelector('select[name="system_scope"]');
		scope.value = "storage_only";
		scope.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await enter(
		document.querySelector('input[name="project_title"]'),
		"Oslo storage",
	);

	listed = [
		{
			id: projectId,
			title: "Residential · 10 kWp · 10115 Berlin",
			revision: 1,
			input_sha256: "8".repeat(64),
			updated_at: 1763200000,
		},
	];
	const refresh = () =>
		[...document.querySelectorAll("button")].find(
			(button) => button.getAttribute("aria-label") === "Refresh projects",
		);
	await act(async () => refresh().click());
	await until(
		() => document.querySelectorAll('[role="listitem"]').length === 1,
	);
	assert.ok(start());
	assert.equal(
		document.querySelector('input[name="project_title"]').value,
		"Oslo storage",
	);
	assert.equal(
		document.querySelector('select[name="system_scope"]').value,
		"storage_only",
	);
	const purpose = document.querySelector('select[name="project_purpose"]');
	assert.ok(purpose, "purpose belongs to the initial Project page");
	await act(async () => {
		purpose.value = "backup";
		purpose.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	const next = [...document.querySelectorAll("button")].find(
		(item) => item.textContent === "Continue with storage",
	);
	await act(async () => {
		next.click();
		next.click();
	});
	await until(() => location.hash === "#sc-energy");
	assert.equal(creates.length, 1);
	assert.equal(accepted.inputs.backup_demand.load_kw, null);
	assert.equal(accepted.title, "Oslo storage");
	await until(() =>
		document.body.textContent.includes("What should the system do?"),
	);
});

test("the first-visit entry compares directions and opens the native inquiry for the choice", async (t) => {
	const fixture = setupDom();
	window.history.replaceState({}, "", "/workspace/#sc-preliminary-options");
	document.querySelector("header").innerHTML =
		'<a hreflang="de" lang="de" href="/de/workspace/">Deutsch</a>';
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const root = createRoot(fixture.element);
	const style = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	const cache = new QueryClient();
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
		if (style) Object.defineProperty(globalThis, "getComputedStyle", style);
		else delete globalThis.getComputedStyle;
	});
	const created = [];
	const revisions = [];
	const previews = [];
	let accepted;
	let missed = false;
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			if (path === "projects/list")
				return { schema_version: 1, items: [], next: null };
			if (path === "projects/read") return accepted;
			assert.equal(path, "inquiry/form");
			previews.push(command);
			return {
				schema_version: 1,
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php">
					<input type="hidden" name="linker_preliminary_project" value="${projectId}:${command.revision}">
					<input name="name" required><input name="email" type="email" required>
					<input name="company"><textarea name="message"></textarea>
					<input name="consent" type="checkbox" required><button>Send inquiry</button>
				</form>`,
				inquiry_lines: [],
			};
		},
		async send(path, body) {
			const command = JSON.parse(body);
			if (path === "projects/revise") {
				revisions.push(command);
				accepted = { ...accepted, revision: 2, inputs: command.inputs };
				return accepted;
			}
			assert.equal(path, "projects/create");
			created.push(command);
			accepted = {
				id: projectId,
				revision: 1,
				title: command.title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
			if (!missed) {
				missed = true;
				throw new Error("Creation reply lost");
			}
			return accepted;
		},
	};
	const store = {
		async readCreations() {
			return [];
		},
		async writeCreation() {},
		async clearCreation() {},
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async write() {},
	};
	const render = (locale) =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Workspace, {
						session,
						client,
						store,
						config: {
							baseUrl: location.origin + "/api/",
							nonceUrl: "",
							locale,
							countries: {},
						},
						recheck() {},
					}),
				),
			),
		);
	await render("en");
	const language = document.querySelector('a[hreflang="de"]');
	assert.equal(language.hash, "#sc-preliminary-options");
	const direction = () =>
		Array.from(fixture.element.querySelectorAll("article")).find(
			(card) =>
				card.querySelector("h3")?.textContent === "Storage for existing PV",
		);
	await until(() => direction()?.querySelector("button:not(:disabled)"));
	assert.equal(
		fixture.element.querySelector('input[name="project_title"]'),
		null,
	);
	assert.deepEqual(created, []);
	await act(async () => direction().querySelector("button").click());
	const button = (label) =>
		Array.from(fixture.element.querySelectorAll("button")).find(
			(item) => item.textContent.trim() === label,
		);
	await until(() => button("Retry project creation"));
	await act(async () => button("Retry project creation").click());
	await until(() => fixture.element.querySelector("form.linker-inquiry-form"));
	assert.equal(created.length, 2);
	assert.deepEqual(created[0], created[1]);
	assert.deepEqual(Object.keys(created[0].inputs), ["brief"]);
	assert.equal(created[0].inputs.brief.system_scope, "storage_addition");
	assert.equal(created[0].inputs.brief.site.country_code, null);
	assert.equal(created[0].inputs.brief.annual_load.kwh, null);
	assert.deepEqual(previews, [
		{ schema_version: 1, lang: "en", project_id: projectId, revision: 1 },
	]);
	assert.match(
		fixture.element.querySelector(".sc-draft-transfer").textContent,
		/Storage for existing PV/,
	);
	assert.equal(
		fixture.element.querySelector('[name="linker_preliminary_project"]').value,
		projectId + ":1",
	);
	assert.equal(
		fixture.element.querySelector("form").getAttribute("action"),
		"/wp-admin/admin-post.php",
	);
	assert.equal(location.hash, "#sc-preliminary-review");

	await enter(
		fixture.element.querySelector('[name="message"]'),
		"Can you help size a battery?",
	);
	await act(async () =>
		fixture.element.querySelector('[name="consent"]').click(),
	);
	await act(async () => history.back());
	await until(() => location.hash === "#sc-preliminary-options" && direction());
	assert.equal(location.search, "?project=" + projectId);
	await act(async () => history.forward());
	await until(
		() =>
			location.hash === "#sc-preliminary-review" &&
			fixture.element.querySelector("#sc-preliminary-review:not([hidden])"),
	);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Can you help size a battery?",
	);
	await act(async () => button("Change selection").click());
	const storage = () =>
		Array.from(fixture.element.querySelectorAll("article")).find(
			(card) => card.querySelector("h3")?.textContent === "Storage",
		);
	await until(() => storage()?.querySelector("button:not(:disabled)"));
	await act(async () => storage().querySelector("button").click());
	await until(
		() =>
			location.hash === "#sc-preliminary-review" &&
			fixture.element.querySelector('[name="linker_preliminary_project"]')
				?.value ===
				projectId + ":2",
	);
	assert.equal(created.length, 2);
	assert.equal(revisions.length, 1);
	assert.equal(revisions[0].project_id, projectId);
	assert.equal(revisions[0].expected_revision, 1);
	assert.equal(revisions[0].inputs.brief.system_scope, "storage_only");
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Can you help size a battery?",
	);
	assert.equal(fixture.element.querySelector('[name="consent"]').checked, true);

	const move = new window.MouseEvent("click", {
		bubbles: true,
		cancelable: true,
		button: 0,
	});
	document.addEventListener(
		"click",
		(event) => {
			if (event.target !== language) return;
			assert.equal(event.defaultPrevented, false);
			event.preventDefault(); // JSDOM does not support navigation.
		},
		{ once: true },
	);
	await act(async () => language.dispatchEvent(move));
	assert.equal(language.search, "?project=" + projectId);
	assert.equal(language.hash, "#sc-preliminary-review");
	window.history.replaceState(null, "", language.href);
	await act(async () => root.render(null));
	await render("de");
	await until(
		() =>
			previews.at(-1)?.lang === "de" &&
			fixture.element.querySelector("form.linker-inquiry-form"),
	);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Can you help size a battery?",
	);
	assert.equal(fixture.element.querySelector('[name="consent"]').checked, true);
});
