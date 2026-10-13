/**
 * External dependencies
 */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { MobileNavigation } from './MobileNavigation';

const steps = [
	{ id: 'inputs', label: 'Inputs' },
	{ id: 'solution', label: 'Solution' },
];

test( 'shortcuts scroll existing sections, without submitting or calculating', () => {
	const inputs = document.createElement( 'section' );
	inputs.id = 'inputs';
	const solution = document.createElement( 'section' );
	solution.id = 'solution';
	document.body.append( inputs, solution );
	const scroll = vi.fn();
	solution.scrollIntoView = scroll;
	const view = render( <MobileNavigation steps={ steps } /> );
	const button = screen.getByRole( 'button', { name: 'Solution' } );
	expect( button ).toHaveAttribute( 'type', 'button' );
	fireEvent.click( button );
	expect( scroll ).toHaveBeenCalledWith( {
		block: 'start',
		behavior: 'smooth',
	} );
	view.unmount();
	inputs.remove();
	solution.remove();
} );

test( 'recalculation removes the report shortcut until a real report exists', () => {
	const view = render(
		<MobileNavigation
			steps={ [ ...steps, { id: 'report', label: 'Design report' } ] }
		/>
	);
	expect(
		screen.getByRole( 'button', { name: 'Design report' } )
	).toBeInTheDocument();
	view.rerender( <MobileNavigation steps={ steps } /> );
	expect(
		screen.queryByRole( 'button', { name: 'Design report' } )
	).not.toBeInTheDocument();
} );

test( 'the measured bar height reserves content space and is cleaned up', () => {
	const app = document.createElement( 'div' );
	app.className = 'linker-configurator';
	document.body.append( app );
	const rect = vi
		.spyOn( Element.prototype, 'getBoundingClientRect' )
		.mockImplementation( function ( this: Element ) {
			return {
				height: this.classList.contains( 'linker-mobile-nav' )
					? 102
					: 0,
			} as DOMRect;
		} );
	const view = render( <MobileNavigation steps={ steps } />, {
		container: app,
	} );
	expect( app.style.getPropertyValue( '--linker-mobile-nav-height' ) ).toBe(
		'102px'
	);
	view.unmount();
	expect( app.style.getPropertyValue( '--linker-mobile-nav-height' ) ).toBe(
		''
	);
	rect.mockRestore();
	app.remove();
} );

test( 'the bar leaves the viewport when the app has ended', () => {
	const root = document.createElement( 'div' );
	root.dataset.linkerApp = 'configurator';
	document.body.append( root );
	let bottom = window.innerHeight + 200;
	vi.spyOn( root, 'getBoundingClientRect' ).mockImplementation(
		() => ( { top: 0, bottom } ) as DOMRect
	);
	const view = render( <MobileNavigation steps={ steps } />, {
		container: root,
	} );
	expect( screen.getByRole( 'navigation' ) ).not.toHaveAttribute( 'hidden' );
	bottom = 100;
	act( () => window.dispatchEvent( new Event( 'scroll' ) ) );
	expect( root.querySelector( 'nav' ) ).toHaveAttribute( 'hidden' );
	view.unmount();
	root.remove();
} );
