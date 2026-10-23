/** Keep an explicit action's result in view after a long form collapses. */
export function revealActionResult(
	element: HTMLElement | null,
	canReveal: () => boolean = () => true,
): boolean {
	if (!element?.isConnected || !canReveal()) return false;
	element.focus({ preventScroll: true });
	if (!canReveal()) return false;
	element.scrollIntoView({ block: "start", behavior: "instant" });
	return true;
}
