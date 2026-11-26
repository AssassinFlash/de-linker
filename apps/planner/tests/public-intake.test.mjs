import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, deferred, enter } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

for (const invalidWhileWaiting of [false, true])
	test(
		"public Genie inputs survive admission and language navigation " +
			(invalidWhileWaiting
				? "pauses on invalid edits"
				: "carries the latest edits"),
		async (t) => {
			const fixture = setupDom();
			window.history.replaceState(
				null,
				"",
				"/solution-configurator/?annual_kwh=6000&phase=3&backup=needed" +
					(invalidWhileWaiting
						? "&application=commercial&goal=peak_shaving"
						: ""),
			);
			const { createRoot } = await import("react-dom/client");
			const { SessionBoundary } =
				await import("../src/components/SessionBoundary.tsx");
			const { Workspace } = await import("../src/components/Workspace.tsx");
			const { DraftStore } = await import("../src/data/DraftStore.ts");
			const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
			Object.defineProperty(globalThis, "indexedDB", {
				configurable: true,
				value: new IDBFactory(),
			});
			const admission = deferred(),
				queries = [];
			let starts = 0,
				admitted = false;
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
			const client = {
				bootstrap: async () => {
					starts++;
					await admission.promise;
					admitted = true;
					return session;
				},
				invalidate() {},
				isCurrentScope: (scope) => admitted && scope === session.query_scope,
				query: async (path) => {
					queries.push(path);
					return { items: [], next: null };
				},
				probeScope: async () => session.query_scope,
			};
			const root = createRoot(fixture.element),
				store = new DraftStore();
			t.after(async () => {
				await fixture.dispose(root);
				if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
				else Reflect.deleteProperty(globalThis, "indexedDB");
			});
			const render = (publicIntake, locale) =>
				act(async () =>
					root.render(
						React.createElement(
							SessionBoundary,
							{ client, publicIntake },
							(value, recheck, ensureSession) =>
								React.createElement(Workspace, {
									client,
									store,
									session: value,
									recheck,
									ensureSession,
									config: { locale, countries: { DE: "Germany" } },
								}),
						),
					),
				);
			await render(true, "en");
			const start = document.querySelector('select[name="project_start"]');
			assert.ok(start);
			assert.equal(start.disabled, false);
			assert.equal(starts, 0);
			assert.equal(
				document.querySelector("[name=annual_load_kwh]").value,
				"6000",
			);
			assert.equal(document.querySelector("[name=grid_phase]").value, "3");
			assert.equal(
				document.querySelector("[name=project_purpose]").value,
				invalidWhileWaiting ? "peak" : "backup",
			);
			const name = document.querySelector('input[name="project_name"]');
			assert.ok(name);
			await act(async () => name.focus());
			await enter(name, "Rooftop");
			assert.equal(starts, 1);
			assert.deepEqual(queries, []);
			const language = document.createElement("a");
			language.lang = "de";
			language.hreflang = "de";
			language.href = "/de/loesungskonfigurator/";
			document.querySelector("header").append(language);
			for (const [options, target] of [
				[{ button: 1 }, ""],
				[{ metaKey: true }, ""],
				[{ ctrlKey: true }, ""],
				[{ altKey: true }, ""],
				[{ shiftKey: true }, ""],
				[{}, "_blank"],
				[{}, "other-tab"],
			]) {
				language.target = target;
				let intercepted;
				language.addEventListener(
					"click",
					(event) => {
						intercepted = event.defaultPrevented;
						event.preventDefault();
					},
					{ once: true },
				);
				await act(async () =>
					language.dispatchEvent(
						new window.MouseEvent("click", {
							bubbles: true,
							cancelable: true,
							...options,
						}),
					),
				);
				assert.equal(intercepted, false);
			}
			language.target = "_self";
			const click = new window.MouseEvent("click", {
				bubbles: true,
				cancelable: true,
			});
			await act(async () => language.dispatchEvent(click));
			assert.ok(click.defaultPrevented);
			assert.equal(
				window.sessionStorage.getItem("linker-comparison-draft"),
				null,
			);
			await enter(name, "Rooftop updated");
			const pv = document.querySelector("[name=site_pv_kw]");
			if (invalidWhileWaiting) await enter(pv, "invalid");
			await act(async () => admission.resolve());
			if (invalidWhileWaiting) {
				await until(() =>
					document.body.textContent.includes(
						"Check the highlighted value before switching languages.",
					),
				);
				assert.equal(location.hash, "");
				assert.equal(pv.value, "invalid");
				await enter(pv, "12");
				await act(async () => language.click());
			}
			await until(
				() =>
					JSON.parse(
						window.sessionStorage.getItem("linker-comparison-draft") ?? "null",
					)?.languageUrl === language.href,
			);
			const handoff = JSON.parse(
				window.sessionStorage.getItem("linker-comparison-draft"),
			);
			assert.equal(handoff.scope, session.query_scope);
			assert.equal(handoff.title, "Rooftop updated");
			assert.equal(handoff.languageUrl, language.href);
			await until(() => admitted);
			assert.equal(name, document.querySelector('input[name="project_name"]'));
			assert.equal(name.value, "Rooftop updated");
			assert.deepEqual(queries, []);
			const german = language.href;
			const to = new URL(german);
			assert.equal(to.pathname, "/de/loesungskonfigurator/");
			if (invalidWhileWaiting) {
				assert.equal(to.searchParams.get("application"), "commercial");
				assert.equal(to.searchParams.get("goal"), "peak_shaving");
			}
			// JSDOM has no document-navigation implementation. Open the actual linked
			// German route with a fresh React tree and the same tab's stored draft.
			await act(async () => root.render(null));
			history.replaceState(null, "", german);
			await render(false, "de-DE");
			await until(() => document.querySelector("[name=project_name]"));
			assert.equal(
				document.querySelector("[name=project_name]").value,
				"Rooftop updated",
			);
			assert.equal(
				document.querySelector("[name=annual_load_kwh]").value,
				"6000",
			);
			if (invalidWhileWaiting)
				assert.equal(
					document.querySelector("[name=project_purpose]").value,
					"peak",
				);
			const projects = Array.from(document.querySelectorAll("button")).find(
				(x) => x.textContent === "Projects",
			);
			await act(async () => projects.click());
			await until(() => queries.includes("projects/list"));
			const footer = document.createElement("footer"),
				late = document.createElement("a");
			late.hreflang = "en";
			late.lang = "en";
			late.href = "/solution-configurator/";
			footer.append(late);
			document.body.append(footer);
			document.dispatchEvent(new window.Event("DOMContentLoaded"));
			assert.equal(new URL(late.href).searchParams.get("projects"), "1");
			assert.equal(starts, 2);
		},
	);

test("signed-in, recovery and private links use the existing admission gate; public marketing hints show intake", async (t) => {
	const fixture = setupDom();
	t.after(() => fixture.dom.window.close());
	const { canStartPublicIntake } = await import("../src/data/publicIntake.ts");
	const url = (query = "") =>
		new URL("/solution-configurator/" + query, location.origin);
	const anon = { nonceUrl: "", hasWorkspaceSession: false };
	for (const query of [
		"",
		"?annual_kwh=6000",
		"?phase=3",
		"?backup=needed",
		"?application=commercial&goal=peak_shaving",
		"?scope=storage_addition",
		"?utm_source=example",
	])
		assert.equal(canStartPublicIntake(anon, url(query)), true, query);
	for (const query of [
		"?projects=1",
		"?project=123",
		"?saved_solution=1",
		"?brief=1",
		"?retry_revision=1",
		"?linker_inquiry_retry=1",
		"?run=1",
		"?view=equipment",
		"?energy_view=1",
		"?step=roof",
		"?step=equipment&product_id=123",
		"?product_id=123",
		"#sc-review",
	])
		assert.equal(canStartPublicIntake(anon, url(query)), false, query);
	assert.equal(
		canStartPublicIntake({ ...anon, nonceUrl: "/nonce" }, url()),
		false,
	);
	assert.equal(
		canStartPublicIntake({ ...anon, hasWorkspaceSession: true }, url()),
		false,
	);
	window.history.replaceState({ "linker-comparison-draft": "draft123" }, "");
	window.sessionStorage.setItem(
		"linker-comparison-draft",
		JSON.stringify({ id: "draft123" }),
	);
	assert.equal(canStartPublicIntake(anon, url()), false);
});

for (const clean of [false, true])
	test(
		(clean ? "fresh" : "returning") +
			" intake never replays a recovered creation for a different selection",
		async (t) => {
			const fixture = setupDom();
			const { createRoot } = await import("react-dom/client");
			const { NewProject } = await import("../src/components/NewProject.tsx");
			const { QueryClient, QueryClientProvider } =
				await import("@tanstack/react-query");
			const { emptyBrief } = await import("../src/domain/brief.ts");
			const scope = "a".repeat(64),
				session = {
					kind: clean ? "guest" : "user",
					cookie_confirmed: true,
					query_scope: scope,
					claim_pending: false,
					runtime: {
						limits: {
							max_json_depth: 32,
							max_body_bytes: 1000000,
							max_page_size: 30,
						},
					},
				};
			const key = crypto.randomUUID(),
				title = "Unconfirmed original";
			const body = JSON.stringify({
				schema_version: 1,
				title,
				key,
				inputs: { brief: emptyBrief() },
			});
			const pending = deferred(),
				sent = [];
			const store = {
				async readCreations() {
					return pending.promise;
				},
				async writeCreation() {},
			};
			const client = {
				isCurrentScope: (v) => v === scope,
				async send(path, captured) {
					assert.equal(path, "projects/create");
					sent.push(captured);
					throw new Error("transport unavailable");
				},
			};
			const cache = new QueryClient();
			const root = createRoot(fixture.element);
			function App() {
				const [ready, setReady] = React.useState(!clean);
				return React.createElement(NewProject, {
					session: ready ? session : null,
					client,
					store,
					ensureSession: async () => {
						setReady(true);
						return session;
					},
					created: () => true,
					recheck() {},
					compareOnLoad: true,
					directComparison: true,
					recoveryScopes: [scope],
					config: { locale: "en", countries: { DE: "Germany" } },
				});
			}
			t.after(async () => {
				await fixture.dispose(root);
				cache.clear();
			});
			await act(async () =>
				root.render(
					React.createElement(
						QueryClientProvider,
						{ client: cache },
						React.createElement(App),
					),
				),
			);
			const choice = document.querySelector(
				"button[aria-describedby=sc-direction-pv_only]",
			);
			assert.ok(choice);
			assert.equal(choice.disabled, !clean);
			await act(async () => choice.click());
			await act(async () =>
				pending.resolve([
					{ key, title, body, createdAt: 1, destination: "preliminary-review" },
				]),
			);
			const retry = () =>
				Array.from(document.querySelectorAll("button")).find(
					(b) => b.textContent === "Retry project creation",
				);
			await until(() => retry() && !retry().disabled);
			assert.deepEqual(sent, []);
			await act(async () => retry().click());
			await until(() => sent.length > 0);
			assert.deepEqual(sent, [body]);
		},
	);
