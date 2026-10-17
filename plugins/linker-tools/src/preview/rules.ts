/**
 * When Genie's preview card may appear (docs/specs/13-genie.md, 目标 4;
 * ticket #249). Pure functions: the controller feeds them what the page and
 * the browser's storage say, so every rule is testable without a browser.
 *
 * The numbers are starting values. No assistant in the competitive research
 * publishes one; each comment names the source the value was taken from
 * (docs/research/2026-10-17-ai-assistants/INTL.md §0.3 and CN.md §5.2), and
 * the prototype tried them on the real pages
 * (docs/prototypes/2026-10-17-preview-card/README.md).
 */

/**
 * The wait after the visitor has scrolled past the page's main content.
 * INTL.md §0.3 "触发": a time delay (Baymard), "spends a set amount of time
 * on the page" (Zendesk), "Time on page in seconds" (HubSpot); CN.md §5.2
 * sets the starting value at 8 seconds, the value the owner's target names
 * ("停留约 8 秒").
 */
export const DWELL_MS = 8_000;

/**
 * How long a closed card stays away. INTL.md §0.3 "关闭记忆": HubSpot keeps
 * a dismissed welcome message away for one day, Intercom's default sends a
 * message once and never again; 30 days sits between them, towards
 * Intercom's default.
 */
export const DISMISS_MS = 30 * 24 * 60 * 60 * 1_000;

/**
 * The anchor counts as scrolled past once its bottom edge rises above this
 * share of the viewport: the next section then fills most of the screen.
 * The prototype's own line for the home hero (preview-prototype.js,
 * `anchorY`: hero bottom minus 0.4 of the viewport).
 */
export const PASSED_LINE = 0.4;

/**
 * Without an anchor on the page, three quarters of a screen of scrolling
 * stands for "past the first screen of content" — the prototype's fallback
 * (preview-prototype.js, `anchorY`).
 */
export const FALLBACK_SCROLL = 0.75;

/**
 * Whether the visitor has scrolled past the page's main content.
 *
 * @param anchorBottom   The anchor's bottom edge relative to the viewport
 *                       (getBoundingClientRect().bottom), or null when the
 *                       page has no anchor.
 * @param viewportHeight The viewport's height.
 * @param scrollY        How far the page has scrolled.
 */
export function scrolledPast(
	anchorBottom: number | null,
	viewportHeight: number,
	scrollY: number
): boolean {
	if ( anchorBottom === null ) {
		return scrollY >= viewportHeight * FALLBACK_SCROLL;
	}
	return anchorBottom <= viewportHeight * PASSED_LINE;
}

/**
 * What the card's gate looks at when the wait is over.
 */
export interface Gate {
	/** The card (or the mobile mark) has already appeared during this visit. */
	shownThisVisit: boolean;
	/** The visitor opened Genie during this visit: a conversation is under way. */
	openedThisVisit: boolean;
	/** The dock is open right now. */
	dockOpen: boolean;
	/**
	 * Until when a closed card stays away (ms since the epoch), 0 when it was
	 * never closed, or null when the browser's storage cannot be read.
	 */
	dismissedUntil: number | null;
	/** The current time (ms since the epoch). */
	now: number;
}

/**
 * Whether the card may appear now.
 *
 * Unreadable storage counts as closed: the card could not remember a visit
 * or a close, and would return on every page (CN.md §5.2 "关掉后记住":
 * "取不到存储时按'已关闭'处理以免反复打扰").
 *
 * @param gate What the page and the storage say.
 */
export function mayShow( gate: Gate ): boolean {
	if ( gate.dismissedUntil === null ) {
		return false;
	}
	return (
		! gate.shownThisVisit &&
		! gate.openedThisVisit &&
		! gate.dockOpen &&
		gate.dismissedUntil <= gate.now
	);
}

/**
 * Whether a field has the focus: the card waits until the visitor stops
 * typing (INTL.md §0.3 "触发": no input field focused; WCAG 2.2 3.2.1).
 *
 * @param active The document's active element.
 */
export function typing( active: Element | null ): boolean {
	if ( ! active ) {
		return false;
	}
	return (
		active.closest(
			'input, textarea, select, [contenteditable=""], [contenteditable="true"]'
		) !== null
	);
}
