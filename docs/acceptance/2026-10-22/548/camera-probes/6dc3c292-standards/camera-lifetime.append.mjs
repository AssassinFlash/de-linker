test("real OrbitControls keeps camera/target coherent, survives Fit/resize, and releases actual listeners", async () => {
  const doc = project(true), f = await mount(doc, 0.5);
  let orbit;
  try {
    assert.equal(f.control.orbits.size, 1);
    [orbit] = f.control.orbits;
    const cameraIdentity = f.camera, initialTarget = orbit.target.clone();
    const enlarged = structuredClone(doc);
    enlarged.roofs[1].origin_enu[0] += 1000;
    const next = readGeometry(enlarged, policy);
    const direction = new Vector3(-1, 1, 0.5).normalize();
    f.camera.position.copy(orbit.target).addScaledVector(direction, 100);
    f.camera.lookAt(orbit.target); f.camera.updateMatrixWorld();
    const position = f.camera.position.clone();
    await f.render(next, "second");
    assert.deepEqual(f.camera.position.toArray(), position.toArray());
    assert.deepEqual(orbit.target.toArray(), initialTarget.toArray());
    f.control.state.size = { width: 390, height: 800 };
    await f.render(next, "second");
    const centre = new Box3().setFromPoints(points(next)).getCenter(new Vector3());
    assert.ok(orbit.target.distanceTo(centre) < 1e-12);
    assert.ok(f.camera.getWorldDirection(new Vector3()).negate().distanceTo(direction) < 1e-12);
    assertFits(next, f.camera, "new whole extent with real OrbitControls target");
    await f.fit();
    assert.ok(f.camera.getWorldDirection(new Vector3()).negate().distanceTo(new Vector3(...sceneViewDirection(next, "second"))) < 1e-12);
    assert.equal(f.camera, cameraIdentity);
    assert.equal(f.control.orbits.size, 1, "Fit/resize must reuse the actual controls");
    assert.equal(f.control.disposed?.size ?? 0, 0);
    const canvas = f.control.state.gl.domElement;
    canvas.dispatchEvent(new window.Event("planner-transform-start"));
    assert.equal(orbit.enabled, false);
    canvas.dispatchEvent(new window.Event("planner-transform-end"));
    assert.equal(orbit.enabled, true);
    assert.equal(f.control.commits, 0);
  } finally { await f.dispose(); }
  assert.ok(f.control.disposed.has(orbit));
  assert.ok([...f.control.plannerListeners.values()].every(listeners => listeners.size === 0));
});

test("StrictMode replays construct separate live controls and fully dispose both lifetimes", async () => {
  const { StrictMode } = await import("react");
  const dom = setupDom(), priorStyle = Object.getOwnPropertyDescriptor(globalThis, "getComputedStyle");
  globalThis.getComputedStyle = dom.dom.window.getComputedStyle.bind(dom.dom.window);
  const control = { mounts: 0, unmounts: 0, state: { camera: new PerspectiveCamera(75, 1, 0.01, 1000),
    size: { width: 400, height: 400 }, invalidate() {} } };
  globalThis.__cameraProbe = control;
  const { createRoot } = await import("react-dom/client");
  const root = createRoot(dom.element), doc = project();
  try {
    await act(async () => root.render(createElement(StrictMode, {}, createElement(SceneViewport, {
      document: doc, poses: panelPoses(doc), selected: null, select() {}, commit() { assert.fail("No geometry commits"); }, disabled: false }))));
    assert.equal(control.orbits.size, 2, "two StrictMode effect lifetimes");
    assert.equal(control.disposed.size, 1, "replayed initial lifetime already released");
    assert.equal([...control.orbits].filter(c => !control.disposed.has(c)).length, 1);
    assertFits(doc, control.state.camera, "StrictMode retained camera fit");
    for (const listeners of control.plannerListeners.values()) assert.equal(listeners.size, 1);
  } finally {
    await dom.dispose(root);
    delete globalThis.__cameraProbe;
    if (priorStyle) Object.defineProperty(globalThis, "getComputedStyle", priorStyle); else delete globalThis.getComputedStyle;
  }
  assert.equal(control.disposed.size, 2);
  assert.ok([...control.plannerListeners.values()].every(listeners => listeners.size === 0));
});

test("a zero-size initial viewport waits, then fits the latest extent when dimensions become valid", async () => {
  const initial = project(), enlarged = project(true), f = await mount(initial, 0);
  try {
    await f.render(enlarged, "second");
    f.control.state.size = { width: 390, height: 800 };
    await f.render(enlarged, "second");
    assertFits(enlarged, f.camera, "first valid viewport uses latest extent");
    const centre = new Box3().setFromPoints(points(enlarged)).getCenter(new Vector3());
    assert.ok(f.camera.position.clone().sub(centre).normalize().distanceTo(new Vector3(...sceneViewDirection(enlarged, "second"))) < 1e-12);
  } finally { await f.dispose(); }
});
