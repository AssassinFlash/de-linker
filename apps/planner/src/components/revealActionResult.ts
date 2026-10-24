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
	// Reveal a field label or the complete marked result heading (including its
	// revision) while keeping keyboard focus on the semantic target itself.
	(
		element.closest("label, [data-action-result-context]") ?? element
	).scrollIntoView({
		block: "start",
		behavior: "instant",
	});
	return true;
}
