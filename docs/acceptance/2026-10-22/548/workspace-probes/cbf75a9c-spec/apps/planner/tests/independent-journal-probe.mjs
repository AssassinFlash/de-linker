import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { emptyBrief } from "../src/domain/brief.ts";
import { emptyGeometry } from "../src/domain/geometryCommands.ts";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };

const SESSION = { schema_version: 1, kind: "guest", cookie_confirmed: true, expires_at: 2000000000, query_scope: "a".repeat(64), nonce: "syntheticnonce", claim_pending: false, runtime: { schema_version: 1, runtime_sha256: "b".repeat(64), models: {}, limits: { max_body_bytes: 1000000, max_csv_bytes: 100000, max_page_size: 30, max_json_depth: 32 } } };

function button(text, scope = document) {
  const found = [...scope.querySelectorAll("button")].find(b => b.textContent.trim() === text);
  assert.ok(found, "Missing button: " + text); return found;
}
async function click(text, scope) { await act(async () => button(text, scope).click()); }
function nav(label) { const found = [...document.querySelectorAll('nav[aria-label="Project sections"] a')].find(a => a.textContent.trim() === label); assert.ok(found, "Missing navigation: " + label); return found; }
async function choose(label) { await act(async () => nav(label).click()); }
function metric(label) { const dt = [...document.querySelectorAll(".lp-overview-metrics dt")].find(n => n.textContent === label); assert.ok(dt); return dt.parentElement.querySelector("dd").textContent.trim(); }
function annual() { return [...document.querySelectorAll("input")].find(n => document.getElementById(n.getAttribute("aria-labelledby"))?.textContent.includes("Annual consumption")); }

async function mount(t, { hash = "", geometry = emptyGeometry(), brief = emptyBrief(), locale = "en-GB" } = {}) {
  const fixture = setupDom();
  fixture.dom.window.history.replaceState(null, "", fixture.dom.window.location.pathname + fixture.dom.window.location.search + hash);
  const { createRoot } = await import("react-dom/client");
  const { ProjectEditor } = await import("../src/components/ProjectEditor.tsx");
  const root = createRoot(fixture.element), cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const writes = [], requests = [], sends = [];
  let admitted = true;
  const store = { async read() { return null; }, async candidates() { return []; }, async readProfileImports() { return []; }, async write(scope, draft) { writes.push({ scope, draft: structuredClone(draft) }); } };
  const client = { isCurrentScope: scope => admitted && scope === SESSION.query_scope, async query(...args) { requests.push(args); throw new Error("No remote query expected in this fixture"); }, async send(...args) { sends.push(args); throw new Error("No remote mutation expected in this fixture"); } };
  const project = { id: "1".repeat(32), title: "Independent Journal project", revision: 7, input_sha256: "2".repeat(64), inputs: { brief, geometry, preserved_extension: { fixture: "exact" } } };
  const config = { baseUrl: location.origin + "/api/", nonceUrl: location.origin + "/nonce", locale, countries: { NO: "Norway", FR: "France", DE: "Germany" } };
  t.after(async () => { cache.clear(); await fixture.dispose(root); });
  await act(async () => root.render(React.createElement(QueryClientProvider, { client: cache }, React.createElement(ProjectEditor, { project, session: SESSION, client, store, config, recheck() {}, close() { return true; } }))));
  await until(() => document.querySelector(".lp-project"));
  return { fixture, writes, requests, sends, original: structuredClone(project.inputs), revoke() { admitted = false; } };
}

test("legacy initial fragment links reveal the corresponding active workspace without revising inputs", async t => {
  for (const [hash, expected] of [["#lp-site", "site"], ["#lp-brief-use", "site"], ["#lp-notes", "site"], ["#lp-load", "energy"], ["#lp-profiles", "energy"], ["#lp-design", "design"], ["#lp-overview", "overview"]]) {
    await t.test(hash, async sub => { const app = await mount(sub, { hash }); assert.equal(document.querySelector(".lp-project").dataset.workspace, expected); assert.equal(document.querySelectorAll('nav a[aria-current="page"]').length, 1); assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0); });
  }
});

test("missing inputs render unknown quantities; an explicitly empty layout can honestly render zero", async t => {
  await t.test("missing", async sub => { const app = await mount(sub); for (const label of ["Country", "Annual consumption", "Included modules", "Declared DC nameplate power"]) assert.equal(metric(label), "—"); assert.equal(document.querySelector(".lp-overview svg.lp-plan-svg"), null); assert.equal(app.sends.length, 0); });
  await t.test("all explicitly excluded", async sub => { const geometry = structuredClone(flat); geometry.arrays[0].excluded_slots = ["0:0", "0:1", "0:2", "1:0", "1:1", "1:2"]; await mount(sub, { geometry }); assert.equal(metric("Included modules"), "0"); assert.equal(metric("Declared DC nameplate power"), "0 kWp"); });
});

test("multiple roof quantities use included objects across the document while preview names its first roof", async t => {
  const geometry = structuredClone(flat);
  geometry.roofs.push({ ...structuredClone(geometry.roofs[0]), id: "roof_second", name: "Second synthetic roof" });
  geometry.module_specs.push({ ...structuredClone(geometry.module_specs[0]), id: "module_second", stc_power_w: 460 });
  geometry.arrays.push({ ...structuredClone(geometry.arrays[0]), id: "array_second", roof_id: "roof_second", module_spec_id: "module_second", rows: 1, columns: 2, excluded_slots: ["0:1"] });
  const brief = emptyBrief(); brief.site.country_code = "FR"; brief.annual_load = { ...brief.annual_load, kwh: 50667, basis: "bill_total" };
  const app = await mount(t, { geometry, brief });
  assert.equal(metric("Country"), "France"); assert.equal(metric("Annual consumption"), "50667 kWh"); assert.equal(metric("Included modules"), "6"); assert.equal(metric("Declared DC nameplate power"), "2.96 kWp");
  assert.equal(document.querySelector(".lp-overview-preview-title span").textContent, "Fixture roof");
  assert.equal(document.querySelectorAll(".lp-overview .lp-panel-shape").length, 6);
  assert.equal(document.querySelectorAll(".lp-overview .lp-panel-shape[data-excluded]").length, 1);
  assert.ok(document.querySelector(".lp-overview").textContent.includes("Across the current roof layouts"));
  assert.equal(app.writes.length, 0); assert.equal(app.requests.length, 0);
});

test("overview plan is read-only and does not offer editor controls or create edits", async t => {
  const app = await mount(t, { geometry: structuredClone(flat) });
  const view = document.querySelector(".lp-overview .lp-plan-view"), svg = view.querySelector("svg");
  assert.equal(view.querySelector("button"), null); assert.equal(view.querySelector(".lp-profile-help"), null);
  await act(async () => { for (const type of ["pointerdown", "pointermove", "pointerup"]) svg.dispatchEvent(new window.MouseEvent(type, { bubbles: true, button: 0, clientX: 40, clientY: 40 })); svg.dispatchEvent(new window.KeyboardEvent("keydown", { bubbles: true, key: "Enter" })); });
  assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0);
  await click("Open roof workspace", document.querySelector(".lp-overview"));
  assert.equal(document.querySelector(".lp-project").dataset.workspace, "design"); assert.equal(document.activeElement.id, "lp-design");
});

test("switching workspaces retains the same raw inputs and one shared undo/redo document including source metadata", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const app = await mount(t, { geometry: structuredClone(flat), brief, locale: "de-DE" });
  const input = annual(); await choose("Energy inputs"); await enter(input, "25,5"); await until(() => app.writes.length > 0);
  const afterEdit = app.writes.at(-1).draft; assert.equal(afterEdit.history.past.length, 1); assert.deepEqual(afterEdit.history.current.geometry, flat); assert.deepEqual(afterEdit.history.current.preserved_extension, { fixture: "exact" });
  await choose("Project overview"); assert.equal(annual(), input); assert.equal(input.value, "25,5"); assert.equal(metric("Annual consumption"), "25,5 kWh");
  assert.equal(document.activeElement.id, "lp-overview"); const writes = app.writes.length;
  await choose("Site and project"); await choose("Roof design"); await choose("Energy inputs"); assert.equal(app.writes.length, writes);
  await act(async () => document.querySelector('button[aria-label="Undo"]').click()); assert.equal(input.value, "10");
  await act(async () => document.querySelector('button[aria-label="Redo"]').click()); assert.equal(input.value, "25,5"); assert.deepEqual(app.writes.at(-1).draft.history.current.geometry, flat);
  await enter(input, "1,,"); await choose("Site and project"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "energy"); assert.equal(input.value, "1,,");
  await act(async () => input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }))); await choose("Site and project"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "site");
});

test("unapplied geometry form blocks navigation until explicit cancel and keeps the raw values", async t => {
  const app = await mount(t, { hash: "#lp-design" });
  await click("Add roof face"); const form = document.querySelector(".lp-geometry-form"), name = form.querySelector('[name="name"]'); await enter(name, "Unapplied synthetic roof");
  await choose("Project overview"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "design"); assert.equal(document.querySelector(".lp-geometry-form"), form); assert.equal(name.value, "Unapplied synthetic roof"); assert.equal(app.writes.length, 0);
  await click("Cancel properties"); await choose("Project overview"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "overview"); assert.equal(app.writes.length, 0);
});

test("an in-progress CSV file selection and raw delimiter remain mounted across workspace switches", async t => {
  const app = await mount(t, { hash: "#lp-load" });
  await click("Import interval data"); const file = document.querySelector('input[type="file"]'); assert.ok(file);
  const bytes = new TextEncoder().encode("time;load\n2026-01-01T00:00:00Z;1\n");
  Object.defineProperty(file, "files", { configurable: true, value: [{ name: "journal-preserved.csv", size: bytes.byteLength, arrayBuffer: async () => bytes.buffer }] });
  await act(async () => file.dispatchEvent(new window.Event("change", { bubbles: true })));
  await until(() => document.querySelector(".lp-file-name")?.textContent === "journal-preserved.csv");
  const delimiter = [...document.querySelectorAll("select")].find(n => document.getElementById(n.getAttribute("aria-labelledby"))?.textContent.includes("Column delimiter"));
  await act(async () => { delimiter.value = ";"; delimiter.dispatchEvent(new window.Event("change", { bubbles: true })); });
  await choose("Roof design"); await choose("Energy inputs");
  assert.equal(document.querySelector('input[type="file"]'), file); assert.equal(document.querySelector(".lp-file-name").textContent, "journal-preserved.csv"); assert.equal(delimiter.value, ";"); assert.equal(app.sends.length, 0);
});

test("revoked scope cannot switch the workspaces or alter its URL fragment", async t => {
  const app = await mount(t); app.revoke(); const hash = location.hash; await choose("Roof design"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "overview"); assert.equal(location.hash, hash); assert.equal(app.writes.length, 0);
});

test("a completed geometry property edit remains one shared history step across the overview", async t => {
  const app = await mount(t, { hash: "#lp-design", geometry: structuredClone(flat) });
  await click("Fixture array"); await click("Edit numeric properties");
  await enter(document.querySelector('[name="rows"]'), "3"); await click("Apply properties");
  await until(() => app.writes.length > 0);
  const applied = app.writes.at(-1).draft;
  assert.equal(applied.history.past.length, 1); assert.equal(applied.history.current.geometry.arrays[0].rows, 3); assert.deepEqual(applied.history.current.geometry.sources, flat.sources);
  await choose("Project overview"); assert.equal(metric("Included modules"), "8"); assert.equal(metric("Declared DC nameplate power"), "4 kWp");
  await act(async () => document.querySelector('button[aria-label="Undo"]').click()); assert.equal(metric("Included modules"), "5"); assert.equal(metric("Declared DC nameplate power"), "2.5 kWp");
  await act(async () => document.querySelector('button[aria-label="Redo"]').click()); assert.equal(metric("Included modules"), "8"); assert.equal(app.sends.length, 0);
});

test("SPEC COUNTEREXAMPLE: Site workspace navigation must reveal its first project-use/system-scope section", async t => {
  await mount(t); await choose("Site and project");
  const first = document.querySelector("#lp-brief-use"), locationSection = document.querySelector("#lp-site");
  assert.equal(first.hidden, false); assert.equal(locationSection.hidden, false);
  assert.ok(first.compareDocumentPosition(locationSection) & window.Node.DOCUMENT_POSITION_FOLLOWING);
  // Native scrolling is the parent's separate evidence. This independent DOM
  // assertion proves the wrong later-section focus/destination at fixed563.
  assert.equal(document.activeElement.id, "lp-brief-use");
});
