/**
 * External dependencies
 */
import { describe, expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import {
	DISMISS_MS,
	DWELL_MS,
	mayShow,
	scrolledPast,
	typing,
	type Gate,
} from './rules';

const open: Gate = {
	shownThisVisit: false,
	openedThisVisit: false,
	dockOpen: false,
	dismissedUntil: 0,
	now: 1_000_000,
};

describe( 'the starting values', () => {
	test( 'about 8 seconds of dwell and 30 days of silence after a close', () => {
		expect( DWELL_MS ).toBe( 8000 );
		expect( DISMISS_MS ).toBe( 30 * 86_400_000 );
	} );
} );

describe( 'scrolledPast', () => {
	test( 'the anchor counts once its bottom rises above 40% of the viewport', () => {
		expect( scrolledPast( 500, 1000, 0 ) ).toBe( false );
		expect( scrolledPast( 401, 1000, 900 ) ).toBe( false );
		expect( scrolledPast( 400, 1000, 900 ) ).toBe( true );
		expect( scrolledPast( -200, 1000, 2000 ) ).toBe( true );
	} );

	test( 'without an anchor, three quarters of a screen of scrolling counts', () => {
		expect( scrolledPast( null, 800, 599 ) ).toBe( false );
		expect( scrolledPast( null, 800, 600 ) ).toBe( true );
	} );
} );

describe( 'mayShow', () => {
	test( 'a fresh visit may see the card', () => {
		expect( mayShow( open ) ).toBe( true );
	} );

	test( 'once per visit', () => {
		expect( mayShow( { ...open, shownThisVisit: true } ) ).toBe( false );
	} );

	test( 'never during a conversation', () => {
		expect( mayShow( { ...open, openedThisVisit: true } ) ).toBe( false );
		expect( mayShow( { ...open, dockOpen: true } ) ).toBe( false );
	} );

	test( 'a close keeps it away until its time has passed', () => {
		expect( mayShow( { ...open, dismissedUntil: open.now + 1 } ) ).toBe(
			false
		);
		expect( mayShow( { ...open, dismissedUntil: open.now } ) ).toBe( true );
	} );

	test( 'unreadable storage counts as closed', () => {
		expect( mayShow( { ...open, dismissedUntil: null } ) ).toBe( false );
	} );
} );

describe( 'typing', () => {
	test( 'fields count, buttons and the page do not', () => {
		document.body.innerHTML =
			'<input id="i"><textarea id="t"></textarea><select id="s"></select><div contenteditable="true" id="c"></div><button id="b">x</button>';
		for ( const id of [ 'i', 't', 's', 'c' ] ) {
			expect( typing( document.getElementById( id ) ) ).toBe( true );
		}
		expect( typing( document.getElementById( 'b' ) ) ).toBe( false );
		expect( typing( document.body ) ).toBe( false );
		expect( typing( null ) ).toBe( false );
	} );
} );
