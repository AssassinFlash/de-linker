// Real React and pinned application, using the existing fake-map/JSDOM fixture.
// Geometry restore models common undo's document update; no native scroll claim.
import assert from "node:assert/strict";
import { createRequire, register } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const app = process.cwd();
assert.ok(app.endsWith("/apps/planner"));
const require = createRequire(resolve(app, "package.json"));
const { act } = require("react");
register("./pinned-fixture-loader.mjs", import.meta.url);
const moduleAt = (path) => import(pathToFileURL(resolve(app, path)).href);
const { rig, geometry, button } = await import(pathToFileURL(resolve(app, "tests/map-roof-workspace.test.mjs")).href + "?review_harness=1");
const { until, enter } = await moduleAt("tests/dom-fixture.mjs");
const cleanup = [];
const r = await rig({ after: (callback) => cleanup.push(callback) });
try {
  await r.click("Start roof drawing");
  await until(() => r.active);
  for (const point of [[6.96, 50.94], [6.9601, 50.94], [6.9601, 50.9401]]) await r.point(...point);
  await r.click("Close outline and review");
  await until(() => document.querySelector(".lp-drawing-properties"));
  for (const [name, value] of Object.entries({ name: "Synthetic repeat submission", pitch: "30", bearing: "180", height: "8.125", source: "Synthetic drawing", rights: "Synthetic permission", calibration: "Synthetic coordinates, not a survey" })) {
    await enter(document.querySelector(`[name="${name}"]`), value);
  }
  await act(async () => document.querySelector('.lp-drawing-properties input[type="checkbox"]').click());
  const submit = async () => {
    await act(async () => {
      button("Check and add roof face").focus();
      document.querySelector(".lp-drawing-properties").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
    });
  };
  await submit();
  await until(() => !r.active && r.commits.length === 1);
  const firstFocusedResult = document.activeElement.classList.contains("lp-map-drawing");
  assert.equal(firstFocusedResult, true);
  await r.replaceGeometry(geometry);
  assert.match(document.querySelector(".lp-drawing-status").textContent, /Drawing paused and retained/);
  await r.click("Resume drawing");
  await until(() => r.active && document.querySelector(".lp-drawing-properties"));
  // No field/corner changes: a new accepted submit is still a new action.
  await submit();
  await until(() => !r.active && r.commits.length === 2);
  const secondFocusedResult = document.activeElement.classList.contains("lp-map-drawing");
  assert.equal(secondFocusedResult, false);
  assert.match(document.querySelector(".lp-drawing-status").textContent, /Roof added to the project draft/);
  console.log(JSON.stringify({
    pin: "786d0db99203d35010b6a7fdc38dc984b3058606",
    first_success_focused_result: firstFocusedResult,
    repeated_success_focused_result: secondFocusedResult,
    repeated_success_focus_tag: document.activeElement.tagName,
    accepted_commands: r.commits.length,
    query_count: r.queries.length,
    input_changes_between_submits: 0,
    geometry_restore_status_truthful: true,
    source: "Fixed-pin application loaded in memory; unchanged installed React; existing JSDOM/fake Map and synthetic engine fixture",
    boundary: "Focus/effect regression only; does not establish native scroll, actual engine refusal or production acceptance",
  }, null, 2));
} finally {
  for (const callback of cleanup.reverse()) await callback();
}
