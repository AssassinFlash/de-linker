/**
 * External dependencies
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { expect, test } from 'vitest';

const source = readFileSync( resolve( 'assets/marketing-hover.js' ), 'utf8' );

function page( finePointer = true, mediaAvailable = true ) {
	const fixture = document.implementation.createHTMLDocument();
	fixture.body.innerHTML = `<button class="stage" aria-selected="true">First</button>
		<button class="stage" aria-selected="false"><span>Second</span></button>
		<div id="outside">Other content</div>`;
	const buttons = Array.from( fixture.querySelectorAll( 'button' ) );
	const clicks: number[] = [];
	const select = ( selected: number ) => {
		buttons.forEach( ( button, index ) => {
			button.setAttribute(
				'aria-selected',
				String( index === selected )
			);
		} );
	};
	buttons.forEach( ( button, index ) => {
		button.addEventListener( 'click', () => {
			clicks.push( index );
			select( index );
		} );
	} );
	fixture.addEventListener( 'keydown', ( event ) => {
		if ( event.key === 'Home' ) {
			select( 0 );
		}
	} );
	runInNewContext( source, {
		window: {
			matchMedia: mediaAvailable
				? () => ( { matches: finePointer } )
				: undefined,
			linkerHoverTriggers: '.stage',
		},
		document: fixture,
	} );
	const pointer = (
		type: string,
		target: Element,
		x = 20,
		y = 30,
		relatedTarget: EventTarget | null = null
	) => {
		target.dispatchEvent(
			new MouseEvent( type, {
				bubbles: true,
				clientX: x,
				clientY: y,
				relatedTarget,
			} )
		);
	};
	return { fixture, buttons, clicks, pointer };
}

test( 'real movement over a nested label uses the native trigger click', () => {
	const { buttons, clicks, pointer } = page();
	pointer( 'mousemove', buttons[ 1 ].querySelector( 'span' )! );
	expect( clicks ).toEqual( [ 1 ] );
	expect( buttons[ 1 ].getAttribute( 'aria-selected' ) ).toBe( 'true' );
} );

test( 'a layout mouseover cannot replace a keyboard selection', () => {
	const { buttons, clicks, pointer } = page();
	buttons[ 1 ].click();
	buttons[ 1 ].dispatchEvent(
		new KeyboardEvent( 'keydown', { key: 'Home', bubbles: true } )
	);
	pointer( 'mouseover', buttons[ 1 ] );
	expect( buttons[ 0 ].getAttribute( 'aria-selected' ) ).toBe( 'true' );
	expect( clicks ).toEqual( [ 1 ] );
} );

test( 'unchanged viewport coordinates do not activate a new element', () => {
	const { fixture, buttons, clicks, pointer } = page();
	pointer( 'mousemove', fixture.querySelector( '#outside' )!, 20, 30 );
	pointer( 'mousemove', buttons[ 1 ], 20, 30 );
	expect( clicks ).toEqual( [] );
	pointer( 'mousemove', buttons[ 1 ], 21, 30 );
	expect( clicks ).toEqual( [ 1 ] );
} );

test( 'movement within the active module does not click it again', () => {
	const { buttons, clicks, pointer } = page();
	pointer( 'mousemove', buttons[ 0 ], 10, 20 );
	pointer( 'mousemove', buttons[ 0 ], 11, 20 );
	expect( clicks ).toEqual( [] );
} );

test( 'movement between modules continues to switch both ways', () => {
	const { buttons, clicks, pointer } = page();
	pointer( 'mousemove', buttons[ 1 ], 10, 20 );
	pointer( 'mousemove', buttons[ 0 ], 11, 20 );
	expect( clicks ).toEqual( [ 1, 0 ] );
} );

test( 'a module with its own active marker clicks once per pointer entry', () => {
	const { fixture, buttons, clicks, pointer } = page();
	buttons[ 1 ].addEventListener( 'click', () => {
		buttons[ 1 ].removeAttribute( 'aria-selected' );
		buttons[ 1 ].classList.add( 'is-on' );
	} );
	const label = buttons[ 1 ].querySelector( 'span' )!;
	pointer( 'mousemove', buttons[ 1 ], 10, 20 );
	pointer( 'mousemove', label, 11, 20 );
	pointer( 'mouseout', buttons[ 1 ], 11, 20, label );
	pointer( 'mousemove', buttons[ 1 ], 12, 20 );
	expect( clicks ).toEqual( [ 1 ] );
	pointer( 'mousemove', fixture.querySelector( '#outside' )!, 13, 20 );
	pointer( 'mousemove', label, 14, 20 );
	expect( clicks ).toEqual( [ 1, 1 ] );
} );

test( 'leaving the viewport permits re-entry at the same coordinates', () => {
	const { buttons, clicks, pointer } = page();
	buttons[ 1 ].addEventListener( 'click', () => {
		buttons[ 1 ].removeAttribute( 'aria-selected' );
	} );
	pointer( 'mousemove', buttons[ 1 ], 10, 20 );
	pointer( 'mouseout', buttons[ 1 ], 10, 20 );
	pointer( 'mousemove', buttons[ 1 ], 10, 20 );
	expect( clicks ).toEqual( [ 1, 1 ] );
} );

test.each( [
	[ false, true ],
	[ true, false ],
] )(
	'non-hover pointers and unavailable media queries keep native clicks',
	( finePointer, mediaAvailable ) => {
		const { buttons, clicks, pointer } = page(
			finePointer,
			mediaAvailable
		);
		pointer( 'mousemove', buttons[ 1 ] );
		pointer( 'mouseover', buttons[ 1 ] );
		expect( clicks ).toEqual( [] );
		buttons[ 1 ].click();
		expect( clicks ).toEqual( [ 1 ] );
	}
);
