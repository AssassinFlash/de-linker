import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { setupDom } from "./dom-fixture.mjs";
import { revealActionResult } from "../src/components/revealActionResult.ts";

test("error reveal focuses the actual field but scrolls its semantic label including the unit", async () => {
  const fixture = setupDom();
  const label = document.createElement("label"), input = document.createElement("input"), calls = [];
  label.append("Relative height (m)", input); fixture.element.append(label);
  label.scrollIntoView = options => calls.push({ target: label, options });
  input.scrollIntoView = () => assert.fail("The field alone loses its label/unit context");
  try {
    assert.equal(revealActionResult(input), true);
    assert.equal(document.activeElement, input);
    assert.equal(calls.length, 1); assert.equal(calls[0].target, label);
    assert.deepEqual(calls[0].options, { block: "start", behavior: "instant" });
    assert.ok(label.textContent.includes("(m)"));
  } finally { await fixture.dispose({ unmount() {} }); }
});

test("reveal fences detached targets and permission changes, while non-label destinations still scroll themselves", async () => {
  const fixture = setupDom(), input = document.createElement("input"), calls = [];
  input.scrollIntoView = () => calls.push(input);
  try {
    assert.equal(revealActionResult(input), false);
    fixture.element.append(input);
    assert.equal(revealActionResult(input, () => false), false);
    assert.equal(calls.length, 0);
    let allowed = true;
    input.addEventListener("focus", () => { allowed = false; });
    assert.equal(revealActionResult(input, () => allowed), false);
    assert.equal(calls.length, 0);
    input.blur();
    assert.equal(revealActionResult(input), true);
    assert.deepEqual(calls, [input]);
  } finally { await fixture.dispose({ unmount() {} }); }
});

test("the one WindPress volume declares both measured-bar offsets for label and field focus destinations", async () => {
  const css = await readFile(new URL("../../../plugins/linker-commerce/content/windpress/planner.css", import.meta.url), "utf8");
  const rule = css.slice(css.indexOf("/* chrome.css gives every [id]"));
  assert.ok(rule.includes('[data-linker-planner] .lp-project :is(label, input, textarea, select)'));
  assert.ok(rule.includes('var(--lp-site-header-height, 0px) + var(--lp-project-bar-height, 0px) + 16px'));
  assert.ok(rule.includes('[data-linker-planner] .lp-import-panel h3'));
  assert.ok(!rule.includes('@layer'), "the documented global rule requires an unlayered override");
});
