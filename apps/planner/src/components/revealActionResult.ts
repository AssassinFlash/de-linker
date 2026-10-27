import { measurePlannerChrome } from "../data/measurePlannerChrome.ts";

/** Keep an explicit action's result in view after a long form collapses. */
export function revealActionResult(
	element: HTMLElement | null,
	canReveal: () => boolean = () => true,
): boolean {
	if (!element?.isConnected || !canReveal()) return false;
	const root = element.closest<HTMLElement>("[data-linker-planner]");
	if (root) measurePlannerChrome(root);
	// Result headings need programmatic focus for the late sticky-bar correction.
	// Native form controls keep their ordinary keyboard tab order.
	if (element.matches("h1,h2,h3,h4,h5,h6") && !element.hasAttribute("tabindex"))
		element.tabIndex = -1;
	element.focus({ preventScroll: true });
	if (!canReveal()) return false;
	// Reveal a field label or the complete marked result heading (including its
	// revision) while keeping keyboard focus on the semantic target itself.
	const context =
		element.closest<HTMLElement>("label, [data-action-result-context]") ??
		element;
	context.scrollIntoView({
		block: "start",
		behavior: "instant",
	});
	// Restored routes can receive their final sticky-bar geometry after the
	// initial layout. Correct occlusion once, only while this target still has
	// focus and the native owner still admits the reveal.
	window.requestAnimationFrame(() => {
		if (
			!element.isConnected ||
			document.activeElement !== element ||
			!canReveal()
		)
			return;
		if (root) measurePlannerChrome(root);
		const clearance =
			Number.parseFloat(window.getComputedStyle(context).scrollMarginTop) || 0;
		if (context.getBoundingClientRect().top < clearance)
			context.scrollIntoView({ block: "start", behavior: "instant" });
	});
	return true;
}
