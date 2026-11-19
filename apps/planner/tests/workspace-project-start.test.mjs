import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
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

test("the home form creates a comparison with the supplied data in a single submit", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const commands = [];
	const opened = [];
	const client = {
		invalidate() {},
		async bootstrap() {
			return session;
		},
		isCurrentScope: (scope) => scope === session.query_scope,
		async send(path, body) {
			assert.equal(path, "projects/create");
			const command = JSON.parse(body);
			commands.push(command);
			return {
				id: projectId,
				revision: 1,
				title: command.title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
		},
		async query() {
			throw new Error("The test user does not select hardware.");
		},
	};
	const store = {
		async readCreations() {
			return [];
		},
		async writeCreation(_, _body, destination) {
			assert.equal(destination, "guided-comparison");
		},
		async clearCreation() {},
	};
	const root = createRoot(fixture.element);
	t.after(async () => fixture.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(SessionBoundary, { client }, (value, recheck) =>
				React.createElement(NewProject, {
					session: value,
					client,
					store,
					recheck,
					openOnLoad: true,
					config: { locale: "en", countries: { DE: "Germany" } },
					homeComparison: { picker: null, savedProject: "", compareSaved() {} },
					created: (project, destination) => {
						opened.push([project.id, destination]);
						return true;
					},
				}),
			),
		),
	);
	const findForm = () =>
		document.querySelector('form[aria-label="Compare project options"]');
	await until(findForm);
	const form = findForm();
	const title = form.querySelector('[name="project_title"]');
	await until(() => !title.disabled && !title.closest("fieldset").disabled);
	function field(name) {
		return form.querySelector('[name="' + name + '"]');
	}
	async function select(name, value) {
		await act(async () => {
			const input = field(name);
			input.value = value;
			input.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	await enter(title, "Berlin workshop");
	await select("country", "DE");
	await select("system_scope", "new_pv_storage");
	await select("project_purpose", "backup");
	await select("grid_phase", "3");
	await enter(field("annual_load_kwh"), "7200");
	await select("annual_load_basis", "bill_total");
	await enter(field("pv_dc_kw"), "8");
	await act(async () => field("estimate_solar").click());
	await enter(field("latitude"), "47.66");
	await enter(field("longitude"), "9.17");
	await enter(field("pv_tilt_deg"), "32");
	await enter(field("pv_azimuth_deg"), "180");
	await enter(field("pvgis_year"), "2020");
	await enter(field("pvgis_loss_percent"), "14");
	await select("pvgis_database", "PVGIS-SARAH3");
	await select("pvgis_technology", "crystSi");
	await select("pvgis_mounting", "free");
	await select("pvgis_horizon", "true");
	await enter(field("pvgis_source"), "Surveyed customer array");
	await enter(field("backup_load_kw"), "3");
	await enter(field("backup_duration_hours"), "2");
	assert.equal(commands.length, 0);
	const submit = form.querySelector('button[type="submit"]');
	assert.equal(submit.textContent.trim(), "Compare systems");
	await act(async () => submit.click());
	await until(() => opened.length === 1);
	assert.equal(commands.length, 1);
	assert.equal(commands[0].inputs.brief.site.country_code, "DE");
	assert.equal(commands[0].inputs.equipment_setup.grid_phase, 3);
	assert.equal(commands[0].inputs.brief.annual_load.kwh, 7200);
	assert.equal(commands[0].inputs.brief.annual_load.basis, "bill_total");
	assert.equal(commands[0].inputs.brief.site.coordinate_basis, "user_entered");
	assert.deepEqual(commands[0].inputs.pvgis_reference.arrays[0], {
		id: "declared-array",
		peak_power_kwp: 8,
		tilt_deg: 32,
		azimuth_north_clockwise_deg: 180,
		source_note: "Surveyed customer array",
	});
	assert.deepEqual(commands[0].inputs.backup_demand, {
		schema_version: 1,
		load_kw: 3,
		duration_hours: 2,
	});
	assert.deepEqual(opened, [[projectId, "guided-comparison"]]);
});

test("visitors with project data can open setup from the comparison and keep their inputs during an index refresh", async (t) => {
	const fixture = setupDom();
	window.history.replaceState(
		{},
		"",
		"/workspace/?plz=0150#sc-preliminary-options",
	);
	document.querySelector("header").innerHTML =
		'<a hreflang="de" lang="de" href="/de/workspace/">Deutsch</a>';
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
	const createResponse = Promise.withResolvers();
	const client = {
		async send(path, body) {
			assert.equal(path, "projects/create");
			creates.push(body);
			await createResponse.promise;
			const command = JSON.parse(body);
			accepted = {
				id: projectId,
				revision: 1,
				title: command.title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
			listed = [{ ...accepted, updated_at: 1763200000 }];
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
	const setup = () =>
		[...document.querySelectorAll("button")].find(
			(button) => button.textContent.trim() === "Enter project details",
		);
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.ok(
		setup(),
		"Known project details can lead directly to the project form",
	);
	await until(() => !setup().disabled);
	await act(async () => setup().click());
	await until(() => document.querySelector('select[name="system_scope"]'));
	assert.equal(location.hash, "#sc-project");
	assert.equal(document.activeElement.textContent, "What is the project?");
	assert.equal(new URL(location.href).searchParams.get("project"), null);
	assert.equal(new URL(location.href).searchParams.get("plz"), "0150");
	assert.equal(document.querySelector('a[hreflang="de"]').hash, "#sc-project");
	assert.deepEqual(creates, []);
	await act(async () => {
		const scope = document.querySelector('select[name="system_scope"]');
		scope.value = "storage_only";
		scope.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await enter(
		document.querySelector('input[name="project_title"]'),
		"Oslo storage",
	);
	await enter(
		document.querySelector('input[name="location_label"]'),
		"Oslo 0150",
	);
	await act(async () => history.back());
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.equal(
		Boolean(document.querySelector('input[name="project_title"]')),
		false,
	);
	assert.equal(document.activeElement.textContent, "Preliminary options");
	await act(async () => history.forward());
	await until(() => document.querySelector('input[name="project_title"]'));
	assert.equal(document.activeElement.textContent, "What is the project?");
	assert.equal(
		document.querySelector('input[name="project_title"]').value,
		"Oslo storage",
	);
	assert.equal(
		document.querySelector('input[name="location_label"]').value,
		"Oslo 0150",
	);
	assert.deepEqual(creates, []);

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
	await until(() => creates.length === 1);
	try {
		await act(async () => history.back());
		const option = () =>
			document.querySelector(
				'table[aria-label="Compare system options"] tbody button',
			);
		await until(
			() =>
				option() &&
				(option().disabled || location.hash === "#sc-preliminary-options"),
		);
		assert.equal(
			option().disabled,
			true,
			"One app session is already creating a project",
		);
		await act(async () => option().click());
		assert.equal(creates.length, 1);
		await act(async () =>
			[...document.querySelectorAll("button")]
				.find((button) => button.textContent.trim() === "Projects")
				.click(),
		);
		assert.equal(location.hash, "");
	} finally {
		await act(async () => createResponse.resolve());
	}
	await until(() => accepted);
	assert.equal(accepted.inputs.backup_demand.load_kw, null);
	assert.equal(accepted.title, "Oslo storage");
	assert.equal(location.hash, "");
	assert.equal(new URL(location.href).searchParams.has("project"), false);
	await until(() =>
		document
			.querySelector('[role="listitem"]')
			?.textContent.includes("Oslo storage"),
	);
});

test("the first-visit entry compares directions and opens the native inquiry for the choice", async (t) => {
	const fixture = setupDom();
	globalThis.indexedDB = new IDBFactory();
	t.after(() => delete globalThis.indexedDB);
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
	let stored = null;
	let missed = false;
	let confirmRevision = null;
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			if (path === "projects/list")
				return { schema_version: 1, items: [], next: null };
			if (path === "projects/read") return accepted;
			if (path === "projects/runs")
				return { schema_version: 1, items: [], next: null };
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
				if (confirmRevision && (await confirmRevision))
					throw new Error("Revision reply lost");
				assert.equal(command.expected_revision, accepted.revision);
				accepted = {
					...accepted,
					revision: accepted.revision + 1,
					inputs: command.inputs,
				};
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
			return stored;
		},
		async candidates() {
			return [];
		},
		async write(_scope, draft) {
			stored = structuredClone(draft);
		},
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
	const comparison = fixture.element.querySelector(
		'table[aria-label="Compare system options"]',
	);
	assert.ok(comparison, "Options belong in one project comparison table");
	assert.deepEqual(
		Array.from(comparison.querySelectorAll("tbody th")).map((cell) =>
			cell.textContent.trim(),
		),
		["Solar and storage", "Storage for existing PV", "Solar", "Storage"],
	);
	const direction = () =>
		Array.from(fixture.element.querySelectorAll("tbody tr")).find(
			(row) =>
				row.querySelector("th")?.textContent === "Storage for existing PV",
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
			fixture.element.querySelector(".sc-draft-transfer:not([hidden])"),
	);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Can you help size a battery?",
	);
	await act(async () => button("Change selection").click());
	const storage = () =>
		Array.from(fixture.element.querySelectorAll("tbody tr")).find(
			(row) => row.querySelector("th")?.textContent === "Storage",
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

	await enter(
		fixture.element.querySelector('[name="message"]'),
		"Frage aus der deutschen Ansicht",
	);
	await act(async () =>
		fixture.element.querySelector('[name="consent"]').click(),
	);
	await act(async () =>
		window.dispatchEvent(
			new window.PageTransitionEvent("pagehide", { persisted: false }),
		),
	);
	window.history.replaceState(
		null,
		"",
		"/workspace/?project=" + projectId + "#sc-preliminary-review",
	);
	await act(async () => root.render(null));
	await render("en");
	await until(
		() =>
			previews.at(-1)?.lang === "en" &&
			fixture.element.querySelector("form.linker-inquiry-form"),
	);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Frage aus der deutschen Ansicht",
	);
	assert.equal(
		fixture.element.querySelector('[name="consent"]').checked,
		false,
	);
	assert.equal(created[0].title, "New project");
	const refine = button("Enter project details");
	assert.ok(refine, "The selected direction can lead into the same project");
	await until(() => !button("Enter project details").disabled);
	await act(async () => refine.click());
	await until(() => document.body.textContent.includes("What is the project?"));
	assert.equal(document.activeElement.textContent, "What is the project?");
	assert.equal(
		document.querySelector('select[name="system_scope"]')?.value,
		"storage_only",
	);
	assert.equal(location.hash, "#sc-project");
	assert.equal(location.search, "?project=" + projectId);
	assert.equal(created.length, 2, "No additional creation request was sent");
	assert.equal(revisions.length, 1, "Opening setup did not revise the project");
	accepted = {
		...accepted,
		revision: 3,
		inputs: {
			...accepted.inputs,
			brief: { ...accepted.inputs.brief, system_scope: "pv_only" },
		},
	};
	await act(async () => history.back());
	await until(() => fixture.element.querySelector("form.linker-inquiry-form"));
	assert.equal(location.hash, "#sc-preliminary-review");
	assert.equal(
		fixture.element.querySelector('[name="linker_preliminary_project"]').value,
		projectId + ":3",
	);
	assert.match(
		fixture.element.querySelector(".linker-inquiry-draft").textContent,
		/Planned system: Solar/,
	);
	assert.equal(previews.at(-1)?.revision, 3);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Frage aus der deutschen Ansicht",
	);
	await until(
		() =>
			!button("Enter project details")?.disabled &&
			button("Enter project details"),
	);
	await act(async () => button("Enter project details").click());
	const site = () => document.querySelector('input[name="location_label"]');
	await until(() => site() && !site().closest("fieldset").disabled);
	await enter(site(), "Berlin 10115");
	assert.equal(site().value, "Berlin 10115");
	const pendingRevision = Promise.withResolvers();
	confirmRevision = pendingRevision.promise;
	try {
		await act(async () => history.back());
		await until(() => revisions.length === 2);
		assert.equal(revisions[1].expected_revision, 3);
		assert.equal(revisions[1].inputs.brief.site.location_label, "Berlin 10115");
		assert.equal(
			Boolean(fixture.element.querySelector("form.linker-inquiry-form")),
			false,
		);
		assert.equal(
			previews.at(-1)?.revision,
			3,
			"Do not request Woo form before the site edit is confirmed",
		);
	} finally {
		pendingRevision.resolve(true);
	}
	await until(() => button("Retry save"));
	assert.equal(revisions.length, 2);
	assert.equal(
		Boolean(fixture.element.querySelector("form.linker-inquiry-form")),
		false,
	);
	confirmRevision = null;
	await act(async () => button("Retry save").click());
	await until(() => fixture.element.querySelector("form.linker-inquiry-form"));
	assert.deepEqual(
		revisions[2],
		revisions[1],
		"Retry the same frozen revise request",
	);
	assert.equal(previews.at(-1)?.revision, 4);
	assert.equal(
		fixture.element.querySelector('[name="linker_preliminary_project"]').value,
		projectId + ":4",
	);
	assert.equal(
		fixture.element.querySelector('[name="message"]').value,
		"Frage aus der deutschen Ansicht",
	);
});

test("signed-in preliminary landing explains a failed recovery read and offers a retry", async (t) => {
	const fixture = setupDom();
	history.replaceState(null, "", "/workspace/#sc-preliminary-options");
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const root = createRoot(fixture.element);
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const style = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
		if (style) Object.defineProperty(globalThis, "getComputedStyle", style);
		else delete globalThis.getComputedStyle;
	});
	let recoveries = 0;
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path) {
			if (path === "projects/list")
				return { schema_version: 1, items: [], next: null };
			assert.equal(path, "recovery/scopes");
			if (++recoveries === 1) throw new Error("Recovery scope unavailable");
			return { schema_version: 1, scopes: [], next: null };
		},
	};
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Workspace, {
					session: { ...session, kind: "user" },
					client,
					store: {
						async readCreations() {
							return [];
						},
					},
					config: {
						baseUrl: location.origin + "/api/",
						nonceUrl: "",
						locale: "en",
						countries: {},
					},
					recheck: () => assert.fail("Unexpected scope invalidation"),
				}),
			),
		),
	);
	const retry = () =>
		Array.from(fixture.element.querySelectorAll("button")).find(
			(button) => button.textContent === "Try again",
		);
	await until(retry);
	assert.match(
		fixture.element.textContent,
		/creations and CSV imports from earlier sessions could not be checked/,
	);
	assert.equal(fixture.element.querySelector("tbody button").disabled, true);
	await act(async () => retry().click());
	await until(() => !fixture.element.querySelector("tbody button").disabled);
	assert.equal(recoveries, 2);
	assert.equal(retry(), undefined);
});

test("the review restores edited signed-in details and Woo billing controls on a language return", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ReviewInquiry } =
		await import("../src/components/configurator/ReviewInquiry.tsx");
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const opens = [];
	const project = { id: projectId, revision: 1 };
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			assert.equal(path, "inquiry/form");
			opens.push(command.lang);
			return {
				schema_version: 1,
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php">
					<input type="hidden" name="linker_preliminary_project" value="${projectId}:1">
					<details class="linker-inquiry-details">
						<summary><span>Your reply details <small>Original Name · old@example.test</small></span></summary>
						<input name="name" value="Original Name"><input name="email" value="old@example.test">
						<input name="billing_city" value="Berlin"><select name="billing_country">
							<option value="DE" selected>Germany</option><option value="NL">Netherlands</option>
						</select>
					</details>
					<button type="submit">Send inquiry</button>
				</form>`,
				inquiry_lines: [],
			};
		},
	};
	const render = (locale) =>
		act(async () =>
			root.render(
				React.createElement(ReviewInquiry, {
					project,
					direction: "storage_only",
					client,
					locale,
					active: true,
					scope: session.query_scope,
					changeSelection() {},
					recheck() {},
				}),
			),
		);
	const details = () => fixture.element.querySelector("details");
	const field = (name) => fixture.element.querySelector(`[name="${name}"]`);
	await render("en");
	await until(details);
	assert.equal(details().open, false);
	await act(async () => {
		details().open = true;
	});
	await enter(field("name"), "Updated Name");
	await enter(field("email"), "new@example.test");
	await enter(field("billing_city"), "Amsterdam");
	await act(async () => {
		field("billing_country").value = "NL";
		field("billing_country").dispatchEvent(
			new window.Event("change", { bubbles: true }),
		);
		window.dispatchEvent(
			new window.PageTransitionEvent("pagehide", { persisted: true }),
		);
	});
	await act(async () => root.render(null));
	await render("de");
	await until(() => opens.at(-1) === "de" && details());
	assert.equal(details().open, true);
	assert.equal(
		details().querySelector("small").textContent,
		"Updated Name · new@example.test",
	);
	assert.equal(field("billing_city").value, "Amsterdam");
	assert.equal(field("billing_country").value, "NL");
	assert.equal(field("linker_preliminary_project").value, projectId + ":1");

	const reads = opens.length;
	await act(async () =>
		window.dispatchEvent(
			new window.PageTransitionEvent("pagehide", { persisted: true }),
		),
	);
	assert.equal(details(), null); // Cached pages keep no editable DOM before the ownership check.
	await act(async () =>
		window.dispatchEvent(
			new window.PageTransitionEvent("pageshow", { persisted: true }),
		),
	);
	await until(() => opens.length === reads + 1 && details());
	assert.equal(field("billing_country").value, "NL");
	assert.equal(field("name").value, "Updated Name");
});

async function lostReceipt(
	t,
	storageAllowed,
	replaySeconds = 86400,
	expired = false,
) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ReviewInquiry } =
		await import("../src/components/configurator/ReviewInquiry.tsx");
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const requestIds = [
		crypto.randomUUID(),
		crypto.randomUUID(),
		crypto.randomUUID(),
	];
	const project = { id: projectId, revision: 7 };
	if (!storageAllowed)
		Object.defineProperty(window, "sessionStorage", {
			get: () => {
				throw new window.DOMException("Storage unavailable", "SecurityError");
			},
		});
	let loads = 0;
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			assert.equal(path, "inquiry/form");
			assert.equal(command.project_id, projectId);
			assert.equal(command.revision, 7);
			const n = loads++;
			return {
				schema_version: 1,
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php" data-linker-inquiry-replay-seconds="${replaySeconds}">
					<input type="hidden" name="linker_preliminary_project" value="${projectId}:7">
					<input type="hidden" name="linker_request_id" value="${requestIds[n]}" data-linker-protected-action="inquiry">
					<input type="hidden" name="linker_draft_hash" value="${n ? "" : "original-cart"}">
					<input type="hidden" name="lang" value="en">
					<input type="hidden" name="linker_proof" value="${n ? "" : "fixture-old-proof"}">
					<input type="hidden" name="linker_inquiry_nonce" value="current-nonce-${n}">
					${n ? "" : '<input type="hidden" name="linker_project_notes_present" value="1"><input type="hidden" name="linker_project_note_revisions[project_source]" value="old-note-revision">'}
					<input name="name" required><input name="email" type="email" required>
					<textarea name="message"></textarea><input name="consent" type="checkbox" value="1" required>
					<button type="submit">Send inquiry</button>
				</form>`,
				inquiry_lines: [],
			};
		},
	};
	await act(async () =>
		root.render(
			React.createElement(ReviewInquiry, {
				project,
				direction: "storage_only",
				client,
				locale: "en",
				active: true,
				scope: session.query_scope,
				changeSelection() {},
				enterDetails() {
					assert.fail("A pending inquiry must stay on the review");
				},
				recheck() {},
			}),
		),
	);
	const form = () => fixture.element.querySelector("form.linker-inquiry-form");
	const field = (name) => form().elements.namedItem(name);
	await until(form);
	await enter(field("name"), "Test Visitor");
	await enter(field("email"), "visitor@example.test");
	await enter(field("message"), "Can you help size a battery?");
	await act(async () => field("consent").click());
	const original = new window.FormData(form());
	assert.equal(original.has("linker_inquiry_receipt_only"), false);
	await act(async () => {
		assert.equal(
			form().dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
			true,
		);
		window.dispatchEvent(
			new window.PageTransitionEvent("pagehide", { persisted: true }),
		);
	});
	assert.equal(form(), null);
	if (expired) {
		const previous = Date.now;
		const afterWindow = previous() + replaySeconds * 1000 + 1;
		Date.now = () => afterWindow;
		t.after(() => {
			Date.now = previous;
		});
	}
	await act(async () =>
		window.dispatchEvent(
			new window.PageTransitionEvent("pageshow", { persisted: true }),
		),
	);
	const pendingKey =
		"linker-preliminary-inquiry-pending:" +
		session.query_scope +
		":" +
		projectId +
		":7";
	if (expired) {
		await until(() =>
			fixture.element.textContent.includes(
				"We could not confirm whether your inquiry was received.",
			),
		);
		assert.equal(form(), null);
		assert.deepEqual(
			Object.keys(JSON.parse(window.sessionStorage.getItem(pendingKey))).sort(),
			["expiresAt", "requestId"],
		);
		return;
	}
	await until(() => loads === 2 && form());
	if (!replaySeconds) {
		assert.equal(field("linker_request_id").value, requestIds[1]);
		assert.equal(window.sessionStorage.getItem(pendingKey), null);
		return;
	}
	assert.equal(
		form().querySelector('button[type="submit"]').textContent,
		"Check inquiry status",
	);
	assert.equal(
		field("linker_request_id").dataset.linkerProtectionRecovery,
		"true",
	);
	assert.equal(
		fixture.element.querySelector(".sc-draft-transfer aside button").disabled,
		true,
	);
	assert.equal(
		[...fixture.element.querySelectorAll("button")].find(
			(button) => button.textContent.trim() === "Enter project details",
		)?.disabled,
		true,
	);
	const replay = new window.FormData(form());
	assert.deepEqual(replay.getAll("linker_inquiry_receipt_only"), ["1"]);
	for (const key of [
		"linker_request_id",
		"linker_preliminary_project",
		"linker_draft_hash",
		"linker_project_notes_present",
		"linker_project_note_revisions[project_source]",
		"name",
		"email",
		"message",
		"consent",
		"lang",
	])
		assert.equal(replay.get(key), original.get(key), key);
	assert.equal(replay.get("linker_inquiry_nonce"), "current-nonce-1");
	assert.equal(replay.get("linker_proof"), "");

	if (!storageAllowed) return;

	// Account keeps unresolved requests. A confirmed receipt retires only its own.
	const otherRequest = crypto.randomUUID();
	const otherKey = "linker-preliminary-inquiry-pending:unrelated";
	window.sessionStorage.setItem(
		otherKey,
		JSON.stringify({ requestId: otherRequest }),
	);

	const { readFileSync } = await import("node:fs");
	const accountUi = readFileSync(
		new URL(
			"../../../plugins/linker-commerce/assets/account-ui.js",
			import.meta.url,
		),
		"utf8",
	);
	const attachAccountUi = new Function("window", "document", accountUi);
	document
		.querySelector("header")
		.insertAdjacentHTML(
			"afterend",
			'<section class="linker-account">Account</section>',
		);
	attachAccountUi(window, document);
	assert.ok(window.sessionStorage.getItem(otherKey));
	assert.ok(
		window.sessionStorage.getItem(
			"linker-preliminary-inquiry-pending:" +
				session.query_scope +
				":" +
				projectId +
				":7",
		),
	);
	document.querySelector(".linker-account").remove();
	document
		.querySelector("header")
		.insertAdjacentHTML(
			"afterend",
			`<section class="linker-inquiry-success" data-linker-received-request="${requestIds[0]}" role="status">Inquiry received</section>`,
		);
	attachAccountUi(window, document);
	assert.ok(window.sessionStorage.getItem(otherKey));
	await act(async () => {
		window.dispatchEvent(
			new window.PageTransitionEvent("pagehide", { persisted: true }),
		);
		window.dispatchEvent(
			new window.PageTransitionEvent("pageshow", { persisted: true }),
		);
	});
	await until(() => loads === 3 && form());
	assert.equal(field("linker_request_id").value, requestIds[2]);
	assert.equal(field("message").value, "");
	assert.equal(
		form().querySelector('button[type="submit"]').textContent,
		"Send inquiry",
	);
}
test("returning after an unconfirmed native POST offers readback of the exact inquiry", (t) =>
	lostReceipt(t, true));
test("storage restrictions allow a native POST and recover the original in browser cache", (t) =>
	lostReceipt(t, false));

test("observe-mode UUID does not offer client-side replay", (t) =>
	lostReceipt(t, true, 0));
test("a pending inquiry beyond Woo's replay window discards its submitted fields and offers outcome guidance", (t) =>
	lostReceipt(t, true, 10, true));

test("reopening a pending preliminary review reads its original revision after another tab advances the project", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const style = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	const root = createRoot(fixture.element);
	const cache = new QueryClient();
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
		if (style) Object.defineProperty(globalThis, "getComputedStyle", style);
		else delete globalThis.getComputedStyle;
	});
	history.replaceState(
		null,
		"",
		"/workspace/?project=" + projectId + "#sc-preliminary-review",
	);
	const original = {
		id: projectId,
		revision: 7,
		title: "New project",
		input_sha256: "2".repeat(64),
		inputs: { brief: { ...emptyBrief(), system_scope: "storage_only" } },
	};
	const advanced = {
		...original,
		revision: 8,
		inputs: { brief: { ...emptyBrief(), system_scope: "pv_only" } },
	};
	const originalRequest = crypto.randomUUID();
	window.sessionStorage.setItem(
		"linker-preliminary-inquiry-pending:" +
			session.query_scope +
			":" +
			projectId +
			":7",
		JSON.stringify({
			requestId: originalRequest,
			expiresAt: Date.now() + 10000,
			fields: {
				linker_request_id: originalRequest,
				linker_preliminary_project: projectId + ":7",
				message: "Original message",
			},
		}),
	);
	const requests = [];
	const client = {
		origin: location.origin,
		isCurrentScope: (scope) => scope === session.query_scope,
		async query(path, command) {
			requests.push([path, command.revision]);
			if (path === "projects/read")
				return command.revision === 7 ? original : advanced;
			assert.equal(path, "inquiry/form");
			return {
				schema_version: 1,
				inquiry_lines: [],
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php" data-linker-inquiry-replay-seconds="10">
					<input type="hidden" name="linker_preliminary_project" value="${projectId}:${command.revision}">
					<input type="hidden" name="linker_request_id" data-linker-protected-action="inquiry" value="${crypto.randomUUID()}">
					<textarea name="message"></textarea><button type="submit">Send inquiry</button>
				</form>`,
			};
		},
	};
	const store = {
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async write() {},
	};
	await act(async () =>
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
						locale: "en",
						countries: {},
					},
					recheck: () => assert.fail("Unexpected scope invalidation"),
				}),
			),
		),
	);
	const form = () => fixture.element.querySelector("form.linker-inquiry-form");
	await until(form);
	assert.deepEqual(requests, [
		["projects/read", 7],
		["inquiry/form", 7],
	]);
	assert.equal(
		form().elements.namedItem("linker_request_id").value,
		originalRequest,
	);
	assert.equal(new window.FormData(form()).get("message"), "Original message");
	assert.match(
		fixture.element.querySelector(".sc-draft-transfer aside").textContent,
		/Planned system: Storage/,
	);
});
