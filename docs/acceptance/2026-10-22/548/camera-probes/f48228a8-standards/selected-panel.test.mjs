import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { Vector3 } from "three/webgpu";
import { readGeometry } from "../src/domain/validateGeometry.ts";
import { panelPoses } from "../src/domain/panelPoses.ts";
import { roofPlane } from "../src/domain/geometryEditing.ts";
import { sceneViewDirection } from "../src/domain/sceneCamera.ts";

test("selecting an actual panel instance uses the same owning roof as selecting its array", async () => {
  const raw = JSON.parse(await readFile(new URL("../../../fixtures/planning/geometry-flat.json", import.meta.url)));
  const policy = JSON.parse(await readFile(new URL("../src/contracts/geometry-policy.json", import.meta.url)));
  const second = { ...raw.roofs[0], id: "second", name: "Second synthetic roof",
    ...roofPlane(60, 180, [110, -20, 4]) };
  raw.roofs.push(second);
  raw.layout_rules.push({ ...raw.layout_rules[0], roof_id: second.id });
  raw.arrays[0].roof_id = second.id;
  const doc = readGeometry(raw, policy), before = JSON.stringify(doc);
  const pose = panelPoses(doc)[0];
  assert.equal(pose.roof_id, second.id);
  const expected = sceneViewDirection(doc, second.id);
  assert.deepEqual(sceneViewDirection(doc, pose.array_id), expected, "array ownership control");
  const actual = sceneViewDirection(doc, pose.id);
  console.log(JSON.stringify({ actualPanelId: pose.id, actualRoofId: pose.roof_id, expectedDirection: expected,
    actualDirection: actual, firstRoofDirection: sceneViewDirection(doc, doc.roofs[0].id) }));
  assert.equal(JSON.stringify(doc), before);
  assert.ok(new Vector3(...actual).distanceTo(new Vector3(...expected)) < 1e-12,
    "Fit after selecting a panel must face that panel's roof, not the first roof");
});
