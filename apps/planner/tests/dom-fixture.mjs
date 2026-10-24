import { JSDOM } from "jsdom";
import { act } from "react";
import { notifyManager, timeoutManager } from "@tanstack/react-query";

// Browser timers disappear with their page. Node's test DOM has no page-owned
// timers, so Query's cache expiry must not keep a disposed fixture alive.
timeoutManager.setTimeoutProvider({
	setTimeout(callback, delay) {
		const timer = setTimeout(callback, delay);
		timer.unref();
		return timer;
	},
	clearTimeout(timer) {
		clearTimeout(timer);
	},
	setInterval(callback, delay) {
		const timer = setInterval(callback, delay);
		timer.unref();
		return timer;
	},
	clearInterval(timer) {
		clearInterval(timer);
	},
});

export function setupDom() {
	const dom = new JSDOM(
		'<!doctype html><header id="lc-header"></header><section data-linker-planner></section>',
		{ url: "https://fixture.invalid/workspace/?project=" + "1".repeat(32) },
	);
	// JSDOM has no layout/scroll implementation. Actual sticky-header clearance
	// and scrolling are independently verified in the native browser matrix.
	dom.window.HTMLElement.prototype.scrollIntoView = function () {};
	dom.window.requestAnimationFrame = (callback) =>
		dom.window.setTimeout(callback, 0);
	dom.window.cancelAnimationFrame = (frame) => dom.window.clearTimeout(frame);
	// Query's notification scheduler is separate from its cache timers. Bind
	// notifications to this page so close() disposes pending native-event work
	// rather than calling a React subscriber after its global DOM is removed.
	notifyManager.setScheduler((callback) => dom.window.setTimeout(callback, 0));
	const names = [
		"window",
		"document",
		"location",
		"history",
		"navigator",
		"HTMLElement",
		"Event",
		"ResizeObserver",
		"IS_REACT_ACT_ENVIRONMENT",
	];
	const previous = Object.fromEntries(
		names.map((name) => [
			name,
			Object.getOwnPropertyDescriptor(globalThis, name),
		]),
	);
	for (const name of names.slice(0, 8))
		Object.defineProperty(globalThis, name, {
			value: dom.window[name],
			writable: true,
			configurable: true,
		});
	globalThis.ResizeObserver = class {
		observe() {}
		disconnect() {}
	};
	globalThis.IS_REACT_ACT_ENVIRONMENT = true;
	dom.window.wp = {
		i18n: {
			__: (message) => message,
			sprintf: (format, ...values) =>
				format.replace(/%(?:\d+\$)?[ds]/g, () => String(values.shift())),
		},
	};
	return {
		dom,
		element: document.querySelector("[data-linker-planner]"),
		async dispose(root) {
			await act(async () => root.unmount());
			dom.window.close();
			notifyManager.setScheduler((callback) => setTimeout(callback, 0));
			for (const name of names) {
				if (previous[name])
					Object.defineProperty(globalThis, name, previous[name]);
				else delete globalThis[name];
			}
		},
	};
}
export async function until(predicate) {
	for (let attempt = 0; attempt < 100; attempt++) {
		await act(async () => {
			await new Promise((resolve) => setTimeout(resolve, 0));
		});
		if (predicate()) return;
	}
	throw new Error("Expected rendered state was not reached");
}
export async function enter(element, value) {
	if (!element) throw new Error("Missing editable input");
	await act(async () => {
		const prototype =
			element.tagName === "TEXTAREA"
				? window.HTMLTextAreaElement.prototype
				: window.HTMLInputElement.prototype;
		Object.getOwnPropertyDescriptor(prototype, "value").set.call(
			element,
			value,
		);
		element.dispatchEvent(new window.Event("input", { bubbles: true }));
	});
}
export function deferred() {
	let resolve, reject;
	const promise = new Promise((yes, no) => {
		resolve = yes;
		reject = no;
	});
	return { promise, resolve, reject };
}
