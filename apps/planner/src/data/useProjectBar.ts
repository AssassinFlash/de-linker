import { useCallback } from "react";

/** React 19 ref cleanup observes the actual bar after draft restoration, not
 * the earlier server-query state. Font, mobile and visibility changes resize it. */
export function useProjectBar() {
	return useCallback((bar: HTMLElement | null) => {
		if (!bar) return;
		const root = bar.closest<HTMLElement>("[data-linker-planner]");
		if (!root) return;
		const measure = () =>
			root.style.setProperty(
				"--lp-project-bar-height",
				`${bar.offsetHeight}px`,
			);
		const observer = new ResizeObserver(measure);
		observer.observe(bar);
		measure();
		return () => {
			observer.disconnect();
			root.style.removeProperty("--lp-project-bar-height");
		};
	}, []);
}
