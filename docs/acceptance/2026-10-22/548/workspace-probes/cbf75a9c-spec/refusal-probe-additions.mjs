// These cases append after the unchanged563 prefix and unchangedeefe additions.
const STAGED_STATUS = "Roof editing in progress";
const STAGED_NOTICE = "Finish or cancel roof editing before leaving this workspace.";
const INVALID_NOTICE = "Correct the highlighted input before leaving this project.";
const RECOVERY_NOTICE = "Browser recovery is unavailable. Changes remain open here until the server confirms a save.";
const RECOVERY_REFUSAL = "Save the project before leaving. Browser recovery could not be stored.";
const noticeHas = text => [...document.querySelectorAll(".lp-notice")].some(element => element.textContent.includes(text));

async function mountStateful(t, { storageFails = false, sendMode = "hold", hash = "#lp-load" } = {}) {
  const fixture = setupDom(); window.history.replaceState(null, "", location.pathname + location.search + hash);
  const { createRoot } = await import("react-dom/client"), { ProjectEditor } = await import("../src/components/ProjectEditor.tsx");
  const root = createRoot(fixture.element), cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const project = { id: "1".repeat(32), title: "Stateful refusal fixture", revision: 7, input_sha256: "2".repeat(64), inputs: { brief, geometry: structuredClone(flat), preserved_extension: { fixture: "exact" } } };
  const state = { storageFails, sendMode, attempts: [], sends: [], gates: [], closes: 0, admitted: true };
  const store = { async read() { return null; }, async candidates() { return []; }, async readProfileImports() { return []; }, async write(scope, draft) { state.attempts.push(structuredClone(draft)); if (state.storageFails) throw new Error("synthetic_storage_failure"); } };
  const client = { isCurrentScope: scope => state.admitted && scope === SESSION.query_scope, async query() { throw new Error("No query expected"); }, async send(path, body) { assert.equal(path, "projects/revise"); state.sends.push(body); if (state.sendMode === "refuse") throw new Error("synthetic_unknown_acknowledgement"); return new Promise((resolve, reject) => state.gates.push({ resolve, reject, body })); } };
  const config = { baseUrl: location.origin + "/api/", nonceUrl: location.origin + "/nonce", locale: "en-GB", countries: { FR: "France" } };
  t.after(async () => { cache.clear(); await fixture.dispose(root); });
  await act(async () => root.render(React.createElement(QueryClientProvider, { client: cache }, React.createElement(ProjectEditor, { project, session: SESSION, client, store, config, recheck() {}, close() { state.closes++; return true; } }))));
  await until(() => document.querySelector(".lp-project"));
  state.ack = async () => { const gate = state.gates.shift(); assert.ok(gate); const body = JSON.parse(gate.body); await act(async () => gate.resolve({ ...project, revision: body.expected_revision + 1, input_sha256: "c".repeat(64), inputs: body.inputs })); };
  return state;
}

test("all roof-editor form kinds use staged guidance after refusal and cancel resumes navigation", async t => {
  const forms = [
    ["new roof", ["Add roof face"], "Cancel properties"],
    ["existing roof", ["Fixture roof", "Edit numeric properties"], "Cancel properties"],
    ["existing array", ["Fixture array", "Edit numeric properties"], "Cancel properties"],
    ["new array", ["Add module array"], "Cancel properties"],
    ["existing module", ["Synthetic 1 x 2 m", "Edit numeric properties"], "Cancel properties"],
    ["new module", ["Add module specification"], "Cancel properties"],
    ["source", ["Fixture roof", "Source properties"], "Cancel properties"],
    ["coordinate reference", ["Coordinate references"], "Cancel properties"],
    ["obstacle", ["Add obstacle"], "Cancel properties"],
    ["keep-out", ["Add keep-out area"], "Cancel properties"],
    ["layout rules", ["Layout clearances"], "Cancel properties"],
    ["roof removal confirmation", ["Fixture roof", "Remove object"], "Cancel"],
  ];
  for (const [kind, actions, cancel] of forms) await t.test(kind, async sub => {
    const app = await mount(sub, { hash: "#lp-design", geometry: structuredClone(flat) });
    for (const action of actions) await click(action);
    assert.equal(document.querySelector(".lp-save-state").textContent, STAGED_STATUS); assert.equal(noticeHas(INVALID_NOTICE), false); assert.equal(noticeHas(STAGED_NOTICE), false);
    await mobileChoose("overview"); assert.equal(mobileSelector().value, "design"); assert.equal(noticeHas(STAGED_NOTICE), true); assert.equal(noticeHas(INVALID_NOTICE), false);
    await click(cancel); assert.equal(noticeHas(STAGED_NOTICE), false); assert.equal(document.querySelector(".lp-save-state").textContent, "Saved · revision 7");
    await mobileChoose("site"); assert.equal(document.activeElement.id, "lp-brief-use"); assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0);
  });
});

test("invalid brief takes precedence over staged roof state until corrected, then cancellation clears refusal", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const app = await mount(t, { hash: "#lp-design", geometry: structuredClone(flat), brief });
  await click("Fixture roof"); await click("Source properties");
  // Adversarially create both states; ordinary workspace navigation already
  // prevents entering a second workspace while its other form is unapplied.
  await enter(annual(), "1,"); await mobileChoose("overview");
  assert.equal(document.querySelector(".lp-save-state").textContent, "Input needs attention"); assert.equal(noticeHas(INVALID_NOTICE), true); assert.equal(noticeHas(STAGED_NOTICE), false);
  await act(async () => annual().dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assert.equal(document.querySelector(".lp-save-state").textContent, STAGED_STATUS); assert.equal(noticeHas(INVALID_NOTICE), false); assert.equal(noticeHas(STAGED_NOTICE), true);
  await click("Cancel properties"); assert.equal(noticeHas(STAGED_NOTICE), false); await mobileChoose("energy"); assert.equal(mobileSelector().value, "energy"); assert.equal(app.writes.length, 0);
});

test("validation cleanup preserves an in-flight save and a later edit beyond its acknowledgement", async t => {
  const state = await mountStateful(t); await enter(annual(), "25"); await click("Save project"); await until(() => state.gates.length === 1);
  const firstBody = state.sends[0]; await mobileChoose("design"); await click("Fixture roof"); await click("Edit numeric properties");
  assert.equal(document.querySelector(".lp-save-state").textContent, "Saving…"); await mobileChoose("overview"); assert.equal(noticeHas(STAGED_NOTICE), true);
  await click("Cancel properties"); assert.equal(noticeHas(STAGED_NOTICE), false); assert.equal(document.querySelector(".lp-save-state").textContent, "Saving…");
  await mobileChoose("energy"); await enter(annual(), "30"); await state.ack();
  assert.equal(annual().value, "30"); assert.equal(document.querySelector(".lp-save-state").textContent, "Unsaved changes"); assert.equal(state.sends.length, 1); assert.equal(state.sends[0], firstBody); assert.equal(JSON.parse(firstBody).inputs.brief.annual_load.kwh, 25);
});

test("staged-form cancellation does not clear an uncertain save intent or change retry bytes", async t => {
  const state = await mountStateful(t, { sendMode: "refuse" }); await enter(annual(), "25"); await click("Save project");
  await until(() => document.querySelector(".lp-save-state").textContent === "Save not confirmed"); const firstBody = state.sends[0];
  await mobileChoose("design"); await click("Add module specification"); await mobileChoose("overview"); assert.equal(noticeHas(STAGED_NOTICE), true); assert.equal(document.querySelector(".lp-save-state").textContent, "Save not confirmed");
  await click("Cancel properties"); assert.equal(noticeHas(STAGED_NOTICE), false); assert.equal(document.querySelector(".lp-save-state").textContent, "Save not confirmed"); assert.equal(noticeHas("The save could not be confirmed. Your input is still here."), true);
  state.sendMode = "hold"; await click("Retry save"); await until(() => state.gates.length === 1); assert.equal(state.sends[1], firstBody); await state.ack(); assert.equal(document.querySelector(".lp-save-state").textContent, "Saved · revision 8");
});

test("validation reset cannot erase unavailable recovery, close admission or the unsaved document", async t => {
  const state = await mountStateful(t, { storageFails: true }); await enter(annual(), "25"); await until(() => noticeHas(RECOVERY_NOTICE));
  await click("Projects"); await until(() => noticeHas(RECOVERY_REFUSAL)); assert.equal(state.closes, 0);
  await enter(annual(), "1,"); await mobileChoose("design"); assert.equal(noticeHas(INVALID_NOTICE), true);
  await act(async () => annual().dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assert.equal(noticeHas(INVALID_NOTICE), false); assert.equal(noticeHas(RECOVERY_NOTICE), true); assert.equal(annual().value, "25");
  await mobileChoose("design"); await click("Fixture roof"); await click("Edit numeric properties"); await click("Cancel properties");
  assert.equal(noticeHas(RECOVERY_NOTICE), true); await click("Projects"); await until(() => noticeHas(RECOVERY_REFUSAL)); assert.equal(state.closes, 0); assert.equal(state.attempts.at(-1).history.current.brief.annual_load.kwh, 25);
});

test("SPEC COUNTEREXAMPLE: refusal feedback must remain with the persistent workspace navigation", async t => {
  await mount(t, { hash: "#lp-design", geometry: structuredClone(flat) }); await click("Fixture roof"); await click("Edit numeric properties");
  const form = document.querySelector(".lp-geometry-form"); await enter(form.querySelector('[name="name"]'), "Retained long-form input");
  await mobileChoose("overview"); assert.equal(mobileSelector().value, "design"); assert.equal(document.querySelector(".lp-geometry-form"), form); assert.equal(noticeHas(STAGED_NOTICE), true);
  const notice = [...document.querySelectorAll(".lp-notice")].find(element => element.textContent.includes(STAGED_NOTICE));
  // The parent separately verified physical offscreen behavior at DE390. The
  // source/DOM seam proves this notice is outside the persistent project bar.
  assert.ok(document.querySelector(".lp-project-bar").contains(notice));
});
