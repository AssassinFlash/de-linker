import { useEffect } from "react";

/** Keep native Polylang destinations; only carry the open opaque project ID. */
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
	return target.href;
}

/** Native site chrome stays owned by LC; this app adapts to its live geometry. */
export function useSiteIntegration(projectId: string | null): void {
	useEffect(() => {
		const root = document.querySelector<HTMLElement>("[data-linker-planner]");
		if (!root) return;
		const header = document.getElementById("lc-header");
		const measure = () => {
			root.style.setProperty(
				"--lp-site-header-height",
				`${header?.offsetHeight ?? 0}px`,
			);
		};
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
			link.href = projectLanguageUrl(href, location.href, projectId);
		}
		return () => {
			observer.disconnect();
			root.style.removeProperty("--lp-site-header-height");
			for (const [link, href] of originals) link.setAttribute("href", href);
		};
	}, [projectId]);
}
