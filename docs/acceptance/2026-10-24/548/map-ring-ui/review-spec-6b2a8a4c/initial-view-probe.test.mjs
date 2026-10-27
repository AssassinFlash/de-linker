// Actual DesignEditor state test; map renderer and browser layout are fixtures.
// This proves one-time view initialization, not native reload or GPU behavior.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, register } from "node:module";
import { execFileSync } from "node:child_process";
import test from "node:test";
const repo = new URL("../../../../../../", import.meta.url);
const app = new URL("apps/planner/", repo);
const pin = "6b2a8a4cc43c95d4710fcb42f16d1bd1e4a8c100";
assert.equal(execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo, encoding: "utf8" }).trim(), pin);
for (const path of ["src/components/ProjectEditor.tsx", "src/components/design/DesignEditor.tsx"])
  assert.deepEqual(readFileSync(new URL(path, app)), execFileSync("git", ["show", pin + ":apps/planner/" + path], { cwd: repo }));
const require = createRequire(new URL("package.json", app));
const React = require("react"), { act } = React;
const { IDBFactory } = require("fake-indexeddb");
register(new URL("tests/map-library-loader.mjs", app), import.meta.url);
const { setupDom, until } = await import(new URL("tests/dom-fixture.mjs", app));
const { DesignEditor } = await import(new URL("src/components/design/DesignEditor.tsx", app));
const asset = JSON.parse(readFileSync(new URL("fixtures/planning/geometry-import-asset.json", repo), "utf8"));

test("map entry initializes once, later renders preserve a chosen Plan, and normal entry defaults to Plan", async (t) => {
  const dom = setupDom(), scope = "f".repeat(64), commits = [], queries = [];
  const values = {
    indexedDB: new IDBFactory(), MutationObserver: window.MutationObserver,
    getComputedStyle: window.getComputedStyle.bind(window),
    requestAnimationFrame: (callback) => setTimeout(() => callback(Date.now()), 0),
    cancelAnimationFrame: clearTimeout,
  };
  const previous = new Map(Object.keys(values).map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  for (const [name, value] of Object.entries(values))
    Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
  const style = document.createElement("style");
  style.textContent = ".lp-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#123456;--proto-neutral-600:#456789;--proto-teal-700:#0a665c;--proto-teal-400:#44bbcc;--proto-neutral-100:#eeeeee;}";
  document.head.append(style);
  const { createRoot } = await import(require.resolve("react-dom/client"));
  const root = createRoot(dom.element);
  t.after(async () => {
    await dom.dispose(root);
    for (const [name, descriptor] of previous)
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
  });
  const props = {
    geometry: asset.metadata.geometry_import.geometry,
    confirmedGeometry: asset.metadata.geometry_import.geometry,
    projectId: asset.project_id, locale: "en-GB", session: { query_scope: scope },
    recoveryScopes: [scope], client: { isCurrentScope: (value) => value === scope,
      query(...args) { queries.push(args); throw new Error("unexpected_query"); } },
    commit(command) { commits.push(command); return true; }, onValidity() {}, recheck() {}, attachImport() { return false; },
  };
  const button = (label) => [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === label);
  const render = async (extra) => act(async () => root.render(React.createElement(DesignEditor, { ...props, ...extra })));
  await render({ initialMapView: true });
  await until(() => document.querySelector(".lp-map-workspace"));
  assert.equal(button("Map").getAttribute("aria-pressed"), "true");
  await act(async () => button("Plan").click());
  assert.equal(button("Plan").getAttribute("aria-pressed"), "true");
  await render({ initialMapView: false });
  await render({ initialMapView: true, geometry: structuredClone(props.geometry) });
  assert.equal(button("Plan").getAttribute("aria-pressed"), "true");
  assert.equal(button("Map").getAttribute("aria-pressed"), "false");
  await act(async () => root.render(null));
  await render({});
  assert.equal(button("Plan").getAttribute("aria-pressed"), "true");
  assert.equal(commits.length, 0);
  assert.equal(queries.length, 0);
  console.log(JSON.stringify({ pin, initial_map: true, chosen_plan_preserved_on_rerender: true,
    default_plan: true, domain_commands: commits.length, queries: queries.length }));
});
