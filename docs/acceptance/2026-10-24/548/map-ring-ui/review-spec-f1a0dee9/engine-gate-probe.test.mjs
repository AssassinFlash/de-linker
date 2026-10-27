// Independent repair recheck copied from the preserved a128 counterexample.
// Adds real-engine controls: an unrelated invalid roof must not block a valid target.
// Fixed-source Spec counterexample. Actual React/workspace/journal/domain,
// installed Terra + adapter, and actual Python review_geometry/Shapely.
// JSDOM and the existing MapLibre port are fixtures: no native UI/HTTP claim.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, register } from "node:module";
import { execFileSync, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const rootURL = new URL("../../../../../../", import.meta.url);
const appURL = new URL("apps/planner/", rootURL);
const rootPath = fileURLToPath(rootURL);
const pin = "f1a0dee90dd719ce5532724a9f6e9021f1555705";
assert.equal(execFileSync("git", ["rev-parse", "HEAD"], { cwd: rootPath, encoding: "utf8" }).trim(), pin);
assert.deepEqual(readFileSync(new URL("src/components/design/MapDrawingWorkspace.tsx", appURL)), execFileSync("git", ["show", pin + ":apps/planner/src/components/design/MapDrawingWorkspace.tsx"], { cwd: rootPath }));
const require = createRequire(new URL("package.json", appURL));
const React = require("react"), { act, useState } = React;
const { IDBFactory } = require("fake-indexeddb");
register(new URL("tests/map-library-loader.mjs", appURL), import.meta.url);
const { setupDom, until } = await import(new URL("tests/dom-fixture.mjs", appURL));
const { MapDrawingWorkspace } = await import(new URL("src/components/design/MapDrawingWorkspace.tsx", appURL));
const { mapDrawingDraftStore } = await import(new URL("src/data/MapDrawingDraftStore.ts", appURL));
const { applyGeometryCommand } = await import(new URL("src/domain/geometryCommands.ts", appURL));
const { maps } = await import(new URL("tests/map-library-fixture.mjs", appURL));
const asset = JSON.parse(readFileSync(new URL("fixtures/planning/geometry-import-asset.json", rootURL), "utf8"));
const scope = "e".repeat(64);
const python = fileURLToPath(new URL("services/engine/.venv/bin/python", rootURL));
const engineSource = fileURLToPath(new URL("services/engine/src", rootURL));
const evidence = [];

function review(geometry, target) {
  const run = spawnSync(python, ["-c", `
import json, sys, shapely
from shapely.geometry import Polygon
from linker_engine.planning.geometry_review import review_geometry
request = json.load(sys.stdin)
geometry, target = request['geometry'], request['target']
items = geometry['obstacles' if target['kind'] == 'obstacle' else 'keepouts']
edited = next(item for item in items if item['id'] == target['id'])
report = review_geometry(geometry)
print(json.dumps({'report': report, 'target_valid': Polygon(edited['footprint_uv']).is_valid,
    'parent_valid': Polygon(geometry['roofs'][0]['boundary_uv']).is_valid,
    'shapely': shapely.__version__, 'geos': shapely.geos_version_string}))
`], {
    input: JSON.stringify({ geometry, target }), encoding: "utf8", cwd: rootPath,
    env: { ...process.env, PYTHONPATH: engineSource, PYTHONDONTWRITEBYTECODE: "1" },
  });
  assert.equal(run.status, 0, run.stderr);
  return JSON.parse(run.stdout);
}

for (const { kind, invalidParent } of ["obstacle", "keepout"].flatMap((kind) => [
  { kind, invalidParent: true }, { kind, invalidParent: false },
])) {
  test(`${kind}: ${invalidParent ? "invalid parent refuses unchecked crossing edit" : "unrelated invalid roof permits checked valid edit"}`, async (t) => {
    const dom = setupDom();
    const globals = ["indexedDB", "MutationObserver", "getComputedStyle", "requestAnimationFrame", "cancelAnimationFrame"];
    const previous = new Map(globals.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
    Object.defineProperty(globalThis, "indexedDB", { value: new IDBFactory(), configurable: true });
    globalThis.MutationObserver = window.MutationObserver;
    globalThis.getComputedStyle = window.getComputedStyle.bind(window);
    globalThis.requestAnimationFrame = (fn) => setTimeout(() => fn(Date.now()), 0);
    globalThis.cancelAnimationFrame = clearTimeout;
    const style = document.createElement("style");
    style.textContent = ".lp-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#123456;--proto-neutral-600:#456789;--proto-teal-700:#0a665c;--proto-teal-400:#44bbcc;--proto-neutral-100:#eeeeee;}";
    document.head.append(style);
    for (const record of await mapDrawingDraftStore.list([scope], asset.project_id))
      await mapDrawingDraftStore.clear(scope, record.body);
    const before = structuredClone(asset.metadata.geometry_import.geometry);
    before.roofs[0].holes_uv = [];
    const invalidBoundary = [[0, 0], [10, 10], [0, 10], [10, 0]];
    if (invalidParent) before.roofs[0].boundary_uv = invalidBoundary;
    else before.roofs.push({ ...structuredClone(before.roofs[0]), id: "spec_unrelated_roof", name: "Synthetic unrelated invalid roof", boundary_uv: invalidBoundary });
    const target = { kind, id: `spec_${kind}` };
    const shape = {
      id: target.id, name: `Synthetic ${kind}`, source_id: before.sources[0].id,
      roof_id: before.roofs[0].id, footprint_uv: [[1, 1], [3, 1], [3, 3], [1, 3]],
    };
    if (kind === "obstacle") before.obstacles = [{ ...shape, height_m: 1, extrusion_axis_enu: [0, 0, 1] }];
    else before.keepouts = [{ ...shape, reason: "Synthetic test exclusion" }];
    const commits = [], reports = [];
    let active = false;
    const client = {
      isCurrentScope: (value) => value === scope,
      query: async (path, input) => {
        assert.equal(path, "geometry/review");
        const actual = review(input.geometry, target);
        reports.push(actual);
        // The route supplies runtime metadata; this fixed marker completes only
        // that envelope. Geometry and every diagnostic above are real engine output.
        return { ...actual.report, runtime_sha256: "b".repeat(64) };
      },
    };
    const { createRoot } = await import(require.resolve("react-dom/client"));
    const root = createRoot(dom.element);
    function Harness() {
      const [geometry, setGeometry] = useState(before);
      return React.createElement(MapDrawingWorkspace, {
        geometry, confirmedGeometry: before, projectId: asset.project_id, locale: "en-GB",
        session: { query_scope: scope }, client, recheck() {}, recoveryScopes: [scope],
        commit(command) { commits.push(command); setGeometry((previous) => applyGeometryCommand(previous, command)); return true; },
        onActivity(value) { active = value; }, mapModuleUrl: null, poses: [], selected: target.id,
        select() {}, disabled: false, openReferences() {}, camera: { current: null },
      });
    }
    t.after(async () => {
      await dom.dispose(root);
      for (const [name, descriptor] of previous)
        if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
    });
    await act(async () => root.render(React.createElement(Harness)));
    const findButton = (name) => [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === name);
    await until(() => findButton("Edit boundary on map") && !findButton("Edit boundary on map").disabled);
    await act(async () => findButton("Edit boundary on map").click());
    await until(() => document.querySelector("#lp-map-ring-properties") && !document.body.textContent.includes("Saving drawing in this browser"));
    const original = (await mapDrawingDraftStore.list([scope], asset.project_id))[0].drawing;
    const map = maps.findLast((value) => !value.removed);
    const scale = 1e7;
    map.project = ({ lng, lat }) => ({ x: lng * scale, y: -lat * scale });
    map.unproject = ({ x, y }) => ({ lng: x / scale, lat: -y / scale });
    const from = original.vertices[1];
    const endpoint = invalidParent ? [
      original.vertices[0][0] - (original.vertices[1][0] - original.vertices[0][0]) / 2,
      (original.vertices[0][1] + original.vertices[2][1]) / 2,
    ] : [from[0] + 0.000001, from[1]];
    const a = map.project({ lng: from[0], lat: from[1] });
    const b = map.project({ lng: endpoint[0], lat: endpoint[1] });
    function pointer(type, x, y, button = 0) {
      const event = new window.Event(type, { bubbles: true, cancelable: true });
      Object.assign(event, { pointerId: 7, pointerType: "mouse", isPrimary: true, button,
        buttons: type === "pointerup" ? 0 : 1, clientX: x, clientY: y });
      map.getCanvas().dispatchEvent(event);
    }
    await act(async () => {
      pointer("pointermove", a.x, a.y, -1);
      pointer("pointerdown", a.x, a.y);
      // A supported small move establishes one actual library drag. The release
      // is a later endpoint, exercising the accepted explicit endpoint correction.
      pointer("pointermove", a.x + 2, a.y);
      pointer("pointermove", a.x + 4, a.y);
      pointer("pointerup", b.x, b.y);
      await Promise.resolve();
    });
    await until(() => !document.body.textContent.includes("Saving drawing in this browser"));
    const edited = (await mapDrawingDraftStore.list([scope], asset.project_id))[0].drawing;
    assert.notDeepEqual(edited.metric_vertices, original.metric_vertices, "actual pointer transaction must change the target");
    await act(async () => document.querySelector('[name="source_confirmed"]').click());
    await act(async () => document.querySelector("#lp-map-ring-properties").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true })));
    await until(() => reports.length === 1 && !document.body.textContent.includes("Checking boundary geometry"));
    const actual = reports[0];
    assert.equal(actual.parent_valid, !invalidParent);
    assert.equal(actual.target_valid, !invalidParent, "candidate validity is established by actual Shapely, not an injected diagnostic");
    const retained = await mapDrawingDraftStore.list([scope], asset.project_id);
    assert.equal(retained.length, 1);
    assert.deepEqual(retained[0].drawing.metric_vertices, edited.metric_vertices);
    assert.equal(retained[0].drawing.prepared_geometry === null, invalidParent);
    assert.equal(active, invalidParent);
    const result = { pin, target, scenario: invalidParent ? "invalid_parent" : "unrelated_invalid_roof", parent_valid: actual.parent_valid, target_valid: actual.target_valid,
      shapely: actual.shapely, geos: actual.geos, report_complete: actual.report.review_complete,
      diagnostics_truncated: actual.report.diagnostics_truncated, issues: actual.report.issues,
      commits: commits.length, active, prepared: Boolean(retained[0]?.drawing.prepared_geometry),
      pointer_changed_target: true, original_metric: original.metric_vertices, edited_metric: edited.metric_vertices,
      status: document.querySelector(".lp-drawing-status")?.textContent };
    evidence.push(result);
    console.log("FIX_RECHECK " + JSON.stringify(result));
    assert.equal(commits.length, invalidParent ? 0 : 1, "SPEC lines 33-36: refuse unchecked invalid target; retain ordinary unrelated layout conflicts");
  });
}
