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

test("the home form creates a comparison with the supplied data in a single submit", (t) =>
	runHomeComparison(t));

test("a rejected CSV mapping remains editable on the same project after reopening the homepage", (t) =>
	runHomeComparison(t, "correct"));

test("a customer can explicitly discard the rejected load profile and compare the same project", (t) =>
	runHomeComparison(t, "discard"));

test("the home form carries an unknown grid connection through project creation", (t) =>
	runHomeComparison(t, undefined, true));

test("a new-project CSV remains actionable when the homepage picker shows a saved project", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { HomepageComparison } =
		await import("../src/components/HomepageComparison.tsx");
	let root = createRoot(fixture.element);
	const cache = new QueryClient();
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
	});
	const project = {
		id: projectId,
		title: "Saved rooftop",
		revision: 1,
		input_sha256: "2".repeat(64),
		updated_at: 1763200000,
	};
	const client = {
		isCurrentScope: () => true,
		async query(path, command) {
			if (path === "products/current")
				return { schema_version: 1, provider: "woocommerce", products: [] };
			assert.equal(path, "projects/list");
			if (command.title_query === "Saved roof")
				return { schema_version: 1, items: [project], next: null };
			const first = {
				...project,
				id: "8".repeat(32),
				title: "Another project",
			};
			return {
				schema_version: 1,
				items: [first],
				next: { id: first.id, updated_at: first.updated_at },
			};
		},
	};
	const mount = (locale) =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(HomepageComparison, {
						session,
						client,
						config: { locale, countries: {} },
						store: {
							async readCreations() {
								return [];
							},
						},
						target: new URL("/workspace/", location.href),
						recheck() {},
					}),
				),
			),
		);
	await mount("en");
	await until(() => document.querySelector('input[type="search"]'));
	await enter(document.querySelector('input[type="search"]'), "Saved roof");
	await until(() =>
		document.querySelector('option[value="' + projectId + '"]'),
	);
	const csv = document.querySelector('[name="load_profile"]');
	await act(async () => {
		Object.defineProperty(csv, "files", {
			value: [new File(["timestamp,load"], "load.csv")],
		});
		csv.dispatchEvent(new Event("change", { bubbles: true }));
	});
	await act(async () => {
		const picker = document.querySelector(
			'option[value="' + projectId + '"]',
		).parentElement;
		picker.value = projectId;
		picker.dispatchEvent(new Event("change", { bubbles: true }));
	});
	assert.equal(document.querySelector('[name="load_profile"]'), null);
	const link = document.createElement("a");
	link.href = "/de/";
	link.lang = "de";
	link.hreflang = "de";
	document.querySelector("header").append(link);
	async function blocked() {
		let result;
		document.addEventListener(
			"click",
			(event) => {
				result = event.defaultPrevented;
				event.preventDefault();
			},
			{ once: true },
		);
		await act(async () =>
			link.dispatchEvent(
				new window.MouseEvent("click", { bubbles: true, cancelable: true }),
			),
		);
		return result;
	}
	assert.equal(await blocked(), true);
	assert.match(document.activeElement.textContent, /Your CSV is still here/);
	const remove = document.activeElement.querySelector("button");
	assert.equal(remove.textContent, "Remove CSV");
	await act(async () => remove.click());
	assert.equal(document.querySelector("option:checked").value, projectId);
	async function switchLanguage(lang, path) {
		link.href = path;
		link.hreflang = lang;
		link.lang = lang;
		assert.equal(await blocked(), false);
		await act(async () => root.unmount());
		cache.clear();
		history.pushState(null, "", link.href);
		root = createRoot(fixture.element);
		await mount(lang);
		await until(() => document.querySelector('input[type="search"]'));
		assert.equal(location.pathname, path);
		assert.equal(location.search, "");
		assert.equal(
			document.querySelector('input[type="search"]').value,
			"Saved roof",
		);
		await until(() =>
			document.querySelector('option[value="' + projectId + '"]'),
		);
	}
	await switchLanguage("de", "/de/");
	const picker = document.querySelector(
		'option[value="' + projectId + '"]',
	).parentElement;
	assert.equal(picker.value, projectId);
	await act(async () => {
		picker.value = "";
		picker.dispatchEvent(new Event("change", { bubbles: true }));
	});
	await switchLanguage("en", "/");
	assert.equal(
		document.querySelector('option[value="' + projectId + '"]').parentElement
			.value,
		"",
	);
	assert.ok(document.querySelector('input[name="project_title"]'));
});

async function runHomeComparison(t, rejectedProfile, unknownPhase = false) {
	const rejectFirstMapping = Boolean(rejectedProfile);
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SessionBoundary } =
		await import("../src/components/SessionBoundary.tsx");
	const { NewProject } = await import("../src/components/NewProject.tsx");
	const { ApiError } = await import("../src/data/protocol.ts");
	const { DraftStore } = await import("../src/data/DraftStore.ts");
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		configurable: true,
		value: new IDBFactory(),
	});
	const commands = [];
	const mappings = [];
	const calls = [];
	const sourceQueries = [];
	const external = t.mock.method(globalThis, "fetch", async () => {
		throw new Error("unexpected request to an external provider");
	});
	const asset = {
		id: "a".repeat(32),
		project_id: projectId,
		content_sha256: "5".repeat(64),
		metadata_sha256: "6".repeat(64),
		media_type: "application/json",
		purpose: "csv_profile_v1",
		metadata: {},
	};
	const startAt = "2020-01-01T10:00:00Z";
	const endAt = "2020-01-01T10:30:00Z";
	const csv = "Timestamp,Load\n" + startAt + ",3\n2020-01-01T10:15:00Z,7\n";
	const opened = [];
	const client = {
		invalidate() {},
		async bootstrap() {
			return session;
		},
		isCurrentScope: (scope) => scope === session.query_scope,
		async send(path, body) {
			const command = JSON.parse(body);
			calls.push(path);
			if (path === "projects/create") commands.push(command);
			else assert.equal(path, "projects/revise");
			return {
				id: projectId,
				revision: path === "projects/create" ? 1 : 2,
				title: commands[0].title,
				inputs: command.inputs,
				input_sha256: "2".repeat(64),
			};
		},
		async query(path, command) {
			if (path === "places/lookup") {
				sourceQueries.push([command.country, command.query]);
				return { imagery: null, viewing_imagery: null };
			}
			if (path === "products/current")
				return { schema_version: 1, provider: "woocommerce", products: [] };
			calls.push(path);
			assert.equal(command.project_id, projectId);
			if (path === "profiles/csv") {
				assert.equal(atob(command.content_base64), csv);
				assert.equal(command.mapping.measurement, "gross_load");
				assert.equal(command.mapping.origin, "measured");
				assert.equal(command.mapping.interval_seconds, 900);
				assert.equal(command.mapping.value_kind, "interval_average_kw");
				mappings.push(command);
				if (command.mapping.value_column === "Incorrect heading") {
					throw new ApiError(422, "invalid_input", {
						issue: "headers",
						line: 1,
						field: "header",
					});
				}
				assert.equal(command.mapping.value_column, "Load");
				assert.equal(command.source_label, "workshop-meter.csv");
				return asset;
			}
			assert.equal(path, "profiles/preview");
			assert.equal(command.asset_id, asset.id);
			return {
				schema_version: 1,
				evaluation_scope: "profile_interpretation",
				project_id: projectId,
				asset_id: asset.id,
				content_sha256: asset.content_sha256,
				metadata_sha256: asset.metadata_sha256,
				measurement: "gross_load",
				source: {},
				transformations: [],
				summary: {
					start_utc: startAt,
					end_utc: endAt,
					interval_count: 2,
					covered_seconds: 1800,
					span_seconds: 1800,
					gap_seconds: 0,
					gap_count: 0,
					energy_kwh: 2.5,
					min_interval_mean_kw: 3,
					max_interval_mean_kw: 7,
					native_max_interval_seconds: 900,
					effective_max_interval_seconds: 900,
					reconstructed_means: false,
				},
				rows: [],
				first_gaps: [],
				gaps_truncated: false,
				next_offset: null,
			};
		},
	};
	let root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else Reflect.deleteProperty(globalThis, "indexedDB");
	});
	const mountHome = (locale = "en") =>
		act(async () =>
			root.render(
				React.createElement(SessionBoundary, { client }, (value, recheck) =>
					React.createElement(NewProject, {
						session: value,
						client,
						store: new DraftStore(),
						recheck,
						openOnLoad: true,
						locale,
						config: { locale, countries: { DE: "Germany" } },
						homeComparison: {
							picker: null,
							savedProject: "",
							compareSaved() {},
						},
						created: (project, destination) => {
							opened.push([project, destination]);
							return true;
						},
					}),
				),
			),
		);
	const findForm = () =>
		document.querySelector('form[aria-label="Compare project options"]');
	await mountHome();
	await until(findForm);
	let form = findForm();
	const title = form.querySelector('[name="project_title"]');
	await until(() => !title.disabled && !title.closest("fieldset").disabled);
	function field(name) {
		return form.querySelector('[name="' + name + '"]');
	}
	function byLabel(label) {
		return [...form.querySelectorAll("label")]
			.find((element) => element.querySelector("span")?.textContent === label)
			?.querySelector("input, select, textarea");
	}
	async function select(name, value) {
		await act(async () => {
			const input = field(name) ?? byLabel(name);
			input.value = value;
			input.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	await enter(title, "Berlin workshop");
	await select("country", "DE");
	assert.deepEqual(sourceQueries, []);
	if (!rejectedProfile) {
		await enter(field("location_label"), "Werkstatt, 10117 Berlin");
		await until(() => sourceQueries.length > 0);
		assert.deepEqual(sourceQueries, [["DE", "10117"]]);
	}
	await select("system_scope", "new_pv_storage");
	await select("project_purpose", "peak");
	if (unknownPhase) {
		assert.match(
			field("grid_phase").selectedOptions[0].textContent,
			/not sure|not yet known/i,
		);
		assert.equal(field("grid_phase").required, false);
	} else await select("grid_phase", "3");
	await enter(field("annual_load_kwh"), "7200");
	await select("annual_load_basis", "bill_total");
	await enter(field("pv_dc_kw"), "8");
	if (unknownPhase) {
		const language = document.createElement("a");
		document.querySelector("header").append(language);
		async function switchLanguage(lang, url) {
			language.href = url;
			language.hreflang = lang;
			language.lang = lang;
			const click = new window.MouseEvent("click", {
				bubbles: true,
				cancelable: true,
			});
			// Emulate the cross-document navigation after the native switcher click.
			let blocked;
			document.addEventListener(
				"click",
				(event) => {
					blocked = event.defaultPrevented;
					event.preventDefault();
				},
				{ once: true },
			);
			await act(async () => language.dispatchEvent(click));
			if (blocked) return false;
			await act(async () => root.unmount());
			history.pushState(null, "", language.href);
			root = createRoot(fixture.element);
			await mountHome(lang);
			await until(findForm);
			form = findForm();
			return true;
		}
		assert.equal(await switchLanguage("de", "/de/"), true);
		assert.equal(field("project_title").value, "Berlin workshop");
		assert.equal(field("annual_load_kwh").value, "7200");
		assert.equal(field("annual_load_basis").value, "bill_total");
		assert.equal(field("pv_dc_kw").value, "8");
		await enter(field("pv_dc_kw"), "");
		await select("project_purpose", "");
		assert.equal(await switchLanguage("en", "/"), true);
		assert.equal(field("pv_dc_kw").value, "");
		assert.equal(field("project_purpose").value, "");
		await select("project_purpose", "peak");
		assert.equal(field("location_label").value, "Werkstatt, 10117 Berlin");
		assert.equal(calls.length, 0);
		await enter(field("pv_dc_kw"), "8");
	}

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
	await enter(field("peak_import_kw"), "5");
	const projectSummary = form.parentElement.querySelector("aside");
	assert.ok(
		projectSummary,
		"the intake shows the customer's current project alongside the form",
	);
	assert.match(projectSummary.textContent, /Berlin workshop/);
	assert.match(projectSummary.textContent, /7200 kWh/);
	assert.match(projectSummary.textContent, /8 kWp/);
	assert.match(projectSummary.textContent, /Target grid import limit5 kW/);

	const fileInput = field("load_profile");
	assert.equal(fileInput?.type, "file");
	await act(async () => {
		Object.defineProperty(fileInput, "files", {
			value: [new File([csv], "workshop-meter.csv", { type: "text/csv" })],
		});
		fileInput.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await select("load_profile_delimiter", ",");
	if (unknownPhase) {
		const link = document.querySelector("a[hreflang]");
		const click = new window.MouseEvent("click", {
			bubbles: true,
			cancelable: true,
		});
		await act(async () => link.dispatchEvent(click));
		assert.equal(click.defaultPrevented, true);
		assert.match(document.activeElement.textContent, /CSV.*switch languages/);
		assert.equal(field("load_profile_delimiter").value, ",");
	}

	await enter(
		field("load_profile_rights"),
		"Customer site meter; permission granted.",
	);
	await enter(byLabel("Timestamp column"), "Timestamp");
	await enter(
		byLabel("Value column"),
		rejectFirstMapping ? "Incorrect heading" : "Load",
	);
	await select("Value meaning and unit", "interval_average_kw");
	await select("Decimal separator in the file", ".");
	await select("Interval boundaries", "fixed");
	await select("The timestamp identifies…", "start");
	await enter(field("profile_interval_minutes"), "15");
	await select("Source time zone", "UTC");
	assert.deepEqual(calls, []);
	assert.equal(external.mock.callCount(), 0);
	const submit = form.querySelector('button[type="submit"]');
	assert.equal(submit.textContent.trim(), "Compare systems");
	if (!rejectFirstMapping && !unknownPhase) {
		await enter(field("latitude"), "91,8");
		assert.equal(field("latitude").value, "91,8");
		await act(async () => submit.click());
		assert.deepEqual(calls, []);
		assert.equal(field("load_profile_source").value, "workshop-meter.csv");
		await enter(field("latitude"), "47,66");
	}
	await act(async () => submit.click());
	if (rejectFirstMapping) {
		await until(() => calls.includes("profiles/csv") && !submit.disabled);
		assert.equal(opened.length, 0);
		const language = document.createElement("a");
		language.href = "/de/";
		language.hreflang = "de";
		language.lang = "de";
		document.querySelector("header").append(language);
		async function languageBlocked() {
			let blocked;
			document.addEventListener(
				"click",
				(event) => {
					blocked = event.defaultPrevented;
					event.preventDefault();
				},
				{ once: true },
			);
			await act(async () =>
				language.dispatchEvent(
					new window.MouseEvent("click", { bubbles: true, cancelable: true }),
				),
			);
			return blocked;
		}
		assert.equal(
			await languageBlocked(),
			false,
			"the saved import can reopen in another language",
		);
		const editedField =
			rejectedProfile === "correct"
				? field("profile_interval_minutes")
				: byLabel("Value column");
		const editedText =
			rejectedProfile === "correct" ? "-1" : "Load corrected before switching";
		const revealed = [];
		const scrolling = t.mock.method(
			window.HTMLElement.prototype,
			"scrollIntoView",
			function (options) {
				revealed.push([this, options]);
			},
		);
		await enter(editedField, editedText);
		assert.equal(revealed.length, 0);
		for (let click = 0; click < 2; click++) {
			const previousReveals = revealed.length;
			language.focus();
			assert.equal(await languageBlocked(), true);
			const notice = document.activeElement;
			assert.equal(notice.getAttribute("role"), "alert");
			assert.match(notice.textContent, /Your CSV changes are still here/);
			assert.equal(revealed.length, previousReveals + 1);
			assert.equal(revealed.at(-1)?.[0], notice);
			assert.equal(revealed.at(-1)?.[1].block, "center");
		}
		scrolling.mock.restore();
		assert.equal(editedField.value, editedText);
		await act(async () => root.unmount());
		root = createRoot(fixture.element);
		await mountHome();
		await until(() =>
			findForm()?.querySelector('[name="load_profile_source"]'),
		);
		form = findForm();
		assert.equal(byLabel("Value column").value, "Incorrect heading");
		assert.equal(field("load_profile_source").value, "workshop-meter.csv");
		if (rejectedProfile === "discard") {
			const discard = [...form.querySelectorAll("button")].find(
				(button) => button.textContent === "Compare without this load profile",
			);
			assert.ok(discard);
			await act(async () => discard.click());
		} else {
			await enter(byLabel("Value column"), "Load");
			await act(async () =>
				form.querySelector('button[type="submit"]').click(),
			);
		}
	}
	await until(() => opened.length === 1);
	assert.equal(commands.length, rejectFirstMapping ? 2 : 1);
	if (rejectFirstMapping) {
		assert.deepEqual(commands[1], commands[0]);
		if (rejectedProfile === "correct")
			assert.notEqual(mappings[1].key, mappings[0].key);
	}
	assert.equal(commands[0].inputs.brief.site.country_code, "DE");
	assert.equal(
		commands[0].inputs.equipment_setup.grid_phase,
		unknownPhase ? null : 3,
	);
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
	assert.deepEqual(calls, [
		...(rejectFirstMapping ? ["projects/create", "profiles/csv"] : []),
		"projects/create",
		...(rejectedProfile === "discard"
			? []
			: ["profiles/csv", "profiles/preview", "projects/revise"]),
	]);
	const [[saved, destination]] = opened;
	assert.equal(destination, "guided-comparison");
	assert.equal(saved.id, projectId);
	assert.equal(saved.revision, rejectedProfile === "discard" ? 1 : 2);
	assert.equal(
		saved.inputs.profile_selections?.selected.gross_load,
		rejectedProfile === "discard" ? undefined : asset.id,
	);
	assert.deepEqual(
		await new DraftStore().readCreations(session.query_scope),
		[],
	);
	const [period] = saved.inputs.energy_scenario.schedule;
	assert.equal(period.import_cap_kw, 5);
	assert.equal(period.start_utc, rejectedProfile === "discard" ? "" : startAt);
	assert.equal(period.end_utc, rejectedProfile === "discard" ? "" : endAt);
}

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
	const renderWorkspace = () =>
		act(async () =>
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
	await renderWorkspace();
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
	const compareAgain = () =>
		Array.from(document.querySelectorAll("button")).find(
			(item) =>
				item.textContent.trim() === "Compare options" &&
				!item.closest("[hidden]"),
		);
	assert.ok(
		compareAgain(),
		"A visitor who filled in optional details can return to compare without starting another project",
	);
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
	const annual = document.querySelector('input[name="annual_load_kwh"]');
	assert.ok(
		annual,
		"A visitor can bring annual usage into the preliminary comparison",
	);
	await enter(annual, "6412");
	assert.equal(document.querySelector("h1").textContent, "Oslo storage");
	assert.match(document.querySelector("aside").textContent, /6412 kWh/);

	await act(async () => compareAgain().click());
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.match(
		document.querySelector("dl.sc-project-facts").textContent,
		/Oslo 0150/,
	);
	assert.deepEqual(creates, []);
	// Rebuild the document against its current history entry, just as a reload does.
	window.dispatchEvent(new window.Event("pagehide"));
	await act(async () => root.render(null));
	await renderWorkspace();
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.match(
		document.querySelector("dl.sc-project-facts")?.textContent ?? "",
		/Oslo 0150/,
	);
	assert.match(
		document.querySelector("dl.sc-project-facts").textContent,
		/6412 kWh/,
	);
	const englishPage = location.href;
	const germanLink = document.querySelector('header a[hreflang="de"]');
	const translatedPage = germanLink.href;
	germanLink.addEventListener("click", (event) => event.preventDefault(), {
		once: true,
	});
	germanLink.click();
	window.dispatchEvent(new window.Event("pagehide"));
	await act(async () => root.render(null));
	history.pushState(null, "", translatedPage);
	await renderWorkspace();
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.match(
		document.querySelector("dl.sc-project-facts")?.textContent ?? "",
		/Oslo 0150/,
	);
	await act(async () => root.render(null));
	await new Promise((resolve) => {
		window.addEventListener("popstate", resolve, { once: true });
		history.back();
	});
	assert.equal(location.href, englishPage);
	await renderWorkspace();
	await act(async () => history.back());
	await until(() => document.querySelector('input[name="location_label"]'));
	await act(async () => history.back());
	await until(() =>
		document.querySelector('table[aria-label="Compare system options"]'),
	);
	assert.equal(
		Boolean(document.querySelector('input[name="project_title"]')),
		false,
	);
	assert.equal(document.activeElement.textContent, "Preliminary options");
	assert.match(
		document.querySelector("dl.sc-project-facts")?.textContent ?? "",
		/Oslo 0150/,
	);
	assert.deepEqual(
		Array.from(
			document.querySelector(".sc-inquiry-stages").children,
			(step) => step.textContent,
		),
		["Compare options", "Choose an option", "Review and send"],
	);
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
	const basis = document.querySelector('select[name="annual_load_basis"]');
	await act(async () => {
		basis.value = "user_estimate";
		basis.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	const next = [...document.querySelectorAll("button")].find(
		(item) => item.textContent === "Compare systems",
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
	const project = { id: projectId, revision: 1, inputs: {} };
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
	const details = () =>
		fixture.element.querySelector("form .linker-inquiry-details");
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
	const project = { id: projectId, revision: 7, inputs: {} };
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
					<input type="hidden" name="linker_request_id" value="${requestIds[n]}">
					<input type="hidden" name="linker_draft_hash" value="${n ? "" : "original-cart"}">
					<input type="hidden" name="lang" value="en">
					<input type="hidden" name="cf-turnstile-response" value="${n ? "" : "previous-turnstile-response"}">
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
	assert.equal(replay.get("cf-turnstile-response"), "");

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
					<input type="hidden" name="linker_request_id" value="${crypto.randomUUID()}">
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

test("native guided retry reads the reviewed revision without any browser replay", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { replacePlannerLocation } =
		await import("../src/data/plannerLocation.ts");
	const cache = new QueryClient();
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
	});
	const route = new URL(location.href);
	route.searchParams.set("project", projectId);
	route.searchParams.set("guided", "inquiry");
	route.searchParams.set("run", "8".repeat(32));
	route.searchParams.set("retry_revision", "7");
	route.searchParams.set("linker_inquiry_retry", crypto.randomUUID());
	route.hash = "sc-review";
	history.replaceState(null, "", route);
	const revisions = [];
	const client = {
		isCurrentScope: () => true,
		query(path, command) {
			assert.equal(path, "projects/read");
			revisions.push(command.revision);
			return new Promise(() => {});
		},
	};
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Workspace, {
					session,
					client,
					config: {},
					store: {},
					recheck: () => assert.fail("Unexpected scope invalidation"),
				}),
			),
		),
	);
	await until(() => revisions.length === 1);
	assert.deepEqual(revisions, [7]);
	route.searchParams.delete("retry_revision");
	route.hash = "sc-system";
	await act(async () => replacePlannerLocation(route));
	await until(() => revisions.length === 2);
	assert.deepEqual(revisions, [7, null]);
});

for (const goal of ["self", "peak", "backup"])
	test(`a retrofit with an unknown phase compares ${goal} inverter options and sends its reviewed project revision`, (t) =>
		compareRetrofit(t, goal));

test("incomplete backup requirements still open preliminary choices when grid phase is known", (t) =>
	compareRetrofit(t, "backup", 3));

async function compareRetrofit(t, goal, gridPhase = null) {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { changeEnergyGoal } =
		await import("../src/components/configurator/EnergyDemand.tsx");
	const { equipmentDraft } = await import("../src/domain/equipment.ts");
	const { DraftStore } = await import("../src/data/DraftStore.ts");
	globalThis.indexedDB = new IDBFactory();
	const root = createRoot(fixture.element);
	const cache = new QueryClient();
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	});
	const brief = emptyBrief();
	const inputs = changeEnergyGoal(
		{
			brief: {
				...brief,
				system_scope: "storage_addition",
				project_use: "residential",
				site: {
					...brief.site,
					country_code: "DE",
					location_label: "Konstanz",
				},
				annual_load: { kwh: 6200, basis: "bill_total", source_note: "" },
			},
			...(goal === "backup" && {
				existing_system: {
					schema_version: 1,
					name: "Workshop inverter",
					inverter_power_kw: 7.5,
					keep_inverter: true,
				},
			}),
			equipment_setup: {
				...equipmentDraft({}),
				pv_dc_kw: 8,
				grid_phase: gridPhase,
			},
		},
		goal,
	);
	let project = {
		id: projectId,
		revision: 1,
		title: "Bodensee",
		inputs,
		input_sha256: "2".repeat(64),
	};
	let review;
	const client = {
		origin: location.origin,
		isCurrentScope: () => true,
		async query(path, command) {
			if (path === "projects/read") return project;
			if (path === "projects/runs")
				return { schema_version: 1, items: [], next: null };
			assert.equal(path, "inquiry/form");
			review = command;
			return {
				schema_version: 1,
				inquiry_lines: [],
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php"><input name="linker_preliminary_project" value="${projectId}:${project.revision}"></form>`,
			};
		},
		async send(path, body) {
			assert.equal(path, "projects/revise");
			project = {
				...project,
				revision: 2,
				inputs: JSON.parse(body).inputs,
				input_sha256: "4".repeat(64),
			};
			return project;
		},
	};
	history.replaceState(
		null,
		"",
		`/workspace/?project=${projectId}&guided=inquiry#sc-system`,
	);
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Workspace, {
					config: { locale: "en", countries: { DE: "Germany" } },
					session,
					client,
					store: new DraftStore(),
					recheck() {},
				}),
			),
		),
	);
	const options = () =>
		document.querySelector('table[aria-label="Compare system options"]');
	await until(options);
	assert.equal(location.hash, "#sc-preliminary-options");
	const facts = document.querySelector("dl.sc-project-facts").textContent;
	for (const value of [
		"Konstanz",
		"Residential",
		"8 kWp",
		"6200 kWh",
		"Electricity bill",
		{
			self: "Use more solar on site",
			peak: "Reduce peak demand",
			backup: "Backup supply",
		}[goal],
		gridPhase ? "Three phase" : "To confirm",
	])
		assert.ok(facts.includes(value), value);
	const keep = [...options().querySelectorAll("tr")].find((row) =>
		row.textContent.includes("Keep the existing inverter"),
	);
	assert.ok(keep);
	assert.equal(document.querySelector("h1").textContent, "Bodensee");
	for (const row of options().querySelectorAll("tbody tr"))
		assert.match(
			row.textContent,
			{
				peak: /peak|import limit/i,
				backup: /backup|outage/i,
				self: /surplus|solar|panels/i,
			}[goal],
		);
	assert.match(options().textContent, /replacement inverter/i);
	await until(() => !keep.querySelector("button").disabled);
	await act(async () => keep.querySelector("button").click());
	await until(() =>
		document.querySelector(
			".sc-preliminary-review:not([hidden]) form.linker-inquiry-form",
		),
	);
	assert.equal(review.revision, goal === "backup" ? 1 : 2);
	assert.equal(review.project_id, projectId);
	assert.equal(review.report_run_id, undefined);
	assert.deepEqual(project.inputs.brief, inputs.brief);
	assert.equal(project.inputs.equipment_setup.grid_phase, gridPhase);
	assert.equal(project.inputs.existing_system.keep_inverter, true);
	assert.match(
		document.querySelector(".sc-inquiry-overview").textContent,
		/Keep the existing inverter/,
	);
}

for (const view of ["", "project", "equipment"])
	test(`${view || "bare"} entry compares a retrofit and opens its Woo inquiry`, (t) =>
		compareEntryRetrofit(t, view));

async function compareEntryRetrofit(t, view) {
	const fixture = setupDom();
	history.replaceState(null, "", "/workspace/" + (view ? "?view=" + view : ""));
	const style = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	t.after(() => {
		if (style) Object.defineProperty(globalThis, "getComputedStyle", style);
		else delete globalThis.getComputedStyle;
	});
	globalThis.indexedDB = new IDBFactory();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { Workspace } = await import("../src/components/Workspace.tsx");
	const { DraftStore } = await import("../src/data/DraftStore.ts");
	const cache = new QueryClient(),
		root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	});
	let project, inquiry;
	const client = {
		origin: location.origin,
		isCurrentScope: () => true,
		async query(path, command) {
			if (path === "projects/list")
				return {
					schema_version: 1,
					items: [
						{
							id: "8".repeat(32),
							title: "Earlier project",
							revision: 1,
							input_sha256: "7".repeat(64),
							updated_at: 1763200000,
						},
					],
					next: null,
				};
			if (path === "projects/runs")
				return { schema_version: 1, items: [], next: null };
			if (path === "products/current")
				return { schema_version: 1, provider: "woocommerce", products: [] };
			if (path === "projects/read") return project;
			assert.equal(path, "inquiry/form");
			inquiry = command;
			return {
				schema_version: 1,
				inquiry_lines: [],
				inquiry_form_html: `<form class="linker-inquiry-form" method="post" action="/wp-admin/admin-post.php"><input name="linker_preliminary_project" value="${projectId}:${command.revision}"></form>`,
			};
		},
		async send(path, body) {
			const command = JSON.parse(body);
			if (path === "projects/create") {
				assert.equal(project, undefined);
				project = {
					id: projectId,
					revision: 1,
					title: command.title,
					inputs: command.inputs,
					input_sha256: "2".repeat(64),
				};
			} else {
				assert.equal(path, "projects/revise");
				project = { ...project, revision: 2, inputs: command.inputs };
			}
			return project;
		},
	};
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Workspace, {
					config: { locale: "en", countries: {} },
					client,
					session,
					store: new DraftStore(),
					recheck: () => {},
				}),
			),
		),
	);
	const selector = 'select[name="system_scope"]';
	await until(() => document.querySelector(selector));
	const scope = document.querySelector(selector);
	const equipment = scope.form.querySelector("details.sc-project-equipment");
	assert.equal(equipment.open, view === "equipment");
	if (view === "equipment")
		assert.ok(
			equipment.compareDocumentPosition(scope) &
				window.Node.DOCUMENT_POSITION_FOLLOWING,
		);
	assert.equal(
		equipment.querySelector('button[aria-pressed="true"]').textContent,
		"Single system",
	);
	await act(async () => {
		scope.value = "storage_addition";
		scope.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	const compare = [...scope.form.querySelectorAll("button")].find(
		(el) => el.textContent === "Compare systems",
	);
	assert.ok(compare, "the new project has a Compare systems action");
	await until(() => !compare.disabled);
	await act(async () => compare.click());
	await until(() =>
		document.querySelector(".sc-direction-comparison tbody tr"),
	);
	const rows = [
		...document.querySelectorAll(".sc-direction-comparison tbody tr"),
	];
	assert.deepEqual(
		rows.map((row) => row.querySelector("th").textContent),
		["Keep the existing inverter", "Consider a replacement inverter"],
	);
	assert.equal(project.inputs.brief.system_scope, "storage_addition");
	await until(() => !rows[0].querySelector("button").disabled);
	await act(async () => rows[0].querySelector("button").click());
	await until(() =>
		document.querySelector(
			".sc-preliminary-review:not([hidden]) form.linker-inquiry-form",
		),
	);
	assert.equal(inquiry.project_id, project.id);
	assert.equal(inquiry.revision, 2);
}
