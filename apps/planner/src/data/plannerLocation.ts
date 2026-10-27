/** Native links are updated after app navigation; no global history patch. */
export const PLANNER_NAVIGATION = "linker-planner:navigation";
const energyViews = [
	"weather",
	"pv",
	"pvgis-reference",
	"scenario",
	"equipment",
	"runs",
	"reports",
	"comparison",
] as const;
export type EnergyView = (typeof energyViews)[number];

/** A saved result/comparison takes precedence over a form-view preference. */
export function initialEnergyView(url: URL): EnergyView {
	if (url.searchParams.has("compare")) return "comparison";
	if (url.searchParams.has("run")) return "runs";
	const value = url.searchParams.get("energy_view");
	return energyViews.find((view) => view === value) ?? "scenario";
}

export function replacePlannerLocation(url: URL): void {
	window.history.replaceState(null, "", url);
	window.dispatchEvent(new Event(PLANNER_NAVIGATION));
}
