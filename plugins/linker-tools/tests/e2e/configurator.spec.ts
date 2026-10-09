/**
 * The configurator in Chromium, driven through its stories (the engine's
 * recorded answers stand in for the engine; the aerial image is the live
 * Bavarian WMS).
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import place from '../fixtures/configurator/place-80538.json';
import roof from '../fixtures/configurator/roof-en.json';
import { roofClick } from './map-offset.mjs';

function story( id: string, locale: 'en' | 'de' = 'en' ) {
	return `/iframe.html?id=configurator-${ id }&viewMode=story&globals=locale:${ locale }`;
}

test( 'a household becomes a released system with its report', async ( {
	page,
} ) => {
	await page.goto( story( 'app--solution' ) );
	const cards = page.getByRole( 'article' );
	await expect( cards.first() ).toBeVisible();
	await expect( cards.first() ).toContainText( 'Hybrid inverter' );
	await expect(
		page.getByRole( 'button', { name: 'Add all to solution draft' } )
	).toBeVisible();
	await expect(
		page.getByRole( 'heading', { name: 'Design report', exact: true } )
	).toBeVisible();
	await expect(
		page.getByRole( 'heading', { name: 'Bill of materials' } )
	).toBeVisible();
} );

test( 'adding all shows the outcome in every card without moving it', async ( {
	page,
} ) => {
	await page.goto( story( 'app--solution' ) );
	const card = page.getByRole( 'article' ).first();
	await expect( card ).toBeVisible();
	const before = await card.boundingBox();
	await page
		.getByRole( 'button', { name: 'Add all to solution draft' } )
		.click();
	await expect( card.getByRole( 'status' ) ).toHaveText(
		'In your solution draft'
	);
	const after = await card.boundingBox();
	expect( after?.height ).toBe( before?.height );
	await expect(
		page.getByText( 'All products are in your solution draft.' )
	).toBeVisible();
} );

test( 'the roof step reads the official building at a click and counts modules', async ( {
	page,
} ) => {
	await page.goto( story( 'roof-step--munich' ) );
	const map = page.getByRole( 'application' );
	await expect( map.locator( 'canvas' ) ).toBeVisible();
	await expect(
		page.getByText( 'Click the roof of the building in the aerial image.' )
	).toBeVisible();
	const box = await map.boundingBox();
	const offset = roofClick( place, roof );
	await page.mouse.click(
		box!.x + box!.width / 2 + offset.x,
		box!.y + box!.height / 2 + offset.y
	);
	await expect(
		page.getByText( 'Official building model: Triftstraße 5' )
	).toBeVisible();
	await expect( page.getByRole( 'checkbox' ).first() ).toBeVisible();
	await expect(
		page.getByText( /Selected: \d+ modules, [\d.]+ kWp/ )
	).toBeVisible();
	await expect(
		page.getByRole( 'button', { name: 'Use this roof' } )
	).toBeEnabled();
} );

test( 'German throughout', async ( { page } ) => {
	await page.goto( story( 'app--solution', 'de' ) );
	await expect(
		page.getByRole( 'button', {
			name: 'Alles zum Lösungsentwurf hinzufügen',
		} )
	).toBeVisible();
	await expect(
		page.getByRole( 'heading', { name: 'Auslegungsbericht', exact: true } )
	).toBeVisible();
	await expect(
		page.getByRole( 'heading', { name: 'Stückliste' } )
	).toBeVisible();
} );

test( 'commercial: a load profile gives power, energy and the options', async ( {
	page,
} ) => {
	await page.goto( story( 'app--commercial-sized' ) );
	await expect(
		page.getByText( 'Battery power', { exact: true } )
	).toBeVisible();
	await expect(
		page.getByRole( 'table', {
			name: 'Peak shaving options from your load profile',
		} )
	).toBeVisible();
} );

test( 'nothing overflows the phone width', async ( { page } ) => {
	await page.setViewportSize( { width: 390, height: 844 } );
	const width = () =>
		page.evaluate(
			() =>
				document.documentElement.scrollWidth -
				document.documentElement.clientWidth
		);
	await page.goto( story( 'app--solution', 'de' ) );
	await expect( page.getByRole( 'article' ).first() ).toBeVisible();
	expect( await width() ).toBeLessThanOrEqual( 0 );
	await page.goto( story( 'app--commercial-sized', 'de' ) );
	await expect( page.getByRole( 'table' ) ).toBeVisible();
	expect( await width() ).toBeLessThanOrEqual( 0 );
	await page.goto( story( 'roof-step--munich', 'de' ) );
	await expect(
		page.getByRole( 'application' ).locator( 'canvas' )
	).toBeVisible();
	expect( await width() ).toBeLessThanOrEqual( 0 );
} );

test( 'the keyboard reaches every input in reading order, each with a visible focus ring', async ( {
	page,
} ) => {
	await page.goto( story( 'app--inputs' ) );
	await expect( page.locator( '#linker-plz' ) ).toBeVisible();
	const reached: string[] = [];
	for ( let step = 0; step < 11; step++ ) {
		await page.keyboard.press( 'Tab' );
		const focused = await page.evaluate( () => {
			const element = document.activeElement as HTMLElement;
			return {
				id: element.id || element.textContent?.trim() || '',
				outline: getComputedStyle( element ).outlineStyle,
			};
		} );
		reached.push( focused.id );
		expect( focused.outline, focused.id ).not.toBe( 'none' );
	}
	expect( reached ).toEqual( [
		'linker-tab-residential',
		'linker-plz',
		'linker-annual',
		'linker-kwp',
		'No PV figure yet? Estimate from the roof',
		'linker-phase-3',
		'linker-backup',
		'linker-heat-pump',
		'linker-ev',
		'linker-existing',
		'Calculate system',
	] );
} );

test( 'the roof step fills the PV array of the inputs', async ( { page } ) => {
	await page.goto( story( 'app--inputs' ) );
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page
		.getByRole( 'button', {
			name: 'No PV figure yet? Estimate from the roof',
		} )
		.click();
	const map = page.getByRole( 'application' );
	await expect( map.locator( 'canvas' ) ).toBeVisible();
	await map.scrollIntoViewIfNeeded();
	const box = await map.boundingBox();
	const offset = roofClick( place, roof );
	await page.mouse.click(
		box!.x + box!.width / 2 + offset.x,
		box!.y + box!.height / 2 + offset.y
	);
	await page.getByRole( 'button', { name: 'Use this roof' } ).click();
	await expect( page.getByRole( 'application' ) ).toHaveCount( 0 );
	await expect( page.locator( '#linker-kwp' ) ).toHaveValue( '6.44' );
	await expect( page.locator( '#linker-kwp' ) ).toHaveAttribute(
		'readonly',
		''
	);
	await expect(
		page.getByText(
			'From the roof: 14 modules on 3 planes, 6.44 kWp. Triftstraße 5'
		)
	).toBeVisible();
} );
