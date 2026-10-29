import { savedSolutionId } from "../domain/savedSolution.ts";
import { useEffect } from "react";
import { initialEnergyView, PLANNER_NAVIGATION } from "./plannerLocation.ts";
import { measurePlannerChrome } from "./measurePlannerChrome.ts";
import { ENTRY_QUERY_KEYS, readEntryHints } from "../domain/entryHints.ts";

const workspaceHashes = new Set([
	"#lp-overview",
	"#lp-site",
	"#lp-brief-use",
	"#lp-notes",
	"#lp-load",
	"#lp-profiles",
	"#lp-design",
	"#lp-calculations",
	"#lp-equipment",
	"#lp-installation",
	"#lp-map-roof-properties",
	"#lp-map-ring-properties",
	"#lp-map-feature-properties",
]);
/** Keep native Polylang destinations and the same owned project/result view.
 * Current-page credentials and arbitrary query/hash content never travel. */
export function projectLanguageUrl(
	href: string,
	current: string,
	id: string | null,
): string {
	const page = new URL(current);
	const target = new URL(href, page);
	if (
		target.origin !== page.origin ||
		!["http:", "https:"].includes(target.protocol)
	)
		return href;
	if (id !== null && !/^[a-f0-9]{32}$/.test(id))
		throw new Error("invalid_project_reference");
	if (id) target.searchParams.set("project", id);
	else target.searchParams.delete("project");
	target.searchParams.delete("run");
	target.searchParams.delete("compare");
	target.searchParams.delete("energy_view");
	for (const key of ENTRY_QUERY_KEYS) target.searchParams.delete(key);
	const saved = id === null ? savedSolutionId(page.searchParams) : null;
	if (saved !== null) target.searchParams.set("saved_solution", String(saved));
	const hints = id === null ? readEntryHints(page.searchParams) : null;
	if (hints)
		for (const [key, value] of Object.entries({
			pv_kwp: hints.pvKw,
			annual_kwh: hints.annualKwh,
			phase: hints.phase,
			backup: hints.backup,
			plz: hints.postalCode,
			step: hints.roof ? "roof" : hints.equipment ? "equipment" : null,
			product: hints.productId,
		}))
			if (value !== null) target.searchParams.set(key, String(value));
	target.hash = "";
	if (id && page.searchParams.get("project") === id) {
		const view = page.searchParams.get("energy_view");
		if (view && initialEnergyView(page) === view)
			target.searchParams.set("energy_view", view);
		const run = page.searchParams.get("run");
		if (run && /^[a-f0-9]{32}$/.test(run)) target.searchParams.set("run", run);
		const comparison = page.searchParams.get("compare");
		if (
			comparison &&
			/^[a-f0-9]{32},[a-f0-9]{32}$/.test(comparison) &&
			comparison.slice(0, 32) !== comparison.slice(33)
		) {
			target.searchParams.delete("run");
			target.searchParams.set("compare", comparison);
		}
		if (workspaceHashes.has(page.hash)) target.hash = page.hash;
		else if (
			!page.hash &&
			!(run && /^[a-f0-9]{32}$/.test(run)) &&
			page.searchParams.getAll("step").length === 1 &&
			page.searchParams.get("step") === "roof"
		)
			target.hash = "#lp-design";
	}
	return target.href;
}

/** Native site chrome stays owned by LC; this app adapts to its live geometry. */
export function useSiteIntegration(projectId: string | null): void {
	useEffect(() => {
		const root = document.querySelector<HTMLElement>("[data-linker-planner]");
		if (!root) return;
		const header = document.getElementById("lc-header");
		const measure = () => measurePlannerChrome(root);
		const observer = new ResizeObserver(measure);
		if (header) observer.observe(header);
		measure();
		const originals = new Map<HTMLAnchorElement, string>();
		for (const link of document.querySelectorAll<HTMLAnchorElement>(
			"header a[hreflang][lang], footer a[hreflang][lang]",
		)) {
			const href = link.getAttribute("href");
			if (href === null) continue;
			originals.set(link, href);
		}
		const updateLinks = () => {
			for (const [link, href] of originals)
				link.href = projectLanguageUrl(href, location.href, projectId);
		};
		updateLinks();
		window.addEventListener(PLANNER_NAVIGATION, updateLinks);
		window.addEventListener("hashchange", updateLinks);
		window.addEventListener("popstate", updateLinks);
		// A native language-link click also covers links updated by a nested view.
		document.addEventListener("click", updateLinks, true);
		return () => {
			window.removeEventListener(PLANNER_NAVIGATION, updateLinks);
			window.removeEventListener("hashchange", updateLinks);
			window.removeEventListener("popstate", updateLinks);
			document.removeEventListener("click", updateLinks, true);
			observer.disconnect();
			root.style.removeProperty("--lp-site-header-height");
			for (const [link, href] of originals) link.setAttribute("href", href);
		};
	}, [projectId]);
}
