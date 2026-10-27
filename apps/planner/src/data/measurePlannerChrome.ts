/** Read the native site/application bars before an anchor or action is revealed.
 * React effects and ResizeObserver callbacks can run after a child needs focus. */
export function measurePlannerChrome(root: HTMLElement): void {
	const header = document.getElementById("lc-header"),
		bar = root.querySelector<HTMLElement>(".lp-project-bar");
	root.style.setProperty(
		"--lp-site-header-height",
		`${header?.offsetHeight ?? 0}px`,
	);
	root.style.setProperty(
		"--lp-project-bar-height",
		`${bar?.offsetHeight ?? 0}px`,
	);
}
