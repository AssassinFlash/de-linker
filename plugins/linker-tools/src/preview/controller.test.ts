/**
 * External dependencies
 */
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { DOCK_CLASS, IN_CLASS, startPreview } from './controller';
import { KEYS, VISIT_IDLE_MS, type Visit } from './memory';
import { DISMISS_MS, DWELL_MS } from './rules';

// The markup Preview.php prints, trimmed to what the rules touch.
const PAGE = `
	<main><section class="hero">hero</section><input id="field"></main>
	<div class="linker-genie">
		<button type="button" class="linker-genie-open" data-linker-genie-open aria-expanded="false">Ask Genie</button>
	</div>
	<aside class="linker-genie-peek" data-linker-genie-peek data-anchor=".hero" hidden>
		<button type="button" data-linker-genie-peek-close>×</button>
		<button type="button" data-linker-genie-peek-ask="What pairs with the SAJ H2-10K-T3?">What pairs with the SAJ H2-10K-T3?</button>
	</aside>`;

let stop: () => void = () => undefined;
let heroBottom = 600;

function card(): HTMLElement {
	return document.querySelector( '[data-linker-genie-peek]' ) as HTMLElement;
}

function dock(): HTMLElement {
	return document.querySelector( '.linker-genie' ) as HTMLElement;
}

function visit(): Visit {
	return JSON.parse( window.localStorage.getItem( KEYS.visit ) ?? '{}' );
}

// The next page view, in this tab or another tab of the same browser: the
// same localStorage, a fresh document.
function nextPage( bottom = 0 ) {
	document.body.innerHTML = PAGE;
	const hero = document.querySelector( '.hero' ) as HTMLElement;
	vi.spyOn( hero, 'getBoundingClientRect' ).mockReturnValue( {
		bottom,
	} as DOMRect );
	start();
}

function start() {
	stop();
	stop = startPreview( card() );
}

// The visitor scrolls so that the hero's bottom edge sits at `bottom` px
// from the top of a 1000px viewport.
function scrollHeroTo( bottom: number ) {
	heroBottom = bottom;
	window.dispatchEvent( new Event( 'scroll' ) );
}

beforeEach( () => {
	vi.useFakeTimers();
	vi.setSystemTime( new Date( '2026-10-18T10:00:00Z' ) );
	window.localStorage.clear();
	document.body.innerHTML = PAGE;
	heroBottom = 600;
	vi.spyOn( window, 'innerHeight', 'get' ).mockReturnValue( 1000 );
	vi.spyOn( window, 'requestAnimationFrame' ).mockImplementation(
		( callback ) => {
			callback( 0 );
			return 0;
		}
	);
	const hero = document.querySelector( '.hero' ) as HTMLElement;
	vi.spyOn( hero, 'getBoundingClientRect' ).mockImplementation(
		() => ( { bottom: heroBottom } ) as DOMRect
	);
} );

afterEach( () => {
	stop();
	stop = () => undefined;
	vi.useRealTimers();
} );

describe( 'the trigger', () => {
	test( 'appears only after the main content is passed and the dwell is over', () => {
		start();
		vi.advanceTimersByTime( DWELL_MS * 3 );
		expect( card().hidden ).toBe( true );

		scrollHeroTo( 380 );
		vi.advanceTimersByTime( DWELL_MS - 1 );
		expect( card().hidden ).toBe( true );
		vi.advanceTimersByTime( 1 );

		expect( card().hidden ).toBe( false );
		expect( card() ).toHaveClass( IN_CLASS );
		expect( dock() ).toHaveClass( DOCK_CLASS );
		expect( visit().shown ).toBe( true );
	} );

	test( 'never takes the focus', () => {
		const field = document.getElementById( 'field' ) as HTMLElement;
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );
		expect( card().ownerDocument.activeElement ).toBe( document.body );
		expect( card().contains( card().ownerDocument.activeElement ) ).toBe(
			false
		);
		expect( field ).not.toHaveFocus();
	} );

	test( 'waits while the visitor types, and appears once they leave the field', () => {
		const field = document.getElementById( 'field' ) as HTMLElement;
		start();
		scrollHeroTo( 0 );
		field.focus();
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( true );

		field.blur();
		vi.advanceTimersByTime( 0 );
		expect( card().hidden ).toBe( false );
		expect( card().ownerDocument.activeElement ).toBe( document.body );
	} );
} );

describe( 'once per visit', () => {
	test( 'the next page, or another tab, of the same visit stays quiet', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );

		nextPage();
		vi.advanceTimersByTime( DWELL_MS * 2 );
		expect( card().hidden ).toBe( true );
	} );

	test( 'activity keeps the visit going past 30 minutes in all', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );

		vi.advanceTimersByTime( VISIT_IDLE_MS - 60_000 );
		window.dispatchEvent( new Event( 'scroll' ) ); // still active
		vi.advanceTimersByTime( VISIT_IDLE_MS - 60_000 );

		nextPage();
		vi.advanceTimersByTime( DWELL_MS * 2 );
		expect( card().hidden ).toBe( true );
	} );

	test( 'after 30 minutes without activity a new visit sees it again', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );
		stop();

		vi.advanceTimersByTime( VISIT_IDLE_MS + 1 );
		nextPage();
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );
	} );
} );

describe( 'during a conversation', () => {
	test( 'an open dock keeps the card away', () => {
		start();
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', { detail: { open: true } } )
		);
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( true );
	} );

	test( 'opening Genie while the card waits cancels it for the visit', () => {
		start();
		scrollHeroTo( 0 );
		document.querySelector< HTMLElement >( '.linker-genie-open' )?.click();
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( true );
		expect( visit().opened ).toBe( true );
	} );

	test( 'opening Genie hides a card that is up', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', { detail: { open: true } } )
		);
		expect( card().hidden ).toBe( true );
		expect( dock() ).not.toHaveClass( DOCK_CLASS );
	} );
} );

describe( 'a suggestion', () => {
	test( "goes to the dock loader's ask event and the card steps aside", () => {
		const asked: unknown[] = [];
		const listener = ( event: Event ) =>
			asked.push( ( event as CustomEvent ).detail );
		window.addEventListener( 'linker-genie-ask', listener );
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );

		document
			.querySelector< HTMLElement >( '[data-linker-genie-peek-ask]' )
			?.click();

		window.removeEventListener( 'linker-genie-ask', listener );
		expect( asked ).toEqual( [
			{ message: 'What pairs with the SAJ H2-10K-T3?' },
		] );
		expect( card().hidden ).toBe( true );
		expect( visit().opened ).toBe( true );
		// A suggestion is not a close: the 30 days do not start.
		expect( window.localStorage.getItem( KEYS.dismissedUntil ) ).toBeNull();
	} );
} );

describe( 'closing', () => {
	test( 'the × keeps it away for 30 days', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		document
			.querySelector< HTMLElement >( '[data-linker-genie-peek-close]' )
			?.click();
		expect( card().hidden ).toBe( true );
		expect( dock() ).not.toHaveClass( DOCK_CLASS );
		expect(
			Number( window.localStorage.getItem( KEYS.dismissedUntil ) )
		).toBe( Date.now() + DISMISS_MS );

		// A new visit within the 30 days stays quiet …
		vi.setSystemTime( Date.now() + DISMISS_MS - 60_000 );
		document.body.innerHTML = PAGE;
		start();
		window.dispatchEvent( new Event( 'scroll' ) );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( true );

		// … and the first visit after them sees it again.
		stop();
		vi.setSystemTime( Date.now() + 120_000 );
		document.body.innerHTML = PAGE;
		start();
		window.dispatchEvent( new Event( 'scroll' ) );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( false );
	} );

	test( 'Escape inside the card closes it the same way', () => {
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		card().dispatchEvent(
			new KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true } )
		);
		expect( card().hidden ).toBe( true );
		expect(
			window.localStorage.getItem( KEYS.dismissedUntil )
		).not.toBeNull();
	} );
} );

describe( 'storage', () => {
	test( 'a browser that blocks storage never sees the card', () => {
		vi.spyOn( window, 'localStorage', 'get' ).mockImplementation( () => {
			throw new DOMException( 'blocked', 'SecurityError' );
		} );
		start();
		scrollHeroTo( 0 );
		vi.advanceTimersByTime( DWELL_MS );
		expect( card().hidden ).toBe( true );
	} );
} );
