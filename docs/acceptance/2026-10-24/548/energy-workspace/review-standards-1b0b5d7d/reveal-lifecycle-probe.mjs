// Read-only, synthetic DOM probe of the real helper's one-frame lifecycle.
// These fixture dimensions are geometry examples, not application thresholds.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../../..");
const require = createRequire(path.join(repo, "apps/planner/package.json"));
const { JSDOM } = require("jsdom");
const { revealActionResult } = await import(
	pathToFileURL(path.join(repo, "apps/planner/src/components/revealActionResult.ts")).href
);

function fixture() {
	const dom = new JSDOM('<header id="lc-header"></header><main data-linker-planner><div class="lp-project-bar"></div><div data-action-result-context><h3 tabindex="-1">Result</h3></div><button>Reader control</button></main>');
	globalThis.window = dom.window;
	globalThis.document = dom.window.document;
	const root = document.querySelector("main");
	const target = document.querySelector("h3");
	const context = target.parentElement;
	Object.defineProperty(document.querySelector("header"), "offsetHeight", { value: 88 });
	Object.defineProperty(document.querySelector(".lp-project-bar"), "offsetHeight", { value: 144 });
	context.style.scrollMarginTop = "248px";
	let top = 240;
	context.getBoundingClientRect = () => ({ top });
	const frames = [], scrolls = [];
	window.requestAnimationFrame = (callback) => { frames.push(callback); return frames.length; };
	context.scrollIntoView = () => scrolls.push([
		root.style.getPropertyValue("--lp-site-header-height"),
		root.style.getPropertyValue("--lp-project-bar-height"),
	]);
	return { dom, root, target, context, frames, scrolls, top: (value) => { top = value; } };
}

for (const outcome of ["occluded", "clear", "focus-moved", "scope-withdrawn", "disconnected"]) {
	const f = fixture();
	let admitted = true;
	assert.equal(revealActionResult(f.target, () => admitted), true);
	assert.ok(document.activeElement === f.target);
	assert.deepEqual(f.scrolls, [["88px", "144px"]]);
	assert.equal(f.frames.length, 1);
	if (outcome === "clear") f.top(300);
	if (outcome === "focus-moved") document.querySelector("button").focus();
	if (outcome === "scope-withdrawn") admitted = false;
	if (outcome === "disconnected") f.target.remove();
	f.frames.shift()();
	assert.equal(f.scrolls.length, outcome === "occluded" ? 2 : 1, outcome);
	assert.equal(f.frames.length, 0, "late correction never schedules another frame");
	f.dom.window.close();
	console.log(`PASS: ${outcome}`);
}

const f = fixture();
assert.equal(revealActionResult(f.target, () => false), false);
f.target.remove();
assert.equal(revealActionResult(f.target), false);
assert.equal(f.frames.length, 0);
assert.equal(f.scrolls.length, 0);
f.dom.window.close();
delete globalThis.window;
delete globalThis.document;
console.log("PASS: initial unadmitted/disconnected targets do not focus, scroll or schedule");
