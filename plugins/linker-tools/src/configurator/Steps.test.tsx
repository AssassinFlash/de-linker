/**
 * Recalculation scrolls the Solution section to the top of the viewport.
 * On a phone only the step rail sticks under the site header. The section's
 * scroll clearance is the sticky top plus that rail's measured height plus
 * the existing 32px gap. The sticky element must not contain the section:
 * a descendant's scroll-margin cannot clear its own sticky ancestor.
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
		if ( this.classList.contains( 'linker-steps' ) ) {
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
		'--linker-steps-scroll-offset': `${ Math.ceil( STICKY_TOP_PX + barHeight + SECTION_GAP_PX ) }px`,
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
	expect( within( rail as HTMLElement ).getByText( 'Inputs' ) ).toHaveClass(
		'linker-steps__label'
	);
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

test( 'a model change lands the Solution clear of the sticky rail', async () => {
	const { chromium } = await import( '@playwright/test' );
	const css = readFileSync(
		join( dirname( fileURLToPath( import.meta.url ) ), 'configurator.css' ),
		'utf8'
	);
	const html = `<!doctype html><html><head><meta charset="utf-8"><style>
			body { margin: 0; }
			.site-header { position: sticky; top: 0; height: 89px; z-index: 50; background: #123; }
			${ css }
			.filler { height: 2400px; }
			</style></head><body>
			<header class="site-header"></header>
			<div style="height: 240px"></div>
			<div data-linker-app="configurator">
				<div class="linker-configurator" lang="en">
					<div class="linker-shell">
						<nav class="linker-steps" aria-label="Configurator">
							<ol class="linker-steps__list">
								<li class="linker-steps__item is-current"><span class="linker-steps__number">01</span><span class="linker-steps__label">Inputs</span></li>
								<li class="linker-steps__item"><span class="linker-steps__number">02</span><span class="linker-steps__label">Solution</span></li>
								<li class="linker-steps__item"><span class="linker-steps__number">03</span><span class="linker-steps__label">Design report</span></li>
							</ol>
						</nav>
						<div class="linker-stage">
							<section class="linker-block"><h2 class="linker-block__title">Project type</h2></section>
							<div class="linker-flow">
								<section class="linker-section"><h2 class="linker-section__title">Inputs</h2><div class="filler"></div></section>
								<section class="linker-section" id="solution"><h2 class="linker-section__title" id="linker-solution-title">Solution</h2><div class="filler"></div></section>
							</div>
						</div>
					</div>
				</div>
			</div>
			</body></html>`;
	const browser = await chromium.launch();
	try {
		const page = await browser.newPage( {
			viewport: { width: 390, height: 844 },
		} );
		await page.setContent( html, { waitUntil: 'load' } );
		const landed = await page.evaluate( () => {
			const section = document.querySelector( '#solution' );
			const title = document.querySelector( '#linker-solution-title' );
			const rail = document.querySelector( '.linker-steps' );
			const root = document.querySelector(
				'[data-linker-app="configurator"]'
			);
			const shell = document.querySelector( '.linker-shell' );
			if (
				! ( section instanceof HTMLElement ) ||
				! ( title instanceof HTMLElement ) ||
				! ( rail instanceof HTMLElement ) ||
				! ( root instanceof HTMLElement ) ||
				! ( shell instanceof HTMLElement )
			) {
				throw new Error( 'configurator fixture is missing a node' );
			}
			const stickyHolding = ( node: Element ) => {
				const held = [];
				for (
					let current = node && node.parentElement;
					current;
					current = current.parentElement
				) {
					const position = getComputedStyle( current ).position;
					if ( position === 'sticky' || position === 'fixed' ) {
						held.push( current.className );
					}
				}
				return held;
			};
			// Same formula Steps publishes: sticky top, measured rail, 32px gap.
			const offset = Math.ceil(
				89 + rail.getBoundingClientRect().height + 32
			);
			root.style.setProperty(
				'--linker-steps-scroll-offset',
				`${ offset }px`
			);
			section.scrollIntoView( { block: 'start' } );
			const titleBox = title.getBoundingClientRect();
			const railBox = rail.getBoundingClientRect();
			return {
				railPosition: getComputedStyle( rail ).position,
				shellPosition: getComputedStyle( shell ).position,
				sectionHeldBy: stickyHolding( section ),
				titleHeldBy: stickyHolding( title ),
				titleTop: titleBox.top,
				railBottom: railBox.bottom,
			};
		} );
		expect( landed.railPosition ).toBe( 'sticky' );
		expect( landed.shellPosition ).not.toBe( 'sticky' );
		expect( landed.sectionHeldBy ).toEqual( [] );
		expect( landed.titleHeldBy ).toEqual( [] );
		expect( landed.titleTop ).toBeGreaterThanOrEqual(
			landed.railBottom + SECTION_GAP_PX
		);
	} finally {
		await browser.close();
	}
} );
