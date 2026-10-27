// Appended to the unchanged 563 probe module, so its actual mount helpers,
// component imports and original counterexample execute without modification.
function mobileSelector() {
  const select = document.querySelector('select.lp-mobile-workspace[aria-label="Project sections"]');
  assert.ok(select); return select;
}
async function mobileChoose(value) {
  await act(async () => { const select = mobileSelector(); select.value = value; select.dispatchEvent(new window.Event("change", { bubbles: true })); });
}

test("new native selector shares the active workspace, destination and unchanged document", async t => {
  const app = await mount(t, { geometry: structuredClone(flat) });
  assert.deepEqual([...mobileSelector().options].map(option => [option.value, option.textContent]), [["overview", "Project overview"], ["site", "Site and project"], ["design", "Roof design"], ["energy", "Energy inputs"]]);
  for (const [value, target, canonicalHash] of [["site", "lp-brief-use", "#lp-site"], ["energy", "lp-load", "#lp-load"], ["design", "lp-design", "#lp-design"], ["overview", "lp-overview", "#lp-overview"], ["site", "lp-brief-use", "#lp-site"], ["site", "lp-brief-use", "#lp-site"]]) {
    await mobileChoose(value); assert.equal(document.querySelector(".lp-project").dataset.workspace, value); assert.equal(mobileSelector().value, value); assert.equal(document.activeElement.id, target); assert.equal(location.hash, canonicalHash);
    assert.equal(document.querySelectorAll('nav a[aria-current="page"]').length, 1);
  }
  assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0); assert.equal(app.requests.length, 0);
});

test("native selector retains actually invalid raw brief input and restores its controlled selection", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const app = await mount(t, { hash: "#lp-load", brief, locale: "de-DE" }), input = annual();
  await enter(input, "1,,"); const hash = location.hash;
  for (const value of ["site", "overview", "design"]) {
    await mobileChoose(value); assert.equal(document.querySelector(".lp-project").dataset.workspace, "energy"); assert.equal(mobileSelector().value, "energy"); assert.equal(location.hash, hash); assert.equal(annual(), input); assert.equal(input.value, "1,,"); assert.equal(input.getAttribute("aria-invalid"), "true");
  }
  assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0);
  await act(async () => input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  await mobileChoose("site"); assert.equal(document.activeElement.id, "lp-brief-use"); assert.equal(input.value, "10");
});

test("native selector cannot hide either a valid unapplied or invalid submitted geometry form", async t => {
  const app = await mount(t, { hash: "#lp-design", geometry: structuredClone(flat) });
  await click("Fixture array"); await click("Edit numeric properties");
  const form = document.querySelector(".lp-geometry-form"), rows = form.querySelector('[name="rows"]'); await enter(rows, "3");
  await mobileChoose("overview"); assert.equal(mobileSelector().value, "design"); assert.equal(document.querySelector(".lp-geometry-form"), form); assert.equal(rows.value, "3");
  await enter(rows, "2.5"); await click("Apply properties"); await mobileChoose("energy");
  assert.equal(mobileSelector().value, "design"); assert.equal(rows.value, "2.5"); assert.equal(rows.getAttribute("aria-invalid"), "true"); assert.equal(app.writes.length, 0);
  await click("Cancel properties"); await mobileChoose("overview"); assert.equal(metric("Included modules"), "5"); assert.equal(app.writes.length, 0);
});

test("mixed brief and geometry edits retain one shared undo chain when navigating with the selector", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const app = await mount(t, { hash: "#lp-load", geometry: structuredClone(flat), brief });
  const input = annual(); await enter(input, "25.5"); await mobileChoose("design"); await click("Fixture array"); await click("Edit numeric properties"); await enter(document.querySelector('[name="rows"]'), "3"); await click("Apply properties");
  await until(() => app.writes.at(-1)?.draft.history.past.length === 2);
  await mobileChoose("overview"); assert.equal(metric("Annual consumption"), "25.5 kWh"); assert.equal(metric("Included modules"), "8");
  for (const [action, annualValue, modules] of [["Undo", "25.5 kWh", "5"], ["Undo", "10 kWh", "5"], ["Redo", "25.5 kWh", "5"], ["Redo", "25.5 kWh", "8"]]) {
    await act(async () => document.querySelector(`button[aria-label="${action}"]`).click()); assert.equal(metric("Annual consumption"), annualValue); assert.equal(metric("Included modules"), modules); assert.equal(mobileSelector().value, "overview"); assert.equal(annual(), input);
  }
  const current = app.writes.at(-1).draft.history.current;
  assert.deepEqual(current.geometry.sources, flat.sources); assert.deepEqual(current.preserved_extension, { fixture: "exact" }); assert.equal(app.sends.length, 0);
});

test("file reading may finish in a hidden workspace without resetting the source or stealing destination focus", async t => {
  const app = await mount(t, { hash: "#lp-load" }); await click("Import interval data");
  const input = document.querySelector('input[type="file"]'), bytes = new TextEncoder().encode("time;load\n2026-01-01T00:00:00Z;1\n"); let release;
  const gate = new Promise(resolve => { release = resolve; });
  Object.defineProperty(input, "files", { configurable: true, value: [{ name: "mobile-retained.csv", size: bytes.byteLength, arrayBuffer: () => gate }] });
  await act(async () => input.dispatchEvent(new window.Event("change", { bubbles: true })));
  await mobileChoose("design"); assert.equal(document.activeElement.id, "lp-design");
  await act(async () => release(bytes.buffer)); await until(() => document.querySelector(".lp-file-name")?.textContent === "mobile-retained.csv");
  assert.equal(document.activeElement.id, "lp-design");
  await mobileChoose("energy"); assert.equal(document.querySelector('input[type="file"]'), input); assert.equal(document.querySelector(".lp-file-name").textContent, "mobile-retained.csv"); assert.equal(app.requests.length, 0); assert.equal(app.sends.length, 0);
});

test("native-scope withdrawal fences selector admission and its deferred reveal", async t => {
  await t.test("withdrawn before event", async sub => { const app = await mount(sub); app.revoke(); const hash = location.hash; await mobileChoose("design"); assert.equal(mobileSelector().value, "overview"); assert.equal(document.querySelector(".lp-project").dataset.workspace, "overview"); assert.equal(location.hash, hash); assert.equal(app.writes.length, 0); });
  await t.test("withdrawn before effect", async sub => { const app = await mount(sub); const original = window.history.replaceState.bind(window.history); window.history.replaceState = (...args) => { app.revoke(); return original(...args); }; await mobileChoose("design"); window.history.replaceState = original; assert.notEqual(document.activeElement.id, "lp-design"); assert.equal(app.writes.length, 0); assert.equal(app.requests.length, 0); assert.equal(app.sends.length, 0); });
});

test("each legacy initial fragment initializes the new selector without changing the old URL or project", async t => {
  for (const [hash, value] of [["#lp-site", "site"], ["#lp-brief-use", "site"], ["#lp-notes", "site"], ["#lp-load", "energy"], ["#lp-profiles", "energy"], ["#lp-design", "design"], ["#lp-overview", "overview"]]) {
    await t.test(hash, async sub => { const app = await mount(sub, { hash }); assert.equal(mobileSelector().value, value); assert.equal(location.hash, hash); assert.equal(app.writes.length, 0); });
  }
});

test("SPEC COUNTEREXAMPLE: a resolved brief refusal must not reappear when a valid unapplied roof form opens", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  await mount(t, { hash: "#lp-load", geometry: structuredClone(flat), brief });
  const warning = "Correct the highlighted input before leaving this project.";
  const hasWarning = () => [...document.querySelectorAll(".lp-notice")].some(element => element.textContent.includes(warning));
  const input = annual(); await enter(input, "25"); await enter(input, "1,"); await mobileChoose("site");
  assert.equal(mobileSelector().value, "energy"); assert.equal(hasWarning(), true);
  await act(async () => input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assert.equal(hasWarning(), false); await act(async () => document.querySelector('button[aria-label="Undo"]').click());
  assert.equal(input.value, "10"); assert.equal(document.querySelector(".lp-save-state").textContent, "Saved · revision 7");
  await mobileChoose("design"); assert.equal(hasWarning(), false);
  await click("Fixture roof"); await click("Edit numeric properties");
  assert.ok(document.querySelector(".lp-geometry-form")); assert.equal(document.querySelectorAll('[aria-invalid="true"]').length, 0);
  // Opening an ordinary valid staged form must not resurrect an unrelated,
  // already corrected highlighted-input refusal from the energy workspace.
  assert.equal(hasWarning(), false);
});
