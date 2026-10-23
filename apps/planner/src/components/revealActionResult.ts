/** Keep an explicit action's result in view after a long form collapses. */
export function revealActionResult(element: HTMLElement | null): boolean {
	if (!element) return false;
	element.focus({ preventScroll: true });
	element.scrollIntoView({ block: "start", behavior: "instant" });
	return true;
}
