/**
 * Genie's preview card on the page (docs/specs/13-genie.md, 目标 4;
 * ticket #249): the card the server printed hidden appears once the visitor
 * has scrolled past the page's main content and stayed for the dwell time.
 *
 * - It never takes the focus and never opens the dock by itself.
 * - A suggestion hands its question to the dock loader's `linker-genie-ask`
 *   event (includes/Genie/Entries.php), the one entry every page chip uses.
 * - The × keeps it away for 30 days; Escape inside the card does the same.
 * - Below the dock's own breakpoint the stylesheet shows only a mark on the
 *   Genie button (preview.css); the gate and the memory are the same.
 */

/**
 * Internal dependencies
 */
import { Memory } from './memory';
import { DISMISS_MS, DWELL_MS, mayShow, scrolledPast, typing } from './rules';

/** The class the dock root carries while the card or the mark is up. */
export const DOCK_CLASS = 'linker-genie--peek';

/** The class that runs the card's entrance once it is visible. */
export const IN_CLASS = 'is-in';

/**
 * Starts the card's rules on a page.
 *
 * @param card The server-rendered card (`[data-linker-genie-peek]`).
 * @param win  The window (a test passes its own).
 * @return A function that removes every listener and timer again.
 */
export function startPreview(
	card: HTMLElement,
	win: Window = window
): () => void {
	const doc = win.document;
	const memory = new Memory( win );
	const anchorSelector = card.dataset.anchor ?? '';
	let armed = false;
	let shown = false;
	let dockOpen = false;
	let timer: ReturnType< typeof setTimeout > | undefined;
	let waitingForBlur = false;

	const dock = () => doc.querySelector< HTMLElement >( '.linker-genie' );

	function anchorBottom(): number | null {
		const anchor = anchorSelector
			? doc.querySelector( anchorSelector )
			: null;
		return anchor ? anchor.getBoundingClientRect().bottom : null;
	}

	function gateOpen(): boolean {
		return mayShow( {
			shownThisVisit: memory.shown(),
			openedThisVisit: memory.opened(),
			dockOpen,
			dismissedUntil: memory.dismissedUntil(),
			now: Date.now(),
		} );
	}

	function show() {
		shown = true;
		memory.markShown();
		card.hidden = false;
		dock()?.classList.add( DOCK_CLASS );
		// The entrance runs on the next frame, after the card has a box.
		win.requestAnimationFrame( () => card.classList.add( IN_CLASS ) );
	}

	function hide() {
		card.classList.remove( IN_CLASS );
		card.hidden = true;
	}

	// The wait is over: show the card, or wait for the visitor to leave the
	// field they are typing in, or give up for this page.
	function attempt() {
		timer = undefined;
		if ( ! gateOpen() ) {
			return;
		}
		if ( typing( doc.activeElement ) ) {
			waitingForBlur = true;
			return;
		}
		show();
	}

	function onFocusOut() {
		if ( ! waitingForBlur ) {
			return;
		}
		// focusout fires before the focus lands on the next element.
		win.setTimeout( () => {
			if ( waitingForBlur && ! typing( doc.activeElement ) ) {
				waitingForBlur = false;
				attempt();
			}
		}, 0 );
	}

	function onScroll() {
		if ( armed || shown ) {
			return;
		}
		if ( scrolledPast( anchorBottom(), win.innerHeight, win.scrollY ) ) {
			armed = true;
			timer = setTimeout( attempt, DWELL_MS );
		}
	}

	// Genie opened by any entry: a conversation is under way for the rest
	// of this visit, and the card steps aside.
	function onOpened() {
		memory.markOpened();
		waitingForBlur = false;
		if ( timer !== undefined ) {
			clearTimeout( timer );
			timer = undefined;
		}
		hide();
	}

	function onState( event: Event ) {
		const detail = ( event as CustomEvent< { open?: unknown } > ).detail;
		dockOpen = !! detail?.open;
		if ( dockOpen ) {
			onOpened();
			// The mobile mark goes with the card once the dock is open.
			dock()?.classList.remove( DOCK_CLASS );
		}
	}

	function onDocumentClick( event: MouseEvent ) {
		const target = event.target as Element | null;
		if ( target?.closest?.( '[data-linker-genie-open]' ) ) {
			onOpened();
		}
	}

	function dismiss() {
		memory.dismiss( Date.now() + DISMISS_MS );
		hide();
		dock()?.classList.remove( DOCK_CLASS );
	}

	function onCardClick( event: MouseEvent ) {
		const target = ( event.target as Element | null )?.closest?.(
			'[data-linker-genie-peek-close], [data-linker-genie-peek-ask]'
		);
		if ( ! target ) {
			return;
		}
		if ( target.hasAttribute( 'data-linker-genie-peek-close' ) ) {
			dismiss();
			return;
		}
		const message =
			target.getAttribute( 'data-linker-genie-peek-ask' ) ?? '';
		onOpened();
		win.dispatchEvent(
			new CustomEvent( 'linker-genie-ask', { detail: { message } } )
		);
	}

	function onCardKey( event: KeyboardEvent ) {
		if ( event.key === 'Escape' ) {
			dismiss();
		}
	}

	win.addEventListener( 'scroll', onScroll, { passive: true } );
	win.addEventListener( 'linker-genie-state', onState );
	doc.addEventListener( 'click', onDocumentClick, true );
	doc.addEventListener( 'focusout', onFocusOut );
	card.addEventListener( 'click', onCardClick );
	card.addEventListener( 'keydown', onCardKey );
	// A page opened already scrolled (a reload, a back navigation) starts
	// the wait at once.
	onScroll();

	return () => {
		if ( timer !== undefined ) {
			clearTimeout( timer );
		}
		win.removeEventListener( 'scroll', onScroll );
		win.removeEventListener( 'linker-genie-state', onState );
		doc.removeEventListener( 'click', onDocumentClick, true );
		doc.removeEventListener( 'focusout', onFocusOut );
		card.removeEventListener( 'click', onCardClick );
		card.removeEventListener( 'keydown', onCardKey );
	};
}
