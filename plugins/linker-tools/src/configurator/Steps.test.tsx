/**
 * Recalculation scrolls the Solution section to the top of the viewport.
 * On a phone the step list sticks under the site header and wraps, so the
 * section's scroll clearance has to be the sticky top plus the list's
 * measured height plus the existing 32px gap — not a guessed one-row height.
 */

/**
 * External dependencies
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { fakeEngine, fakeStore } from '../../tests/configurator/fakes';
import { App } from './App';
import type { Config } from './config';

vi.mock( './api/solutions', () => ( { saveSolution: vi.fn() } ) );

const STICKY_TOP_PX = 89;
const SECTION_GAP_PX = 32;

function mount( barHeight: number ) {
	const config: Config = {
		engineUrl: 'https://engine.test',
		restUrl: '/wp-json/',
		restNonce: 'n',
		locale: 'en',
		openRoof: false,
	};
	const root = document.createElement( 'div' );
	root.dataset.linkerApp = 'configurator';
	document.body.append( root );
	const rect = Element.prototype.getBoundingClientRect;
	Element.prototype.getBoundingClientRect = function getBoundingClientRect() {
		const box = rect.call( this );
		if (
			this.classList.contains( 'linker-steps' ) ||
			this.classList.contains( 'linker-shell' )
		) {
			return { ...box, height: barHeight, bottom: box.top + barHeight };
		}
		return box;
	};
	const view = render(
		<App
			config={ config }
			engine={ fakeEngine( { locale: 'en' } ).engine }
			store={ fakeStore().store }
		/>,
		{ container: root }
	);
	Element.prototype.getBoundingClientRect = rect;
	return view;
}

async function calculate() {
	fireEvent.change( screen.getByLabelText( /Postcode of the site/ ), {
		target: { value: '80538' },
	} );
	fireEvent.change( screen.getByLabelText( /Annual household consumption/ ), {
		target: { value: '5000' },
	} );
	fireEvent.change( screen.getByLabelText( /PV array/ ), {
		target: { value: '10' },
	} );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate system' } )
		);
	} );
}

test( 'a model change scrolls the Solution clear of the measured step list', async () => {
	const scrolls: { target: Element; options: ScrollIntoViewOptions }[] = [];
	Element.prototype.scrollIntoView = function scrollIntoView( options ) {
		scrolls.push( {
			target: this as Element,
			options:
				typeof options === 'object' && options !== null ? options : {},
		} );
	};
	// jsdom has no layout. 77px is a two-row phone bar, the case a fixed
	// one-row height would under-clear.
	const barHeight = 77;
	const { container } = mount( barHeight );

	await calculate();
	expect(
		await screen.findByRole( 'heading', { name: 'Solution' } )
	).toBeVisible();
	const select = await screen.findByLabelText( 'Other inverter' );
	const other = within( select ).getAllByRole(
		'option'
	)[ 1 ] as HTMLOptionElement;
	await act( async () => {
		fireEvent.change( select, { target: { value: other.value } } );
	} );

	// The one call site serves the first calculation and every model change;
	// each call must scroll the Solution section itself, so the section's
	// scroll-margin is what clears the bar.
	expect( scrolls ).toHaveLength( 2 );
	for ( const { target, options } of scrolls ) {
		expect( options ).toEqual( { block: 'start', behavior: 'smooth' } );
		expect(
			target.classList.contains( 'linker-section' ) &&
				target.querySelector( '.linker-section__title' )
					?.textContent === 'Solution'
		).toBe( true );
	}
	expect( container ).toHaveStyle( {
		'--linker-steps-scroll-offset': `${ STICKY_TOP_PX + barHeight + SECTION_GAP_PX }px`,
	} );
} );

test( 'the rail is vertical, the project type is cards, and the form stays expanded', () => {
	const { container } = mount( 48 );
	const rail = container.querySelector( '.linker-steps' );
	expect( rail?.tagName ).toBe( 'NAV' );
	expect(
		within( rail as HTMLElement ).getByText( 'Configurator' )
	).toBeInTheDocument();
	expect(
		within( rail as HTMLElement )
			.getAllByRole( 'listitem' )
			.map( ( item ) => item.textContent )
	).toEqual( [ '01Inputs', '02Solution', '03Design report' ] );
	expect(
		screen.getByRole( 'radio', { name: 'Residential' } )
	).toBeChecked();
	expect(
		screen.getByRole( 'heading', { name: 'Project type' } )
	).toBeVisible();
	expect(
		screen.getByText( 'Step 1 · Which project are you sizing?' )
	).toBeVisible();
	expect(
		screen.getByRole( 'group', { name: 'Grid connection' } )
	).toBeVisible();
	expect(
		screen.getByRole( 'button', { name: 'Calculate system' } )
	).toBeVisible();
} );

test( 'the narrow-viewport rule pins the shell and clears the measured rail', () => {
	const css = readFileSync(
		join( dirname( fileURLToPath( import.meta.url ) ), 'configurator.css' ),
		'utf8'
	);
	const sticky = css.match(
		/@media \(max-width: 860px\) \{([\s\S]*?)\n\}/
	)?.[ 1 ];
	expect( sticky ).toBeDefined();
	expect( sticky ).toContain( '.linker-shell' );
	expect( sticky ).toContain( 'position: sticky;' );
	expect( sticky ).toContain( 'top: 89px;' );
	expect( sticky ).toContain( 'z-index: 40;' );
	expect( sticky ).toContain(
		'scroll-margin-top: var(--linker-steps-scroll-offset, 32px);'
	);
	expect( sticky ).not.toContain( '44px' );
	// Desktop keeps the rail in the left column. Only the phone pins it.
	expect( css ).toContain( 'grid-template-columns: 13.5rem minmax(0, 1fr);' );
	expect( css ).not.toMatch(
		/@media \(min-width: 861px\)[\s\S]*\.linker-steps[\s\S]*position:\s*sticky/
	);
} );
