import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { GeographicBridge, geographicOnRoof, horizontalOnRoof } from "./apps/planner/src/domain/geographic.ts";
import { readGeometryImportCommand, readPreparedGeometryImport, attachGeometryImport } from "./apps/planner/src/domain/geometryImports.ts";
import { emptyGeometry } from "./apps/planner/src/domain/geometryCommands.ts";
import { beginDraft, editDraft, undoDraft, redoDraft } from "./apps/planner/src/domain/draft.ts";

const source = JSON.parse(readFileSync(new URL("./fixtures/planning/geometry-import-asset.json", import.meta.url), "utf8"));
const reference = { schema_version: 1, method: "wgs84_cart_topocentric_v1", longitude_deg: 0, latitude_deg: 0, ellipsoid_height_m: 0, height_basis: "zero_height_horizontal_convention" };
const bridge = new GeographicBridge(reference);
const plane = (origin = [0, 0, 0], v = [0, 1, 0]) => ({ origin_enu: origin, u_axis_enu: [1, 0, 0], v_axis_enu: v });
function close(actual, expected, budget = 2e-9) { assert.ok(Math.abs(actual - expected) <= budget, `${actual} != ${expected}`); }

test("independent analytic oblique equatorial line and translated local solve", () => {
  for (const up of [-100, 0, 20]) for (const longitude of [-40, -.001, .001, 40]) {
    const actual = geographicOnRoof(bridge, plane([-.25, .5, up], [0, .8, -.6]), [longitude, 0]);
    const expectedV = -.5 / .8;
    close(actual[1], expectedV);
    close(actual[0], (6378137 + up - .6 * expectedV) * Math.tan(longitude * Math.PI / 180) + .25);
  }
  for (const up of [0, 5, 1e9, 1e15]) close(horizontalOnRoof(plane([0, 0, up], [0, .8, -.6]), [0, .1])[1], .125, 1e-16);
});

test("browser facing, UV spacing, ENU spacing and inverse branch guards remain independent", () => {
  for (const [longitude, p] of [
    [179.9999, plane([0, 0, 5])], [89.9999, plane([0, 0, 5])], [90, plane()],
    [Math.atan(1e7 / 6378137) * 180 / Math.PI, plane([1e7, 0, 0])],
    [0, plane([-1e7, 0, 0])], [0, plane([0, 0, -6378137 - 100])],
  ]) assert.throws(() => geographicOnRoof(bridge, p, [longitude, 0]));
  const longitude = 89.99, base = bridge.forward([longitude, 0, 0]);
  close(geographicOnRoof(bridge, plane([0, 0, base[2]]), [longitude, 0])[0], base[0]);
  const uv = geographicOnRoof(bridge, plane([0, 0, -100]), [.001, 0]);
  assert.ok(bridge.inverse([uv[0], uv[1], -100])[2] < 0);
});

test("legacy recovery command is preserved without becoming a newly attachable candidate", () => {
  const command = { schema_version: 1, project_id: source.project_id, content_base64: "eA==", options: structuredClone(source.metadata.geometry_import_options), key: "00000000-0000-4000-8000-000000000001" };
  delete command.options.plane_intersection_method;
  const checked = readGeometryImportCommand(command);
  assert.equal(Object.hasOwn(checked.options, "plane_intersection_method"), false);
  for (const method of [undefined, null, "unknown_method"]) {
    const old = structuredClone(source);
    if (method === undefined) delete old.metadata.geometry_import_options.plane_intersection_method;
    else old.metadata.geometry_import_options.plane_intersection_method = method;
    delete old.metadata.geometry_import.plane_intersection_method;
    assert.throws(() => readPreparedGeometryImport(old, source.project_id));
  }
});

test("owned candidate, source attachment, openings and unrelated inputs share one history step", () => {
  const candidate = readPreparedGeometryImport(source, source.project_id), before = emptyGeometry();
  const inputs = { brief: { synthetic: true }, profile_selections: { retained: "exactly" } };
  const changed = attachGeometryImport(inputs, before, candidate);
  assert.deepEqual(inputs, { brief: { synthetic: true }, profile_selections: { retained: "exactly" } });
  assert.deepEqual(changed.geometry.roofs[0].holes_uv, candidate.geometry.roofs[0].holes_uv);
  assert.equal(changed.geometry.sources[0].reference_sha256, source.content_sha256);
  assert.equal(changed.geometry_imports.selected[candidate.geometry.sources[0].id], source.id);
  const initial = beginDraft({ id: source.project_id, title: "Synthetic", revision: 1, input_sha256: "a".repeat(64), inputs });
  const draft = editDraft(initial, changed);
  assert.deepEqual(undoDraft(draft).history.current, inputs);
  assert.deepEqual(redoDraft(undoDraft(draft)).history.current, changed);
  const mutated = structuredClone(before); mutated.coordinate_system.anchor = { longitude_deg: 1, latitude_deg: 0, datum: "EPSG:4326", source_id: "not_present" };
  assert.throws(() => attachGeometryImport({ geometry: mutated }, before, candidate));
});
