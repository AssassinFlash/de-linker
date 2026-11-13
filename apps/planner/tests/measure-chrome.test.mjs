import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import {
	armHashReveal,
	disarmHashReveal,
	measurePlannerChrome,
	revealHashTarget,
} from "../src/data/measurePlannerChrome.ts";

function fixture(hash) {
	const dom = new JSDOM(
		`<!doctype html><html><body><div data-linker-planner><section id="lp-design"></section></div></body></html>`,
		{ url: `https://fixture.invalid/workspace/${hash}` },
	);
	disarmHashReveal();
	Object.assign(globalThis, {
		document: dom.window.document,
		location: dom.window.location,
		window: dom.window,
		CSS: { escape: (value) => value },
	});
	const root = dom.window.document.querySelector("[data-linker-planner]");
	const target = dom.window.document.getElementById("lp-design");
	const calls = [];
	dom.window.scrollTo = (to) => calls.push(to.top);
	const computeStub = () => ({ scrollMarginTop: "260px" });
	dom.window.getComputedStyle = computeStub;
	Object.assign(globalThis, { getComputedStyle: computeStub });
	target.getBoundingClientRect = () => ({ top: 100 });
	Object.defineProperty(dom.window, "scrollY", {
		configurable: true,
		get: () => 500,
	});
	return { dom, root, target, calls };
}

test("revealHashTarget re-scrolls the armed hash below the measured sticky chrome", () => {
	const { root, calls } = fixture("#lp-design");
	armHashReveal();
	revealHashTarget(root);
	// 500 + 100 - 260: the landing the browser made with 0px fallbacks lacked
	// the full header + project-bar offset.
	assert.deepEqual(calls, [340]);
});

test("revealHashTarget stays armed while measurements keep shifting the layout", () => {
	const { root, calls } = fixture("#lp-design");
	armHashReveal();
	revealHashTarget(root);
	revealHashTarget(root);
	assert.equal(calls.length, 2);
});

test("an already-correct landing or a disarmed reveal never scrolls", () => {
	const { dom, root, target, calls } = fixture("#lp-design");
	armHashReveal();
	// A correct landing leaves the target exactly one scroll-margin below the top.
	target.getBoundingClientRect = () => ({ top: 260 });
	Object.defineProperty(dom.window, "scrollY", {
		configurable: true,
		get: () => 340,
	});
	revealHashTarget(root);
	assert.deepEqual(calls, []);
	Object.defineProperty(dom.window, "scrollY", {
		configurable: true,
		get: () => 500,
	});
	disarmHashReveal();
	revealHashTarget(root);
	assert.deepEqual(calls, []);
});

test("arming keeps the hash of the first landing and ignores later hash changes", () => {
	const { dom, root, calls } = fixture("#lp-design");
	armHashReveal();
	dom.window.location.hash = "#lp-equipment";
	armHashReveal();
	revealHashTarget(root);
	assert.deepEqual(calls, [340]);
});

test("a page without a hash never arms a reveal", () => {
	const { root, calls } = fixture("");
	armHashReveal();
	revealHashTarget(root);
	assert.deepEqual(calls, []);
});

test("measurePlannerChrome publishes both bar heights as CSS variables", () => {
	const { dom, root } = fixture("");
	const header = dom.window.document.createElement("div");
	header.id = "lc-header";
	Object.defineProperty(header, "offsetHeight", { value: 81 });
	dom.window.document.body.append(header);
	const bar = dom.window.document.createElement("div");
	bar.className = "lp-project-bar";
	Object.defineProperty(bar, "offsetHeight", { value: 163 });
	root.append(bar);
	measurePlannerChrome(root);
	assert.equal(root.style.getPropertyValue("--lp-site-header-height"), "81px");
	assert.equal(root.style.getPropertyValue("--lp-project-bar-height"), "163px");
});
