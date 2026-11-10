// @vitest-environment jsdom

/**
 * The helper sheet's keyboard ownership: the entrance focus, the modal
 * boundary and the escape-return. These are the parts a page cannot state in
 * markup, and the state-matrix rows
 * `genie:dock-keyboard-focus-escape-and-return` check them in a browser; this
 * test keeps the hook itself honest.
 */

/**
 * External dependencies
 */
import { act, render } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { useHelperDialog } from './useHelperDialog';

// jsdom has no layout: every element reports no client rects, which the hook
// reads as "not focusable". Give connected, non-hidden elements a box so the
// contract can be exercised at all.
beforeEach( () => {
	vi.spyOn( HTMLElement.prototype, 'getClientRects' ).mockImplementation(
		function ( this: HTMLElement ) {
			if ( ! this.isConnected || this.hasAttribute( 'hidden' ) ) {
				return { length: 0 } as unknown as DOMRectList;
			}
			return { length: 1 } as unknown as DOMRectList;
		}
	);
} );

afterEach( () => {
	vi.restoreAllMocks();
	document.body.style.overflow = '';
	document.body.replaceChildren();
} );

/** A sheet whose composer stays disabled while `enabled` is false. */
function Sheet( { enabled }: { enabled: boolean } ) {
	const { panel } = useHelperDialog( {
		open: true,
		workspace: false,
		close: () => undefined,
	} );
	return (
		<div data-linker-genie-mount>
			<a href="#sign-in">Sign in</a>
			<section ref={ panel }>
				<textarea
					className="linker-genie-app__input"
					disabled={ ! enabled }
				/>
				<button type="button">Send</button>
			</section>
		</div>
	);
}

test( 'the composer takes the entrance focus once it is enabled', async () => {
	vi.spyOn( window, 'innerWidth', 'get' ).mockReturnValue( 390 );
	const { rerender } = render( <Sheet enabled={ false } /> );

	// The mount prints the guest links above the app: while the composer is
	// disabled they must not become the dialog's entrance.
	await act( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 250 ) );
	} );
	expect( document.activeElement?.tagName ).not.toBe( 'A' );

	rerender( <Sheet enabled /> );
	await act( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 250 ) );
	} );
	expect(
		document.activeElement?.classList.contains( 'linker-genie-app__input' ),
		'the composer is the entrance'
	).toBe( true );
} );

test( 'the sheet is a modal dialog below the breakpoint', async () => {
	vi.spyOn( window, 'innerWidth', 'get' ).mockReturnValue( 390 );
	render( <Sheet enabled /> );
	await act( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 100 ) );
	} );
	const mount = document.querySelector( '[data-linker-genie-mount]' )!;
	expect( mount.getAttribute( 'role' ) ).toBe( 'dialog' );
	expect( mount.getAttribute( 'aria-modal' ) ).toBe( 'true' );
	expect( mount.getAttribute( 'aria-label' ) ).toBe( 'Genie' );
	expect( document.body.style.overflow ).toBe( 'hidden' );
} );

test( 'Escape closes the sheet and returns focus to the opener', async () => {
	vi.spyOn( window, 'innerWidth', 'get' ).mockReturnValue( 390 );
	let open = true;

	function Harness() {
		const [ shown, setShown ] = useState( false );
		open = shown;
		const { panel, remember } = useHelperDialog( {
			open: shown,
			workspace: false,
			close: () => setShown( false ),
		} );
		// The loader's own sequence: the opening control is handed over with
		// the event, then the sheet opens. This is what focus returns to.
		return (
			<>
				<button
					type="button"
					data-testid="opener"
					onClick={ ( event ) => {
						remember( event.currentTarget );
						setShown( true );
					} }
				>
					Ask Genie
				</button>
				{ shown ? (
					<div data-linker-genie-mount>
						<section ref={ panel }>
							<textarea className="linker-genie-app__input" />
							<button type="button">Send</button>
						</section>
					</div>
				) : null }
			</>
		);
	}

	render( <Harness /> );
	const opener = document.querySelector< HTMLButtonElement >(
		'[data-testid="opener"]'
	)!;
	await act( async () => {
		opener.click();
		await new Promise( ( resolve ) => setTimeout( resolve, 100 ) );
	} );

	await act( async () => {
		document.dispatchEvent(
			new KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true } )
		);
		await new Promise( ( resolve ) => setTimeout( resolve, 100 ) );
	} );
	expect(
		document.querySelector( '[data-linker-genie-mount]' ),
		'the sheet closes on Escape'
	).toBe( null );
	expect( document.activeElement, 'focus returns to the opener' ).toBe(
		opener
	);
} );
