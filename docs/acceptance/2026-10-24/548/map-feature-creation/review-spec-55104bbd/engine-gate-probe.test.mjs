// Independent fixed-source Spec probe. Real React, application journal/domain,
// and Python review_geometry/Shapely. JSDOM and the existing MapLibre port are
// fixtures; no native/GPU/touch/HTTP/engineering-release claim is made.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, register } from "node:module";
import { execFileSync, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const rootURL = new URL("../../../../../../", import.meta.url);
const appURL = new URL("apps/planner/", rootURL);
const rootPath = fileURLToPath(rootURL);
const pin = "55104bbdbbf9e694eba4785787daaaf109b99ed8";
const sourcePaths = ["apps/planner/src", "apps/planner/tests", "services/engine/src", "fixtures/planning/geometry-import-asset.json"];
function verifyPin() {
  assert.equal(execFileSync("git", ["rev-parse", "HEAD"], { cwd: rootPath, encoding: "utf8" }).trim(), pin);
  assert.equal(execFileSync("git", ["diff", pin, "--", ...sourcePaths], { cwd: rootPath, encoding: "utf8" }), "");
}
verifyPin();
const require = createRequire(new URL("package.json", appURL));
const React = require("react"), { act, useState } = React;
const { IDBFactory } = require("fake-indexeddb");
register(new URL("tests/map-library-loader.mjs", appURL), import.meta.url);
const { setupDom, until } = await import(new URL("tests/dom-fixture.mjs", appURL));
const { MapDrawingWorkspace } = await import(new URL("src/components/design/MapDrawingWorkspace.tsx", appURL));
const { mapDrawingDraftStore } = await import(new URL("src/data/MapDrawingDraftStore.ts", appURL));
const { startMapFeatureDraft } = await import(new URL("src/domain/mapFeatureDraft.ts", appURL));
const { appendMapDrawingVertex, mapDrawingDraftCommand } = await import(new URL("src/domain/mapDrawingDraft.ts", appURL));
const { applyGeometryCommand } = await import(new URL("src/domain/geometryCommands.ts", appURL));
const asset = JSON.parse(readFileSync(new URL("fixtures/planning/geometry-import-asset.json", rootURL), "utf8"));
const scope = "d".repeat(64);
const python = fileURLToPath(new URL("services/engine/.venv/bin/python", rootURL));
const engineSource = fileURLToPath(new URL("services/engine/src", rootURL));
const valid = [[6.96001, 50.94001], [6.96004, 50.94001], [6.96004, 50.94004], [6.960025, 50.940025], [6.96001, 50.94004]];
const crossing = [[6.96001, 50.94001], [6.96004, 50.94004], [6.96001, 50.94004], [6.96004, 50.94001]];
const crossedBoundary = [[0, 0], [14, 14], [0, 14], [14, 0]];
function realReview(geometry, target) {
  const run = spawnSync(python, ["-c", `
import json, sys, shapely
from shapely.geometry import Polygon
from linker_engine.planning.geometry_review import review_geometry
request = json.load(sys.stdin)
geometry, target = request['geometry'], request['target']
roof = next(item for item in geometry['roofs'] if item['id'] == target['roof_id'])
if target['kind'] == 'hole':
    ring = roof['holes_uv'][-1]
else:
    collection = geometry['obstacles' if target['kind'] == 'obstacle' else 'keepouts']
    ring = next(item for item in collection if item['id'] == target['id'])['footprint_uv']
report = review_geometry(geometry)
print(json.dumps({'report': report, 'target_valid': Polygon(ring).is_valid,
    'parent_valid': Polygon(roof['boundary_uv'], roof['holes_uv']).is_valid,
    'shapely': shapely.__version__, 'geos': shapely.geos_version_string}))
`], { input: JSON.stringify({ geometry, target }), encoding: "utf8", cwd: rootPath,
    env: { ...process.env, PYTHONPATH: engineSource, PYTHONDONTWRITEBYTECODE: "1" } });
  assert.equal(run.status, 0, run.stderr);
  return JSON.parse(run.stdout);
}

const cases = ["hole", "obstacle", "keepout"].flatMap(kind => [
  { kind, scenario: "valid_concave", expected: 1 },
  { kind, scenario: "invalid_target", expected: 0 },
  { kind, scenario: "invalid_parent", expected: 0 },
  { kind, scenario: "unrelated_invalid_roof", expected: 1 },
]);
cases.push(
  { kind: "obstacle", scenario: "incomplete_numerical_report", expected: 0 },
  { kind: "keepout", scenario: "truncated_report", expected: 0 },
  { kind: "obstacle", scenario: "stale_frame_reply", expected: 0 },
  { kind: "keepout", scenario: "changed_identity_reply", expected: 0 },
  { kind: "obstacle", scenario: "unknown_prepared_write", expected: 0 },
);
for (const { kind, scenario, expected } of cases) {
  test(`${kind}: ${scenario}`, async t => {
    const dom = setupDom();
    const globals = ["indexedDB", "MutationObserver", "getComputedStyle", "requestAnimationFrame", "cancelAnimationFrame"];
    const previous = new Map(globals.map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
    Object.defineProperty(globalThis, "indexedDB", { value: new IDBFactory(), configurable: true });
    globalThis.MutationObserver = window.MutationObserver;
    globalThis.getComputedStyle = window.getComputedStyle.bind(window);
    globalThis.requestAnimationFrame = fn => setTimeout(() => fn(Date.now()), 0);
    globalThis.cancelAnimationFrame = clearTimeout;
    const style = document.createElement("style");
    style.textContent = ".lp-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#123456;--proto-neutral-600:#456789;--proto-teal-700:#0a665c;--proto-teal-400:#44bbcc;--proto-neutral-100:#eeeeee;}";
    document.head.append(style);
    for (const record of await mapDrawingDraftStore.list([scope], asset.project_id)) await mapDrawingDraftStore.clear(scope, record.body);
    const before = structuredClone(asset.metadata.geometry_import.geometry);
    before.roofs[0].holes_uv = [];
    before.sources[0].permissions.export = "prohibited";
    before.sources.push({ ...structuredClone(before.sources[0]), id: "spec_existing_source", note: "Independent synthetic measurement source", spatial_precision_m: 0.01, permissions: { derive: "permitted", retain: "permitted", export: "unknown" } });
    if (scenario === "invalid_parent") before.roofs[0].boundary_uv = crossedBoundary;
    if (scenario === "unrelated_invalid_roof") before.roofs.push({ ...structuredClone(before.roofs[0]), id: "spec_unrelated_roof", name: "Synthetic unrelated invalid roof", boundary_uv: crossedBoundary });
    if (scenario === "incomplete_numerical_report") before.roofs.push({ ...structuredClone(before.roofs[0]), id: "spec_unrelated_roof", name: "Synthetic unsupported UV chart", boundary_uv: [[1e9, 0], [1e9 + 10, 0], [1e9 + 10, 10], [1e9, 10]] });
    if (scenario === "truncated_report") for (let i = 0; i < 201; i++) before.roofs.push({ ...structuredClone(before.roofs[0]), id: `spec_unrelated_${i}`, name: "Synthetic unrelated invalid roof", boundary_uv: crossedBoundary });
    let draft = startMapFeatureDraft(asset.project_id, before, "de-DE", { kind, roof_id: before.roofs[0].id });
    for (const point of scenario === "invalid_target" ? crossing : valid) draft = appendMapDrawingVertex(draft, point);
    draft = { ...draft, phase: "staged", fields: { ...draft.fields, name: kind === "hole" ? "" : "Synthetic new feature", height: kind === "obstacle" ? "1,25" : "", axis: kind === "obstacle" ? "normal" : "", reason: kind === "keepout" ? "Synthetic local exclusion" : "", source_id: kind === "hole" ? before.roofs[0].source_id : "spec_existing_source", source_confirmed: true } };
    await mapDrawingDraftStore.write(scope, null, JSON.stringify(draft));
    const candidate = applyGeometryCommand(before, mapDrawingDraftCommand(draft));
    assert.deepEqual(candidate.sources, before.sources);
    assert.deepEqual(candidate.coordinate_system, before.coordinate_system);
    assert.deepEqual(candidate.roofs[0].origin_enu, before.roofs[0].origin_enu);
    assert.deepEqual(candidate.roofs[0].u_axis_enu, before.roofs[0].u_axis_enu);
    assert.deepEqual(candidate.roofs[0].v_axis_enu, before.roofs[0].v_axis_enu);
    assert.deepEqual(candidate.roofs[0].boundary_uv, before.roofs[0].boundary_uv);
    if (kind !== "hole") assert.deepEqual(candidate.roofs, before.roofs);
    const commits = [], reports = [];
    let active = false, currentScope = scope, replaceGeometry, releaseReply;
    const hold = new Promise(resolve => { releaseReply = resolve; });
    const client = { isCurrentScope: value => value === currentScope,
      query: async (path, input) => {
        assert.equal(path, "geometry/review");
        assert.deepEqual(input.geometry, candidate);
        const actual = realReview(input.geometry, { ...draft.target, id: draft.object_id });
        reports.push(actual);
        if (["stale_frame_reply", "changed_identity_reply"].includes(scenario)) await hold;
        // Runtime metadata belongs to the HTTP route. Only this envelope field
        // is a fixed marker; geometry and every diagnostic are native engine output.
        return { ...actual.report, runtime_sha256: "b".repeat(64) };
      } };
    const { createRoot } = await import(require.resolve("react-dom/client"));
    const root = createRoot(dom.element);
    function Harness() {
      const [geometry, setGeometry] = useState(before);
      replaceGeometry = setGeometry;
      return React.createElement(MapDrawingWorkspace, { geometry, confirmedGeometry: before,
        projectId: asset.project_id, locale: "en-GB", session: { query_scope: scope }, client,
        recheck() {}, recoveryScopes: [scope], onActivity(value) { active = value; },
        commit(command) { commits.push(command); setGeometry(previous => applyGeometryCommand(previous, command)); return true; },
        mapModuleUrl: null, poses: [], selected: before.roofs[0].id, select() {}, disabled: false, openReferences() {}, camera: { current: null } });
    }
    const originalWrite = mapDrawingDraftStore.write;
    if (scenario === "unknown_prepared_write") mapDrawingDraftStore.write = async function (grant, prior, next) {
      await originalWrite.call(this, grant, prior, next);
      if (JSON.parse(next).prepared_geometry) throw new Error("synthetic_lost_acknowledgement_after_write");
    };
    t.after(async () => {
      mapDrawingDraftStore.write = originalWrite;
      await dom.dispose(root);
      for (const [name, descriptor] of previous) if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
    });
    const button = name => [...document.querySelectorAll("button")].find(node => node.textContent.trim() === name);
    await act(async () => root.render(React.createElement(Harness)));
    await until(() => button("Open saved drawing") && !button("Open saved drawing").disabled);
    await act(async () => button("Open saved drawing").click());
    await until(() => document.querySelector("#lp-map-feature-properties"));
    await act(async () => document.querySelector("#lp-map-feature-properties").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true })));
    await until(() => reports.length === 1);
    if (scenario === "stale_frame_reply") await act(async () => replaceGeometry({ ...before, roofs: before.roofs.map(roof => ({ ...roof, name: roof.name + " changed" })) }));
    if (scenario === "changed_identity_reply") currentScope = "f".repeat(64);
    if (["stale_frame_reply", "changed_identity_reply"].includes(scenario)) await act(async () => releaseReply());
    await until(() => !document.body.textContent.includes("Checking boundary geometry"));
    const retained = await mapDrawingDraftStore.list([scope], asset.project_id);
    assert.equal(retained.length, 1);
    assert.deepEqual(retained[0].drawing.vertices, draft.vertices);
    assert.equal(retained[0].drawing.locale, "de-DE");
    assert.equal(retained[0].drawing.object_id, draft.object_id);
    assert.deepEqual(retained[0].drawing.fields, draft.fields);
    const actual = reports[0];
    const summary = { pin, kind, scenario, commits: commits.length, expected_commits: expected,
      target_valid: actual.target_valid, parent_valid: actual.parent_valid, active,
      report_complete: actual.report.review_complete, diagnostics_truncated: actual.report.diagnostics_truncated,
      issue_count: actual.report.issue_count, diagnostic_count: actual.report.issues.length,
      issue_kinds: [...new Set(actual.report.issues.map(issue => issue.kind))],
      shapely: actual.shapely, geos: actual.geos, retained_original_locale: true, source_plane_exact: true,
      prepared: Boolean(retained[0].drawing.prepared_geometry), status: document.querySelector(".lp-drawing-status")?.textContent };
    console.log("REAL_ENGINE_SPEC " + JSON.stringify(summary));
    assert.equal(commits.length, expected);
    if (scenario === "invalid_target") assert.equal(actual.target_valid, false);
    if (scenario === "invalid_parent") assert.equal(actual.parent_valid, false);
    if (scenario === "incomplete_numerical_report") assert.equal(actual.report.review_complete, false);
    if (scenario === "truncated_report") assert.equal(actual.report.diagnostics_truncated, true);
    if (expected === 0 && scenario !== "unknown_prepared_write") assert.equal(retained[0].drawing.prepared_geometry, null);
    // Persistence and the product's sameJson contract compare JSON. JSON has
    // one zero value, so the normal's in-memory -0 is canonically written as 0.
    if (scenario === "unknown_prepared_write") assert.deepEqual(retained[0].drawing.prepared_geometry, JSON.parse(JSON.stringify(candidate)));
  });
}
test.after(() => verifyPin());
