import { measurePlannerChrome } from "../data/measurePlannerChrome.ts";

/** Keep an explicit action's result in view after a long form collapses. */
export function revealActionResult(
	element: HTMLElement | null,
	canReveal: () => boolean = () => true,
): boolean {
	if (!element?.isConnected || !canReveal()) return false;
	const root = element.closest<HTMLElement>("[data-linker-planner]");
	if (root) measurePlannerChrome(root);
	element.focus({ preventScroll: true });
	if (!canReveal()) return false;
	// A field's visible label carries its name/unit. Reveal that context while
	// keeping keyboard focus on the editable control itself.
	(element.closest("label") ?? element).scrollIntoView({
		block: "start",
		behavior: "instant",
	});
	return true;
}
