import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { act, createElement } from "react";
import { PerspectiveCamera, Vector3, Box3 } from "three/webgpu";
import { setupDom } from "./dom-fixture.mjs";
import SceneViewport from "../src/components/design/SceneViewport.tsx";
import { roofPlane } from "../src/domain/geometryEditing.ts";
import { readGeometry } from "../src/domain/validateGeometry.ts";
import { renderBoundsPoints } from "../src/domain/renderGeometry.ts";
import { sceneViewDirection } from "../src/domain/sceneCamera.ts";
import { panelPoses } from "../src/domain/panelPoses.ts";

const raw = JSON.parse(await readFile(new URL("../../../fixtures/planning/geometry-flat.json", import.meta.url)));
const policy = JSON.parse(await readFile(new URL("../src/contracts/geometry-policy.json", import.meta.url)));
function project(twoRoofs = false) {
  const doc = structuredClone(raw);
  doc.arrays = [];
  doc.module_specs = [];
  doc.roofs[0] = { ...doc.roofs[0], ...roofPlane(36.86989764584402, 0, [10, -20, 4]) };
  if (twoRoofs) {
    const roof = { ...doc.roofs[0], id: "second", name: "Second synthetic roof",
      ...roofPlane(60, 180, [1010, -20, 4]) };
    doc.roofs.push(roof);
    doc.layout_rules.push({ ...doc.layout_rules[0], roof_id: roof.id });
  }
  return readGeometry(doc, policy);
}
const points = doc => renderBoundsPoints(doc, panelPoses(doc), doc.roofs[0].origin_enu).map(p => new Vector3(...p));
function assertFits(doc, camera, message) {
  camera.updateMatrixWorld();
  const projected = points(doc).map(p => p.clone().project(camera).toArray());
  const outside = projected.filter(p => p.some(c => Math.abs(c) >= 1));
  console.log(JSON.stringify({ message, camera: camera.position.toArray(), far: camera.far,
    aspect: camera.aspect, actualCentre: new Box3().setFromPoints(points(doc)).getCenter(new Vector3()).toArray(),
    projected, outside: outside.length }));
  assert.equal(outside.length, 0, message);
}
async function mount(doc, aspect = 1) {
  const dom = setupDom();
  const priorStyle = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
  globalThis.getComputedStyle = dom.dom.window.getComputedStyle.bind(dom.dom.window);
  const camera = new PerspectiveCamera(75, aspect, 0.01, 1000);
  const control = { mounts: 0, unmounts: 0, commits: 0, invalidates: 0, state: { camera,
    size: { width: 500 * aspect, height: 500 }, invalidate: () => control.invalidates++ } };
  globalThis.__cameraProbe = control;
  const { createRoot } = await import("react-dom/client");
  const root = createRoot(dom.element);
  let document = doc, selected = null;
  async function render(next = document, selection = selected) {
    document = next; selected = selection;
    await act(async () => root.render(createElement(SceneViewport, { document, poses: panelPoses(document),
      selected, select() {}, commit() { control.commits++; return true; }, disabled: false })));
  }
  await render();
  return { camera, control, dom, render,
    fit: async () => { const button = [...dom.element.querySelectorAll("button")].find(b => b.textContent === "Fit 3D view");
      assert.ok(button && !button.disabled); await act(async () => button.click()); },
    async dispose() { await dom.dispose(root); delete globalThis.__cameraProbe;
      if (priorStyle) Object.defineProperty(globalThis, "getComputedStyle", priorStyle); else delete globalThis.getComputedStyle; } };
}

test("actual component initial narrow fit, selected roof Fit, accessible help and no scene remount/data commit", async () => {
  const doc = project(true), before = JSON.stringify(doc), f = await mount(doc, 0.3);
  try {
    assertFits(doc, f.camera, "initial narrow whole geometry fit");
    const beforeSelection = f.camera.position.clone();
    await f.render(doc, "second");
    assert.deepEqual(f.camera.position.toArray(), beforeSelection.toArray(), "ordinary selection retains orbit");
    await f.fit();
    const centre = new Box3().setFromPoints(points(doc)).getCenter(new Vector3());
    const actual = f.camera.position.clone().sub(centre).normalize();
    assert.ok(actual.distanceTo(new Vector3(...sceneViewDirection(doc, "second"))) < 1e-12);
    assertFits(doc, f.camera, "explicit selected roof fit");
    assert.equal(f.control.mounts, 1); assert.equal(f.control.unmounts, 0);
    assert.equal(f.control.commits, 0); assert.equal(JSON.stringify(doc), before);
    const box = f.dom.element.querySelector('input[type="checkbox"]');
    assert.ok(box.closest("label").textContent.includes("Compatibility mode"));
    assert.equal(f.dom.element.querySelector("summary").textContent, "View options");
    const help = f.dom.element.querySelector('[id="' + box.getAttribute("aria-describedby") + '"]');
    assert.equal(help.textContent, "Use this if the 3D view does not display correctly.");
  } finally { await f.dispose(); }
});

test("resize after current geometry changes must fit the current extent and preserve orbit direction", async () => {
  const initial = project(), enlarged = project(true), f = await mount(initial);
  try {
    const orbit = new Vector3(1, 1, 1).normalize(), oldCentre = f.control.framing.centre;
    f.camera.position.copy(oldCentre).addScaledVector(orbit, 80);
    f.camera.lookAt(oldCentre); f.camera.updateMatrixWorld();
    const before = f.camera.position.toArray();
    await f.render(enlarged);
    assert.deepEqual(f.camera.position.toArray(), before, "ordinary edits do not reset orbit");
    f.control.state.size = { width: 390, height: 800 };
    await f.render(enlarged);
    const after = f.camera.getWorldDirection(new Vector3()).negate();
    assert.ok(after.distanceTo(orbit) < 1e-12, "resize retains actual viewing direction");
    assertFits(enlarged, f.camera, "resize must fit current, not captured initial, geometry");
  } finally { await f.dispose(); }
});
