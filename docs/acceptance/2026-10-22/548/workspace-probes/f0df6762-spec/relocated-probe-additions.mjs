const currentBarRefusal = () => document.querySelector(".lp-project-bar .lp-navigation-refusal .lp-notice");
function assertPinned(text) {
  const notice = currentBarRefusal(); assert.ok(notice); assert.equal(notice.getAttribute("role"), "alert"); assert.ok(notice.textContent.includes(text));
  assert.equal([...document.querySelectorAll(".lp-notice")].filter(element => element.textContent.includes(text)).length, 1);
}

test("relocated staged refusal preserves the exact bar, selector, form and raw input until cancel", async t => {
  const app = await mount(t, { hash: "#lp-design", geometry: structuredClone(flat) });
  const bar = document.querySelector(".lp-project-bar"), selector = mobileSelector();
  await click("Fixture roof"); await click("Edit numeric properties");
  const form = document.querySelector(".lp-geometry-form"), input = form.querySelector('[name="name"]'); await enter(input, "Exact unapplied roof name");
  assert.equal(currentBarRefusal(), null); await mobileChoose("overview"); assertPinned(STAGED_NOTICE);
  assert.equal(document.querySelector(".lp-project-bar"), bar); assert.equal(mobileSelector(), selector); assert.equal(document.querySelector(".lp-geometry-form"), form); assert.equal(input.value, "Exact unapplied roof name"); assert.equal(selector.value, "design");
  await click("Cancel properties"); assert.equal(currentBarRefusal(), null); assert.equal(document.querySelector(".lp-project-bar"), bar); assert.equal(mobileSelector(), selector);
  await mobileChoose("overview"); assert.equal(document.activeElement.id, "lp-overview"); assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0);
});

test("relocated invalid brief refusal appears once and clears after correction without a document edit", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  const app = await mount(t, { hash: "#lp-load", brief }), input = annual();
  await enter(input, "1,"); assert.equal(currentBarRefusal(), null); await mobileChoose("site"); assertPinned(INVALID_NOTICE); assert.equal(input.value, "1,");
  await act(async () => input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assert.equal(currentBarRefusal(), null); assert.equal(input.value, "10"); await mobileChoose("site"); assert.equal(document.activeElement.id, "lp-brief-use"); assert.equal(app.writes.length, 0);
});

test("relocated refusal retains brief-error precedence then switches to staged guidance without duplication", async t => {
  const brief = emptyBrief(); brief.annual_load.kwh = 10;
  await mount(t, { hash: "#lp-design", geometry: structuredClone(flat), brief }); await click("Fixture roof"); await click("Source properties");
  await enter(annual(), "1,"); await mobileChoose("overview"); assertPinned(INVALID_NOTICE); assert.equal(noticeHas(STAGED_NOTICE), false);
  await act(async () => annual().dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assertPinned(STAGED_NOTICE); assert.equal(noticeHas(INVALID_NOTICE), false); await click("Cancel properties"); assert.equal(currentBarRefusal(), null); await mobileChoose("energy"); assert.equal(mobileSelector().value, "energy");
});

test("relocated refusal survives acknowledgement without replacing an unapplied form or its raw text", async t => {
  const state = await mountStateful(t); await enter(annual(), "25"); await click("Save project"); await until(() => state.gates.length === 1);
  const body = state.sends[0]; await mobileChoose("design"); await click("Fixture roof"); await click("Edit numeric properties");
  const form = document.querySelector(".lp-geometry-form"), input = form.querySelector('[name="name"]'); await enter(input, "Raw during acknowledgement");
  await mobileChoose("overview"); assertPinned(STAGED_NOTICE); assert.equal(document.querySelector(".lp-save-state").textContent, "Saving…");
  await state.ack(); assertPinned(STAGED_NOTICE); assert.equal(document.querySelector(".lp-geometry-form"), form); assert.equal(input.value, "Raw during acknowledgement"); assert.equal(document.querySelector(".lp-save-state").textContent, STAGED_STATUS); assert.equal(state.sends[0], body);
  await click("Cancel properties"); assert.equal(currentBarRefusal(), null); assert.equal(document.querySelector(".lp-save-state").textContent, "Saved · revision 8"); await mobileChoose("overview"); assert.equal(metric("Annual consumption"), "25 kWh");
});

test("relocated refusal cancellation leaves uncertain save status and retry bytes intact", async t => {
  const state = await mountStateful(t, { sendMode: "refuse" }); await enter(annual(), "25"); await click("Save project"); await until(() => document.querySelector(".lp-save-state").textContent === "Save not confirmed");
  const body = state.sends[0]; await mobileChoose("design"); await click("Add module specification"); await mobileChoose("overview"); assertPinned(STAGED_NOTICE); assert.equal(document.querySelector(".lp-save-state").textContent, "Save not confirmed");
  await click("Cancel properties"); assert.equal(currentBarRefusal(), null); assert.equal(document.querySelector(".lp-save-state").textContent, "Save not confirmed"); assert.equal(noticeHas("The save could not be confirmed. Your input is still here."), true);
  state.sendMode = "hold"; await click("Retry save"); await until(() => state.gates.length === 1); assert.equal(state.sends[1], body); await state.ack(); assert.equal(document.querySelector(".lp-save-state").textContent, "Saved · revision 8"); assert.equal(currentBarRefusal(), null);
});

test("relocated recovery refusal stays actionable and close protection survives validation cleanup", async t => {
  const state = await mountStateful(t, { storageFails: true }); await enter(annual(), "25"); await until(() => noticeHas(RECOVERY_NOTICE)); await click("Projects"); await until(() => currentBarRefusal()?.textContent.includes(RECOVERY_REFUSAL)); assertPinned(RECOVERY_REFUSAL); assert.equal(state.closes, 0);
  await enter(annual(), "1,"); assertPinned(INVALID_NOTICE); await act(async () => annual().dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  assert.equal(currentBarRefusal(), null); assert.equal(noticeHas(RECOVERY_NOTICE), true); assert.equal(annual().value, "25");
  await click("Projects"); await until(() => currentBarRefusal()?.textContent.includes(RECOVERY_REFUSAL)); assertPinned(RECOVERY_REFUSAL); assert.equal(state.closes, 0); assert.equal(state.attempts.at(-1).history.current.brief.annual_load.kwh, 25);
});

test("relocated refusal is not created by a navigation attempt after native admission is withdrawn", async t => {
  const app = await mount(t, { hash: "#lp-load" }); await enter(annual(), "1,"); assert.equal(currentBarRefusal(), null);
  app.revoke(); const hash = location.hash; await mobileChoose("site"); assert.equal(currentBarRefusal(), null); assert.equal(mobileSelector().value, "energy"); assert.equal(location.hash, hash); assert.equal(annual().value, "1,"); assert.equal(app.writes.length, 0); assert.equal(app.sends.length, 0);
});
