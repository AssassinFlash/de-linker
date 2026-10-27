/** Native links are updated after app navigation; no global history patch. */
export const PLANNER_NAVIGATION = "linker-planner:navigation";
export function replacePlannerLocation(url: URL): void {
	window.history.replaceState(null, "", url);
	window.dispatchEvent(new Event(PLANNER_NAVIGATION));
}
