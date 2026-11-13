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

/** The browser scrolls an initial location hash before either bar is measured,
 * so the scroll-margin fallbacks (0px) land the target under the sticky chrome;
 * browsers without scroll anchoring (Safari) never correct that. Correct it
 * here after every measurement, once per load, until the deadline passes or
 * the user scrolls away. */
let armedHash: string | null = null;
let revealDeadline = 0;

export function armHashReveal(): void {
	if (armedHash !== null) return;
	armedHash = location.hash.slice(1) || null;
	// Production loads resolve the project bar and fonts well inside 4 s;
	// past that a correction would fight the reader instead of fixing a
	// cold landing, so the arm expires.
	revealDeadline = performance.now() + 4000;
}

export function disarmHashReveal(): void {
	armedHash = null;
}

export function revealHashTarget(root: HTMLElement): void {
	if (armedHash === null) return;
	if (performance.now() > revealDeadline) {
		armedHash = null;
		return;
	}
	const target = document.getElementById(armedHash);
	if (!target || !root.contains(target)) return;
	const top =
		target.getBoundingClientRect().top +
		window.scrollY -
		(parseFloat(getComputedStyle(target).scrollMarginTop) || 0);
	if (Math.abs(window.scrollY - top) > 1) window.scrollTo({ top });
}
